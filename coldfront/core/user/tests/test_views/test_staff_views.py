from django.urls import reverse
from http import HTTPStatus

from flags.state import flag_enabled

from coldfront.core.project.models import *
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.allocation.models import *
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.tests.test_base import TestBase as AllTestsBase

from django.contrib.auth.models import User
from django.core import mail


class TestBase(AllTestsBase):
    """Base class for testing staff view permissions"""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        self.user1 = User.objects.create(
            email='user1@email.com',
            first_name='Normal',
            last_name='User1',
            username='user1')
        self.user1.set_password(self.password)
        self.user1.save()

        self.staff1 = User.objects.create(
            email='staff1@email.com',
            first_name='Normal',
            last_name='Staff1',
            username='staff1')
        self.staff1.set_password(self.password)
        self.staff1.is_staff = True
        self.staff1.save()

        computing_allowance_interface = ComputingAllowanceInterface()
        computing_allowance = self.get_predominant_computing_allowance()
        project_name_prefix = computing_allowance_interface.code_from_name(
            computing_allowance.name)

        project_name = f'{project_name_prefix}_project'
        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        self.project = Project.objects.create(
            name=project_name,
            title=project_name,
            status=active_project_status)

        # Clear the mail outbox.
        mail.outbox = []

    def assert_has_access(self, user, has_access, url):
        """Assert that the given user has or does not have access to
        the URL"""
        self.client.login(username=user.username, password=self.password)
        status_code = [HTTPStatus.OK, HTTPStatus.FOUND] if has_access else [HTTPStatus.FORBIDDEN]
        response = self.client.get(url)
        self.assertIn(response.status_code, status_code)
        self.client.logout()


class TestStaffViewPermissions(TestBase):
    """A class for testing staff permissions"""

    def setUp(self):
        """Set up test data."""
        super().setUp()

    def test_user_search(self):
        # user-search-all
        self.assert_has_access(self.staff1, True, reverse('user-search-all'))

        # user-search-home
        self.assert_has_access(self.staff1, True, reverse('user-search-home'))

    def test_pi_allocation_renewal_request_detail(self):
        # pi-allocation-renewal-request-detail
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        ProjectUser.objects.create(
            project=self.project,
            role=pi_role,
            status=active_project_user_status,
            user=self.user1)

        # Create an AllocationRenewalRequest.
        computing_allowance = self.get_predominant_computing_allowance()
        allocation_period = get_current_allowance_year_period()
        under_review_request_status = \
            AllocationRenewalRequestStatusChoice.objects.get(
                name='Under Review')
        allocation_renewal_request = \
            AllocationRenewalRequest.objects.create(
                requester=self.user1,
                pi=self.user1,
                computing_allowance=computing_allowance,
                allocation_period=allocation_period,
                status=under_review_request_status,
                pre_project=self.project,
                post_project=self.project,
                request_time=utc_now_offset_aware())

        self.assert_has_access(self.staff1, True,
                               reverse(
                                   'pi-allocation-renewal-request-detail',
                                   kwargs={'pk': allocation_renewal_request.pk}))

        # pi-allocation-renewal-pending-request-list
        self.assert_has_access(self.staff1, True,
                               reverse('pi-allocation-renewal-pending-request-list'))

        # pi-allocation-renewal-completed-request-list
        self.assert_has_access(self.staff1, True,
                               reverse('pi-allocation-renewal-completed-request-list'))

    def test_vector_project_request(self):
        if flag_enabled('LRC_ONLY'):
            return

        # Create a new Project.
        computing_allowance_interface = ComputingAllowanceInterface()
        computing_allowance = self.get_predominant_computing_allowance()
        project_name_prefix = computing_allowance_interface.code_from_name(
            computing_allowance.name)

        new_project_name = f'{project_name_prefix}_new_project'
        new_project_status = ProjectStatusChoice.objects.get(name='New')
        new_project = Project.objects.create(
            name=new_project_name,
            status=new_project_status,
            title=new_project_name,
            description=f'Description of {new_project_name}.')

        # create vector project request
        status = ProjectAllocationRequestStatusChoice.objects.get(
            name='Under Review')
        request = VectorProjectAllocationRequest.objects.create(
            requester=self.user1,
            pi=self.user1,
            project=new_project,
            status=status)

        # vector-project-request-detail
        self.assert_has_access(self.staff1, True,
                               reverse('vector-project-request-detail',
                                       kwargs={'pk': request.pk}))

        # vector-project-pending-request-list
        self.assert_has_access(self.staff1, True,
                               reverse('vector-project-pending-request-list'))

        # vector-project-completed-request-list
        self.assert_has_access(self.staff1, True,
                               reverse('vector-project-completed-request-list'))

    def test_savio_project_request(self):
        # new-project-request-detail
        # Create a new Project.
        computing_allowance_interface = ComputingAllowanceInterface()
        computing_allowance = self.get_predominant_computing_allowance()
        project_name_prefix = computing_allowance_interface.code_from_name(
            computing_allowance.name)

        new_project_name = f'{project_name_prefix}_new_project'
        new_project_status = ProjectStatusChoice.objects.get(name='New')
        new_project = Project.objects.create(
            name=new_project_name,
            status=new_project_status,
            title=new_project_name,
            description=f'Description of {new_project_name}.')

        under_review_request_status = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Under Review')
        request = SavioProjectAllocationRequest.objects.create(
            requester=self.user1,
            allocation_type=computing_allowance_interface.name_short_from_name(
                computing_allowance.name),
            computing_allowance=computing_allowance,
            allocation_period=get_current_allowance_year_period(),
            pi=self.user1,
            project=new_project,
            survey_answers={},
            status=under_review_request_status)

        # new-project-request-detail
        self.assert_has_access(self.staff1, True,
                               reverse('new-project-request-detail',
                                       kwargs={'pk': request.pk}))

        # new-project-pending-request-list
        self.assert_has_access(self.staff1, True,
                               reverse('new-project-pending-request-list'))

        # new-project-completed-request-list
        self.assert_has_access(self.staff1, True,
                               reverse('new-project-completed-request-list'))

    def test_allocation_cluster_account_request_lists(self):
        # allocation-cluster-account-request-list
        self.client.login(username=self.staff1.username, password=self.password)
        url = reverse('allocation-cluster-account-request-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotContains(response, 'Allocation Actions')
        self.assertNotContains(response, 'Activate')
        self.assertNotContains(response, 'Deny')
        self.client.logout()

        # allocation-cluster-account-request-list-completed
        self.assert_has_access(self.staff1, True,
                               reverse('allocation-cluster-account-request-list-completed'))

        # allocation-cluster-account-update-status "Should staff have this?"

    def test_project_review(self):
        project_review = ProjectReview.objects.create(
            project=self.project,
            status=ProjectReviewStatusChoice.objects.get(
                name='Completed'),
            reason_for_not_updating_project=''
        )
        # project-review-list
        self.assert_has_access(self.staff1, True, reverse('project-review-list'))

        # project-review-complete
        self.assert_has_access(self.staff1, True,
                               reverse('project-review-complete',
                                       kwargs={'project_review_pk': project_review.pk}))

        # project-review-email ??
        self.assert_has_access(self.staff1, True,
                               reverse('project-review-email',
                                       kwargs={'pk': project_review.pk}))

    def test_allocation(self):
        allocation = Allocation.objects.create(project=self.project,
                                               status=AllocationStatusChoice.objects.get(name='Active'))
        # allocation-detail
        self.assert_has_access(self.staff1, True,
                               reverse('allocation-detail',
                                       kwargs={'pk': allocation.pk}))

        # allocation-list
        self.assert_has_access(self.staff1, True, reverse('allocation-list'))

    def test_project_detail(self):
        # project-detail
        self.assert_has_access(self.staff1, True,
                               reverse('project-detail',
                                       kwargs={'pk': self.project.pk}))
