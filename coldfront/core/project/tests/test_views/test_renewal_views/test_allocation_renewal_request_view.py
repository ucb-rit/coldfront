from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase
from django.urls import reverse
from http import HTTPStatus


class TestAllocationRenewalRequestView(TestBase):
    """A class for testing AllocationRenewalRequestView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

    def _create_project_to_renew(self):
        """Create a Project for the user to renew. Return the created
        Project along with a ProjectUser representing its PI."""
        computing_allowance_interface = ComputingAllowanceInterface()
        computing_allowance = self.get_predominant_computing_allowance()
        project_name_prefix = computing_allowance_interface.code_from_name(
            computing_allowance.name)

        project_name = f'{project_name_prefix}_project'
        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        project = Project.objects.create(
            name=project_name,
            title=project_name,
            status=active_project_status)
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        project_user = ProjectUser.objects.create(
            project=project,
            role=pi_role,
            status=active_project_user_status,
            user=self.user)
        return project, project_user

    @staticmethod
    def _renew_pi_allocation_url():
        """Return the URL for requesting to renew a PI's allocation."""
        return reverse('renew-pi-allocation')

    @staticmethod
    def _request_view_name():
        """Return the name of the request view."""
        return 'allocation_renewal_request_view'

    def _send_post_requests(self, allocation_period, pi_project_user):
        """Send the necessary POST requests to the view for the given
        AllocationPeriod, Project, and PI ProjectUser. Optionally
        include sample renewal survey answers."""
        view_name = self._request_view_name()
        current_step_key = f'{view_name}-current_step'

        form_data = []

        allocation_period_form_data = {
            '0-allocation_period': allocation_period.pk,
            current_step_key: '0',
        }
        form_data.append(allocation_period_form_data)

        pi_selection_form_data = {
            '1-PI': pi_project_user.pk,
            current_step_key: '1',
        }
        form_data.append(pi_selection_form_data)

        pooling_preference_form_data = {
            '2-preference': AllocationRenewalRequest.UNPOOLED_TO_UNPOOLED,
            current_step_key: '2',
        }
        form_data.append(pooling_preference_form_data)

        google_renewal_survey_form_data = {
            '6-was_survey_completed': True,
            current_step_key: '6',
        }
        form_data.append(google_renewal_survey_form_data)

        review_and_submit_form_data = {
            '7-confirmation': True,
            current_step_key: '7',
        }
        form_data.append(review_and_submit_form_data)

        url = self._renew_pi_allocation_url()
        for i, data in enumerate(form_data):
            response = self.client.post(url, data)
            if i == len(form_data) - 1:
                self.assertRedirects(response, reverse('home'))
            else:
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_sets_request_request_time(self):
        """Test that a POST request sets the request_time of the renewal
        request."""
        project, pi_project_user = self._create_project_to_renew()

        pre_time = utc_now_offset_aware()

        allocation_period = get_current_allowance_year_period()

        self._send_post_requests(
            allocation_period, pi_project_user)

        post_time = utc_now_offset_aware()

        requests = AllocationRenewalRequest.objects.all()
        self.assertEqual(requests.count(), 1)
        request = requests.first()
        self.assertTrue(pre_time <= request.request_time <= post_time)
