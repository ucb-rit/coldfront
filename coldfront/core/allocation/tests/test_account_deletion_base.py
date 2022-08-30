from decimal import Decimal

from django.contrib.auth.models import User

from coldfront.api.statistics.utils import create_project_allocation, \
    create_user_project_allocation
from coldfront.core.allocation.models import AllocationAttributeType, \
    AllocationUserAttribute, AccountDeletionRequestReasonChoice, \
    AccountDeletionRequestStatusChoice, AccountDeletionRequest
from coldfront.core.billing.models import BillingActivity, BillingProject
from coldfront.core.project.models import ProjectStatusChoice, Project, \
    ProjectUser, ProjectUserStatusChoice, ProjectUserRoleChoice
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase


class TestAccountDeletionBase(TestBase):
    """Base testing class for account deletions."""

    def setUp(self):
        super().setUp()

        self.superuser = User.objects.create(username='superuser',
                                             email='superuser@example.com',
                                             is_superuser=True)

        self.create_test_user()
        self.user2 = User.objects.create(username='user2')

        self.staff_user = User.objects.create(username='staff_user',
                                              is_staff=True)

        self.user.userprofile.cluster_uid = '11223344'
        billing_project = BillingProject.objects.create(
            identifier='123456')
        self.user.userprofile.billing_activity = \
            BillingActivity.objects.create(identifier='123',
                                           billing_project=billing_project)
        self.user.userprofile.host_user = self.superuser
        self.user.userprofile.save()

        for user in User.objects.all():
            user.set_password(self.password)
            self.sign_user_access_agreement(user)
            user.save()

        for i in range(3):
            project = Project.objects.create(
                name=f'project{i}',
                status=ProjectStatusChoice.objects.get(name='Active'))
            setattr(self, f'project{i}', project)

            project_user = ProjectUser.objects.create(
                project=project,
                user=self.user,
                status=ProjectUserStatusChoice.objects.get(name='Active'),
                role=ProjectUserRoleChoice.objects.get(name='User'))
            setattr(self, f'project_user{i}', project_user)

            # Create a compute allocation for the Project.
            amount = Decimal(f'{i + 1}000.00')
            allocation_objs = create_project_allocation(project, amount)
            setattr(self, f'allocation{i}', allocation_objs.allocation)

            # Create a compute allocation the user.
            allocation_user_objs = \
                create_user_project_allocation(self.user, project, amount)
            setattr(self, f'allocation_user{i}', allocation_user_objs.allocation_user)

            AllocationUserAttribute.objects.create(
                allocation=allocation_objs.allocation,
                allocation_user=allocation_user_objs.allocation_user,
                allocation_attribute_type=AllocationAttributeType.objects.get(name='Cluster Account Status'),
                value='Active')

    def create_account_deletion_request(self, user, status, reason):
        self.request = AccountDeletionRequest.objects.create(
            user=user,
            status=AccountDeletionRequestStatusChoice.objects.get(name=status),
            reason=AccountDeletionRequestReasonChoice.objects.get(name=reason),
            expiration=utc_now_offset_aware())

    def get_response(self, user, url):
        self.client.login(username=user.username, password=self.password)
        return self.client.get(url)

    def post_response(self, user, url, data):
        self.client.login(username=user.username, password=self.password)
        return self.client.post(url, data)

    def change_request_status(self, status_name):
        self.request.status = \
            AccountDeletionRequestStatusChoice.objects.get(name=status_name)
        self.request.save()

    def change_request_reason(self, reason_name):
        self.request.reason = \
            AccountDeletionRequestReasonChoice.objects.get(name=reason_name)
        self.request.save()

    def complete_request_checklist(self):
        completed_state = {'status': 'Complete',
                           'timestamp': utc_now_offset_aware().isoformat()}
        self.request.state['project_removal'] = completed_state
        self.request.state['data_deletion'] = completed_state
        self.request.state['account_deletion'] = completed_state
        self.request.save()
