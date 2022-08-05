import datetime

from coldfront.core.allocation.models import ClusterAcctDeletionRequest, \
    ClusterAcctDeletionRequestStatusChoice, AllocationUserAttribute, \
    ClusterAcctDeletionRequestRequesterChoice
from coldfront.core.allocation.utils import has_cluster_access
from coldfront.core.utils.common import import_from_settings, \
    utc_now_offset_aware


class ClusterAcctDeletionRequestRunner(object):
    """An object that performs necessary database changes when a new
    cluster account deletion request is submitted."""

    def __init__(self, user_obj, requester_str):
        self.requester_str = requester_str
        self.user_obj = user_obj

        self.success_messages = []
        self.error_messages = []

    def run(self):
        queued_status = \
            ClusterAcctDeletionRequestStatusChoice.objects.get(name='Queued')
        ready_status = \
            ClusterAcctDeletionRequestStatusChoice.objects.get(name='Ready')
        processing_status = \
            ClusterAcctDeletionRequestStatusChoice.objects.get(name='Processing')

        requester_obj = \
            ClusterAcctDeletionRequestRequesterChoice.objects.get(name=self.requester_str)

        if self.requester_str in ['User', 'PI']:
            expiration_days = import_from_settings('ACCOUNT_DELETION_MANUAL_QUEUE_DAYS')
        elif self.requester_str == 'System':
            expiration_days = import_from_settings('ACCOUNT_DELETION_AUTO_QUEUE_DAYS')
        else:
            message = f'Invalid requester_str {self.requester_str} passed.'
            self.error_messages.append(message)
            return None

        expiration = utc_now_offset_aware() + \
                     datetime.timedelta(days=expiration_days)

        proceed_flag = True
        deletion_request = None

        # Check for active ClusterAcctDeletionRequest for user.
        if ClusterAcctDeletionRequest.objects.filter(
                user=self.user_obj,
                status__in=[queued_status, ready_status, processing_status]).exists():
            message = f'Error requesting cluster account deletion of user ' \
                      f'{self.user_obj.username}. An active cluster account ' \
                      f'deletion request for user ' \
                      f'{self.user_obj.username} already exists.'
            self.error_messages.append(message)
            proceed_flag = False

        # Cannot delete cluster account if the user does not have a
        # cluster account.
        if not has_cluster_access(self.user_obj):
            message = f'Error requesting cluster account deletion of user ' \
                      f'{self.user_obj.username}. {self.user_obj.username} ' \
                      f'does not have a cluster account.'
            self.error_messages.append(message)
            proceed_flag = False

        if proceed_flag:
            deletion_request = ClusterAcctDeletionRequest.objects.create(
                user=self.user_obj,
                requester=requester_obj,
                status=queued_status,
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

        return deletion_request

    def get_messages(self):
        """A getter for this instance's user_messages."""
        return self.success_messages, self.error_messages

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
