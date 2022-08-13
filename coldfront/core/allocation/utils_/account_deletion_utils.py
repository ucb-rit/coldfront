import datetime
import logging
from urllib.parse import urljoin

from django.db import transaction
from django.urls import reverse

from coldfront.config import settings
from coldfront.core.allocation.models import AccountDeletionRequest, \
    AccountDeletionRequestStatusChoice, AllocationUserAttribute, \
    AccountDeletionRequestRequesterChoice
from coldfront.core.allocation.utils import has_cluster_access
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.utils_.removal_utils import \
    ProjectRemovalRequestRunner
from coldfront.core.utils.common import import_from_settings, \
    utc_now_offset_aware
from coldfront.core.utils.email.email_strategy import EnqueueEmailStrategy
from coldfront.core.utils.mail import send_email_template

logger = logging.getLogger(__name__)


class AccountDeletionRequestRunner(object):
    """An object that performs necessary database changes when a new
    cluster account deletion request is submitted."""

    def __init__(self, user_obj, requester_obj, requester_str):
        self.user_obj = user_obj
        self.requester_obj = requester_obj
        self.requester_str = requester_str

        self.requester_choice = \
            AccountDeletionRequestRequesterChoice.objects.get(
                name=self.requester_str)

        self._email_strategy = EnqueueEmailStrategy()

        self.success_messages = []
        self.error_messages = []

    def run(self):
        expiration = self._get_expiration()

        no_deletion_requests = self._check_active_account_deletion_requests()
        # has_cluster_access = self._check_cluster_access()

        if no_deletion_requests: # and has_cluster_access:
            with transaction.atomic():
                self.deletion_request = self._create_request(expiration)
                self._create_project_removal_requests()
            self._send_emails_safe()

    def _create_project_removal_requests(self):
        if self.requester_str == 'Admin':
            proj_users = ProjectUser.objects.filter(user=self.user_obj,
                                                    status__name='Active')

            for proj_user in proj_users:
                # Note that the request is technically requested by the
                # system but we have to set the admin that made the initial
                # deletion request as the requester.
                request_runner = ProjectRemovalRequestRunner(
                    self.requester_obj,
                    self.user_obj,
                    proj_user.project)
                runner_result = request_runner.run()
                success_messages, error_messages = request_runner.get_messages()

                for m in success_messages:
                    self.success_messages.append(m)
                for m in error_messages:
                    self.error_messages.append(m)

    def _create_request(self, expiration):
        request = AccountDeletionRequest.objects.create(
            user=self.user_obj,
            requester=self.requester_choice,
            status=AccountDeletionRequestStatusChoice.objects.get(name='Queued'),
            expiration=expiration
        )

        cluster_access_attributes = AllocationUserAttribute.objects.filter(
            allocation_user__user=self.user_obj,
            allocation_attribute_type__name='Cluster Account Status',
            value='Active')

        for attr in cluster_access_attributes:
            attr.value = 'Pending - Delete'
            attr.save()

        message = f'Successfully created cluster account deletion ' \
                  f'request for user {self.user_obj.username}.'
        self.success_messages.append(message)

        return request

    def _get_expiration(self):
        """Returns the expiration date based on who created the
        deletion request."""
        if self.requester_str in ['User', 'Admin']:
            expiration_days = \
                import_from_settings('ACCOUNT_DELETION_MANUAL_QUEUE_DAYS')
        elif self.requester_str == 'System':
            expiration_days = \
                import_from_settings('ACCOUNT_DELETION_AUTO_QUEUE_DAYS')
        else:
            message = f'Invalid requester_str {self.requester_str} passed.'
            self.error_messages.append(message)
            return None

        return utc_now_offset_aware() + datetime.timedelta(days=expiration_days)

    def _check_cluster_access(self):
        """Checks if the user has cluster access."""
        # TODO: does this need to be checked? A user could have no
        #  access to projects but have access
        if not has_cluster_access(self.user_obj):
            message = f'Error requesting cluster account deletion of user ' \
                      f'{self.user_obj.username}. {self.user_obj.username} ' \
                      f'does not have a cluster account.'
            self.error_messages.append(message)
            return False
        return True

    def _check_active_account_deletion_requests(self):
        """Checks if a user already has an active account deletion request."""
        queued_status = \
            AccountDeletionRequestStatusChoice.objects.get(name='Queued')
        ready_status = \
            AccountDeletionRequestStatusChoice.objects.get(name='Ready')
        processing_status = \
            AccountDeletionRequestStatusChoice.objects.get(name='Processing')

        if AccountDeletionRequest.objects.filter(
                user=self.user_obj,
                status__in=[queued_status, ready_status, processing_status]).exists():
            message = f'Error requesting cluster account deletion of user ' \
                      f'{self.user_obj.username}. An active cluster account ' \
                      f'deletion request for user ' \
                      f'{self.user_obj.username} already exists.'
            self.error_messages.append(message)
            return False
        return True

    def get_messages(self):
        """A getter for this instance's user_messages."""
        return self.success_messages.copy(), self.error_messages.copy()

    def _send_notification_emails(self):
        """Sends emails to the user whose account is being deleted."""
        email_args = (self.user_obj, self.deletion_request, self.requester_str)
        if self.requester_str == 'Admin':
            self._email_strategy.process_email(
                send_account_deletion_user_notification_emails,
                *email_args)
        elif self.requester_str == 'User':
            self._email_strategy.process_email(
                send_account_deletion_admin_notification_emails,
                *email_args)
        else:
            self._email_strategy.process_email(
                send_account_deletion_user_notification_emails,
                *email_args)
            self._email_strategy.process_email(
                send_account_deletion_user_notification_emails,
                *email_args)

        self._email_strategy.send_queued_emails()

    def _send_emails_safe(self):
        """Send emails.

        Catch all exceptions to prevent rolling back any
        enclosing transaction.

        If send failures occur, store a warning message.
        """
        try:
            self._send_notification_emails()
        except Exception as e:
            message = (
                f'Encountered unexpected exception when sending notification '
                f'emails. Details: \n{e}')
            logger.exception(message)


def send_account_deletion_user_notification_emails(user_obj, request_obj, requester_str):
    if requester_str not in ['Admin', 'System']:
        raise ValueError(f'Invalid requester_str {requester_str} passed. '
                         f'Must be either \"Admin\" or \"System\"')

    if settings.EMAIL_ENABLED:
        subject = 'Cluster Account Deletion Request'
        template = 'email/account_deletion/new_request_user.txt'
        html_template = 'email/account_deletion/new_request_user.html'

        if requester_str == 'Admin':
            reason = 'The request to delete your account was initiated by a ' \
                     'system administrator.'
            waiting_period = settings.ACCOUNT_DELETION_MANUAL_QUEUE_DAYS
        else:
            reason = 'The request to delete your account was automatically ' \
                     'initiated when you left your last project.'
            waiting_period = settings.ACCOUNT_DELETION_AUTO_QUEUE_DAYS

        confirm_url = urljoin(settings.CENTER_BASE_URL,
                              reverse('cluster-account-deletion-request-user-data-deletion',
                                      kwargs={'pk': request_obj.pk}))

        template_context = {
            'user_str': f'{user_obj.first_name} {user_obj.last_name}',
            'reason': reason,
            'confirm_url': confirm_url,
            'waiting_period': waiting_period,
            'center_help_email': settings.CENTER_HELP_EMAIL,
            'signature': settings.EMAIL_SIGNATURE,
        }

        send_email_template(
            subject,
            template,
            template_context,
            settings.EMAIL_SENDER,
            [user_obj.email],
            cc=[user_obj.userprofile.host_user.email],
            html_template=html_template)


def send_account_deletion_admin_notification_emails(user_obj, request_obj, requester_str):
    if requester_str not in ['User', 'System']:
        raise ValueError(f'Invalid requester_str {requester_str} passed. '
                         f'Must be either \"Admin\" or \"System\"')

    if settings.EMAIL_ENABLED:
        subject = 'New Cluster Account Deletion Request'
        template = 'email/account_deletion/new_request_admin.txt'
        html_template = 'email/account_deletion/new_request_admin.html'

        user_str = f'{user_obj.first_name} {user_obj.last_name}'
        if requester_str == 'User':
            reason = f'The request to delete the cluster account was ' \
                     f'initiated by {user_str}.'
            waiting_period = settings.ACCOUNT_DELETION_MANUAL_QUEUE_DAYS
        else:
            reason = f'The request to delete the cluster account was ' \
                     f'automatically initiated when {user_str} left their ' \
                     f'last project.'
            waiting_period = settings.ACCOUNT_DELETION_AUTO_QUEUE_DAYS

        review_url = urljoin(settings.CENTER_BASE_URL,
                              reverse('cluster-account-deletion-request-detail',
                                      kwargs={'pk': request_obj.pk}))

        template_context = {
            'user_str': f'{user_obj.first_name} {user_obj.last_name}',
            'reason': reason,
            'review_url': review_url,
            'waiting_period': waiting_period
        }

        send_email_template(
            subject,
            template,
            template_context,
            settings.EMAIL_SENDER,
            [user_obj.email],
            cc=[user_obj.userprofile.host_user.email],
            html_template=html_template)


class AccountDeletionRequestCompleteRunner(object):
    pass