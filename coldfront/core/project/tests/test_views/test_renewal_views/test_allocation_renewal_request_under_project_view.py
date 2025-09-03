from http import HTTPStatus

from django.urls import reverse

from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import enable_deployment
from coldfront.core.utils.tests.test_base import TestBase


class TestAllocationRenewalRequestUnderProjectViewMixin(object):
    """A mixin for testing AllocationRenewalRequestUnderProjectView
    functionality common to both deployments."""

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
        project = self.create_active_project_with_pi(
            project_name, self.user, create_compute_allocation=True)
        project_user = ProjectUser.objects.get(project=project, user=self.user)
        return project, project_user

    @staticmethod
    def _project_detail_url(pk):
        """Return the URL for the detail view for the Project with the
        given primary key."""
        return reverse('project-detail', kwargs={'pk': pk})

    @staticmethod
    def _project_renew_url(pk):
        """Return the URL for the requesting to renew a PI's
        allocation under the Project with the given primary key."""
        return reverse('project-renew', kwargs={'pk': pk})

    @staticmethod
    def _request_view_name():
        """Return the name of the request view."""
        return 'allocation_renewal_request_under_project_view'

    def test_post_sets_request_request_time(self):
        """Test that a POST request sets the request_time of the renewal
        request."""
        with enable_deployment(self._deployment_name):
            project, pi_project_user = self._create_project_to_renew()

            pre_time = utc_now_offset_aware()

            allocation_period = get_current_allowance_year_period()

            self._send_post_requests(
                allocation_period, project, pi_project_user)

            post_time = utc_now_offset_aware()

            requests = AllocationRenewalRequest.objects.all()
            self.assertEqual(requests.count(), 1)
            request = requests.first()
            self.assertTrue(pre_time <= request.request_time <= post_time)


class TestBRCAllocationRenewalRequestUnderProjectView(TestAllocationRenewalRequestUnderProjectViewMixin,
                                                      TestBase):
    """A class for testing AllocationRenewalRequestUnderProjectView on
    the BRC deployment."""

    @enable_deployment('BRC')
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self._deployment_name = 'BRC'

    def _send_post_requests(self, allocation_period, project, pi_project_user):
        """Send the necessary POST requests to the view for the given
        AllocationPeriod, Project, and PI ProjectUser."""
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

        renewal_survey_form_data = {
            '3-was_survey_completed': True,
            current_step_key: '3',
        }
        form_data.append(renewal_survey_form_data)

        review_and_submit_form_data = {
            '4-confirmation': True,
            current_step_key: '4',
        }
        form_data.append(review_and_submit_form_data)

        url = self._project_renew_url(project.pk)
        for i, data in enumerate(form_data):
            response = self.client.post(url, data)
            if i == len(form_data) - 1:
                self.assertRedirects(
                    response, self._project_detail_url(project.pk))
            else:
                self.assertEqual(response.status_code, HTTPStatus.OK)


class TestLRCAllocationRenewalRequestUnderProjectView(TestAllocationRenewalRequestUnderProjectViewMixin,
                                                      TestBase):
    """A class for testing AllocationRenewalRequestUnderProjectView on
    the LRC deployment."""

    @enable_deployment('LRC')
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self._deployment_name = 'LRC'

    def _send_post_requests(self, allocation_period, project, pi_project_user):
        """Send the necessary POST requests to the view for the given
        AllocationPeriod, Project, and PI ProjectUser."""
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

        billing_id_form_data = {
            '2-billing_id': '000000-000',
            current_step_key: '2',
        }
        form_data.append(billing_id_form_data)

        renewal_survey_form_data = {
            '3-was_survey_completed': True,
            current_step_key: '3',
        }
        form_data.append(renewal_survey_form_data)

        review_and_submit_form_data = {
            '4-confirmation': True,
            current_step_key: '4',
        }
        form_data.append(review_and_submit_form_data)

        url = self._project_renew_url(project.pk)
        for i, data in enumerate(form_data):
            response = self.client.post(url, data)
            if i == len(form_data) - 1:
                self.assertRedirects(
                    response, self._project_detail_url(project.pk))
            else:
                self.assertEqual(response.status_code, HTTPStatus.OK)
