import datetime

from coldfront.core.allocation.models import AccountDeletionRequest, \
    AccountDeletionRequestStatusChoice, AllocationUserAttribute, \
    AccountDeletionRequestRequesterChoice
from coldfront.core.allocation.utils import has_cluster_access
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.utils_.removal_utils import \
    ProjectRemovalRequestRunner
from coldfront.core.utils.common import import_from_settings, \
    utc_now_offset_aware


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

        self.success_messages = []
        self.error_messages = []

    def run(self):
        expiration = self._get_expiration()
        deletion_request = None

        no_deletion_requests = self._check_active_account_deletion_requests()
        has_cluster_access = self._check_cluster_access()

        if no_deletion_requests and has_cluster_access:
            deletion_request = self._create_request(expiration)
            if self.requester_str == 'Admin':
                self._create_project_removal_requests()

        return deletion_request

    def _create_project_removal_requests(self):
        proj_users = ProjectUser.objects.filter(user=self.user_obj,
                                                status='Active')

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

    def send_emails(self):
        # TODO: send emails about cluster account deletion
        # TODO: send to user, PIs, and admins
        email_enabled = import_from_settings('EMAIL_ENABLED', False)

        # Email PI, managers, user and admins

        # if email_enabled:
        #     email_sender = import_from_settings('EMAIL_SENDER')
        #     email_signature = import_from_settings('EMAIL_SIGNATURE')
        #     support_email = import_from_settings('CENTER_HELP_EMAIL')
        #     email_admin_list = import_from_settings('EMAIL_ADMIN_LIST')
        #
        #     # Send emails to the removed user, the project's PIs (who have
        #     # notifications enabled), and the project's managers. Exclude the
        #     # user who made the request.
        #     pi_condition = Q(
        #         role__name='Principal Investigator', status__name='Active',
        #         enable_notifications=True)
        #     manager_condition = Q(role__name='Manager', status__name='Active')
        #     manager_pi_queryset = self.proj_obj.projectuser_set.filter(
        #         pi_condition | manager_condition).exclude(
        #         user=self.requester_obj)
        #     users_to_notify = [x.user for x in manager_pi_queryset]
        #     if self.user_obj != self.requester_obj:
        #         users_to_notify.append(self.user_obj)
        #     for user in users_to_notify:
        #         template_context = {
        #             'user_first_name': user.first_name,
        #             'user_last_name': user.last_name,
        #             'requester_first_name': self.requester_obj.first_name,
        #             'requester_last_name': self.requester_obj.last_name,
        #             'remove_user_first_name': self.user_obj.first_name,
        #             'remove_user_last_name': self.user_obj.last_name,
        #             'project_name': self.proj_obj.name,
        #             'signature': email_signature,
        #             'support_email': support_email,
        #         }
        #         send_email_template(
        #             'Project Removal Request',
        #             'email/project_removal/project_removal.txt',
        #             template_context,
        #             email_sender,
        #             [user.email])
        #
        #     # Email cluster administrators.
        #     template_context = {
        #         'user_first_name': self.user_obj.first_name,
        #         'user_last_name': self.user_obj.last_name,
        #         'project_name': self.proj_obj.name,
        #     }
        #     send_email_template(
        #         'Project Removal Request',
        #         'email/project_removal/project_removal_admin.txt',
        #         template_context,
        #         email_sender,
        #         email_admin_list)
