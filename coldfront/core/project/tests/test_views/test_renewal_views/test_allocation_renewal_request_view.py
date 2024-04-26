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

    @staticmethod
    def renew_pi_allocation_url():
        """Return the URL for requesting to renew a PI's allocation."""
        return reverse('renew-pi-allocation')

    def test_post_sets_request_request_time(self):
        """Test that a POST request sets the request_time of the renewal
        request."""
        computing_allowance_interface = ComputingAllowanceInterface()
        computing_allowance = self.get_predominant_computing_allowance()
        project_name_prefix = computing_allowance_interface.code_from_name(
            computing_allowance.name)

        # Create a Project for the user to renew.
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

        pre_time = utc_now_offset_aware()

        allocation_period = get_current_allowance_year_period()

        renewal_survey = [
            {"which_brc_services_used":"srdc"},
            {"publications_supported_by_brc":"N/A"},
            {"grants_supported_by_brc":"N/A"},
            {"recruitment_or_retention_cases":"N/A"},
            {"classes_being_taught":"N/A"},
            {"brc_recommendation_rating":6},
            {"brc_recommendation_rating_reason":""},
            {"how_brc_helped_bootstrap_computational_methods":"N/A"},
            {"how_important_to_research_is_brc":2},
            {"do_you_use_mybrc":"no"},
            {"mybrc_comments":""},
            {"which_open_ondemand_apps_used":"jupyter_notebook"},
            {"which_open_ondemand_apps_used":"vscode_server"},
            {"brc_feedback":""},
            {"colleague_suggestions":""},
            {"indicate_topic_interests":"have_had_rdmp_event_or_consultation"},
            {"indicate_topic_interests":"want_to_learn_more_and_have_rdm_consult"},
            {"training_session_usefulness_of_computational_platforms_training":2},
            {"training_session_usefulness_of_basic_savio_cluster":4},
            {"training_session_other_topics_of_interest":""}
                ]
        
        view_name = 'allocation_renewal_request_view'
        current_step_key = f'{view_name}-current_step'

        allocation_period_form_data = {
            '0-allocation_period': allocation_period.pk,
            current_step_key: '0',
        }
        pi_selection_form_data = {
            '1-PI': project_user.pk,
            current_step_key: '1',
        }
        pooling_preference_form_data = {
            '2-preference':
                AllocationRenewalRequest.UNPOOLED_TO_UNPOOLED,
            current_step_key: '2',
        }

        renewal_survey_form_data = {}
        for data in renewal_survey:
            for key, value in data.items():
                renewal_survey_form_data[f"6-{key}"] = value
        renewal_survey_form_data[current_step_key] = '6'

        review_and_submit_form_data = {
            '7-confirmation': True,
            current_step_key: '7',
        }
        form_data = [
            allocation_period_form_data,
            pi_selection_form_data,
            pooling_preference_form_data,
            renewal_survey_form_data,
            review_and_submit_form_data,
        ]

        url = self.renew_pi_allocation_url()
        for i, data in enumerate(form_data):
            response = self.client.post(url, data)
            if i == len(form_data) - 1:
                self.assertRedirects(response, reverse('home'))
            else:
                self.assertEqual(response.status_code, HTTPStatus.OK)

        post_time = utc_now_offset_aware()

        requests = AllocationRenewalRequest.objects.all()
        self.assertEqual(requests.count(), 1)
        request = requests.first()
        self.assertTrue(pre_time <= request.request_time <= post_time)
