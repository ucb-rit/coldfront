import datetime
import logging
from urllib.parse import urljoin

from django.db import transaction
from django.urls import reverse
from flags.state import flag_enabled

from coldfront.config import settings
from coldfront.core.allocation.models import AccountDeletionRequest, \
    AccountDeletionRequestStatusChoice, AllocationUserAttribute, \
    AccountDeletionRequestReasonChoice, AllocationUser, \
    AllocationUserStatusChoice
from coldfront.core.allocation.utils import has_cluster_access
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.utils_.removal_utils import \
    ProjectRemovalRequestRunner
from coldfront.core.resource.models import Resource
from coldfront.core.utils.common import import_from_settings, \
    utc_now_offset_aware
from coldfront.core.utils.email.email_strategy import EnqueueEmailStrategy, \
    SendEmailStrategy
from coldfront.core.utils.mail import send_email_template

logger = logging.getLogger(__name__)


class AccountDeletionRequestRunner(object):
    """An object that performs necessary database changes when a new
    cluster account deletion request is submitted."""

    def __init__(self, user_obj, requester, reason_obj):
        self.user_obj = user_obj
        self.requester = requester
        self.reason_obj = reason_obj

        self._email_strategy = EnqueueEmailStrategy()

        self._success_messages = []
        self._warning_messages = []

    def get_warning_messages(self):
        """Return warning messages raised during the run."""
        return self._warning_messages.copy()

    def run(self):
        no_deletion_requests = self._check_active_account_deletion_requests()
        # has_cluster_access = self._check_cluster_access()

        if no_deletion_requests:
            with transaction.atomic():
                expiration = self._get_expiration()
                self.request_obj = self._create_request(expiration)
                self._create_project_removal_requests()

            self._send_emails_safe()
            self._log_success_messages()

    def _create_project_removal_requests(self):
        if self.reason_obj.name == 'Admin':
            proj_users = ProjectUser.objects.filter(user=self.user_obj,
                                                    status__name='Active')

            for proj_user in proj_users:
                # Note that the request is technically requested by the
                # system but we have to set the admin that made the initial
                # deletion request as the requester.
                request_runner = ProjectRemovalRequestRunner(
                    self.requester,
                    self.user_obj,
                    proj_user.project)
                runner_result = request_runner.run()

            message = f'Created {proj_users.count()} project removal ' \
                      f'requests for {self.user_obj}.'
            self._success_messages.append(message)

    def _create_request(self, expiration):
        request = AccountDeletionRequest.objects.create(
            user=self.user_obj,
            reason=self.reason_obj,
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
        self._success_messages.append(message)

        return request

    def _get_expiration(self):
        """Returns the expiration date based on who created the
        deletion request."""
        if self.reason_obj.name in ['User', 'Admin']:
            expiration_days = \
                import_from_settings('ACCOUNT_DELETION_MANUAL_QUEUE_DAYS')
        else:
            expiration_days = \
                import_from_settings('ACCOUNT_DELETION_AUTO_QUEUE_DAYS')

        return utc_now_offset_aware() + datetime.timedelta(days=expiration_days)

    def _check_cluster_access(self):
        """Checks if the user has cluster access."""
        # TODO: does this need to be checked? A user could have no
        #  access to projects but have access
        if not has_cluster_access(self.user_obj):
            message = f'Error requesting cluster account deletion of user ' \
                      f'{self.user_obj.username}. {self.user_obj.username} ' \
                      f'does not have a cluster account.'
            self._warning_messages.append(message)
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
            self._warning_messages.append(message)
            return False
        return True

    def _log_success_messages(self):
        """Write success messages to the log.

        Catch all exceptions to prevent rolling back any enclosing
        transaction.

        Warning: If the enclosing transaction fails, the already-written
        log messages are not revoked."""
        try:
            for message in self._success_messages:
                logger.info(message)
        except Exception:
            pass

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
            self._warning_messages.append(message)

    def _send_notification_emails(self):
        """Sends emails to the user whose account is being deleted."""
        email_args = (self.user_obj, self.request_obj, self.reason_obj)
        if self.reason_obj.name == 'Admin':
            self._email_strategy.process_email(
                send_account_deletion_user_notification_emails,
                *email_args)
        elif self.reason_obj.name == 'User':
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


def send_account_deletion_user_notification_emails(user_obj,
                                                   request_obj,
                                                   reason_obj):
    if reason_obj.name not in ['Admin', 'LastProject']:
        raise ValueError(f'Invalid reason {reason_obj.name} passed. '
                         f'Must be either \"Admin\" or \"LastProject\"')

    if settings.EMAIL_ENABLED:
        subject = 'Cluster Account Deletion Request'
        template = 'email/account_deletion/new_request_user.txt'
        html_template = 'email/account_deletion/new_request_user.html'

        if reason_obj.name == 'Admin':
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


def send_account_deletion_admin_notification_emails(user_obj,
                                                    request_obj,
                                                    reason_obj):
    if reason_obj.name not in ['User', 'System']:
        raise ValueError(f'Invalid reason_obj {reason_obj} passed. '
                         f'Must be either \"User\" or \"LastProject\"')

    if settings.EMAIL_ENABLED:
        subject = 'New Cluster Account Deletion Request'
        template = 'email/account_deletion/new_request_admin.txt'
        html_template = 'email/account_deletion/new_request_admin.html'

        user_str = f'{user_obj.first_name} {user_obj.last_name}'
        if reason_obj.name == 'User':
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
    """An object that performs necessary database changes when a
    cluster account deletion request is completed."""

    def __init__(self, request_obj):
        if not isinstance(request_obj, AccountDeletionRequest):
            raise TypeError(
                f'AccountDeletionRequest {request_obj} has unexpected '
                f'type {type(request_obj)}.')

        self.request_obj = request_obj
        self.user_obj = request_obj.user

        self._email_strategy = SendEmailStrategy()

        self._success_messages = []
        self._warning_messages = []

    def run(self):
        with transaction.atomic():
            self._set_userprofile_values()
            self._remove_allocation_users()

        self._send_emails_safe()
        self._log_success_messages()

    def get_warning_messages(self):
        """Return warning messages raised during the run."""
        return self._warning_messages.copy()

    def _set_userprofile_values(self):
        """Sets the appropriate userprofile values."""
        self.request_obj.user.userprofile.is_deleted = True
        self.request_obj.user.userprofile.billing_activity = None
        self.request_obj.user.userprofile.cluster_uid = None
        self.request_obj.user.userprofile.save()

    def _remove_allocation_users(self):
        """Removes any remaining allocation users."""
        self._remove_secure_directories()
        self._remove_remaining_allocations()

    def _remove_secure_directories(self):
        """Removes the user from any secure directories."""
        if flag_enabled('SECURE_DIRS_REQUESTABLE'):
            scratch_dir = Resource.objects.get(name='Scratch P2/P3 Directory')
            groups_dir = Resource.objects.get(name='Groups P2/P3 Directory')
            alloc_users = AllocationUser.objects.filter(
                user=self.user_obj,
                status__name='Active',
                allocation__resources__in=[scratch_dir, groups_dir])

            for alloc_user in alloc_users:
                alloc_user.status = \
                    AllocationUserStatusChoice.objects.get(name='Removed')
                alloc_user.save()

            message = f'Removed {self.user_obj.username} from ' \
                      f'{alloc_users.count()} secure directories.'
            self._success_messages.append(message)

    def _remove_remaining_allocations(self):
        """Removes the user from any remaining allocations."""
        alloc_users = AllocationUser.objects.filter(
            user=self.user_obj,
            status__name='Active')

        for alloc_user in alloc_users:
            alloc_user.status = \
                AllocationUserStatusChoice.objects.get(name='Removed')
            alloc_user.save()

        message = f'Removed {self.user_obj.username} from ' \
                  f'{alloc_users.count()} allocations.'
        self._success_messages.append(message)

    def _log_success_messages(self):
        """Write success messages to the log.

        Catch all exceptions to prevent rolling back any enclosing
        transaction.

        Warning: If the enclosing transaction fails, the already-written
        log messages are not revoked."""
        try:
            for message in self._success_messages:
                logger.info(message)
        except Exception:
            pass

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
            self._warning_messages.append(message)

    def _send_notification_emails(self):
        """Sends emails to the user whose account is being deleted."""
        email_args = (self.user_obj, self.request_obj)
        self._email_strategy.process_email(
            send_account_deletion_complete_user_notification_emails,
            *email_args)


def send_account_deletion_complete_user_notification_emails(user_obj,
                                                            request_obj):
    if settings.EMAIL_ENABLED:
        subject = 'Cluster Account Deletion Request Complete'
        template = 'email/account_deletion/request_complete_user.txt'

        if request_obj.requester.name == 'Admin':
            reason = 'The request to delete your account was initiated by a ' \
                     'system administrator.'
        elif request_obj.requester.name == 'System':
            reason = 'The request to delete your account was automatically ' \
                     'initiated when you left your last project.'
        else:
            reason = 'The request to delete your account was self initiated.'
        
        # TODO: can users create new cluster accounts? If they can, 
        #  that text should be included in the email template.
        template_context = {
            'user_str': f'{user_obj.first_name} {user_obj.last_name}',
            'reason': reason,
            'center_help_email': settings.CENTER_HELP_EMAIL,
            'signature': settings.EMAIL_SIGNATURE,
        }

        send_email_template(
            subject,
            template,
            template_context,
            settings.EMAIL_SENDER,
            [user_obj.email],
            cc=[user_obj.userprofile.host_user.email])
    