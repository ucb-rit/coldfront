from coldfront.core.project.forms_.renewal_forms.request_forms import ProjectRenewalSurveyForm
from coldfront.core.project.models import Project, ProjectStatusChoice, ProjectUser, ProjectUserRoleChoice, ProjectUserStatusChoice
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.tests.test_base import TestBase
from coldfront.core.project.utils_.renewal_survey.backends.base import BaseRenewalSurveyBackend

from django.contrib.auth.models import User
from django.test import override_settings


@override_settings(RENEWAL_SURVEY = {
    'backend': 'coldfront.core.project.tests.test_forms.test_renewal_forms.test_project_renewal_survey_form.DummyRenewalSurveyBackend',
    'details': {},
})
class TestProjectRenewalSurveyForm(TestBase):
    """A class for testing ProjectRenewalSurveyForm."""
    def setUp(self):
        """Set up test data."""
        super().setUp()
        computing_allowance_interface = ComputingAllowanceInterface()
        computing_allowance = self.get_predominant_computing_allowance()
        self._project_prefix = computing_allowance_interface.code_from_name(
            computing_allowance.name)
        
        self.allocation_period = get_current_allowance_year_period()

        self.pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        self.active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        
    def test_is_renewal_survey_completed_returns_false(self):
        user = User.objects.create(
            email='test_user@email.com',
            first_name='Test',
            last_name='User',
            username='test_user')

        project_name = f'{self._project_prefix}project'
        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        project = Project.objects.create(
            name=project_name,
            title=project_name,
            status=active_project_status)
        self.project_user = ProjectUser.objects.create(
            project=project,
            role=self.pi_role,
            status=self.active_project_user_status,
            user=user)
        
        form=ProjectRenewalSurveyForm(
            project_name=project_name,
            pi_username=user.username,
            allocation_period_name=self.allocation_period.name,
            data={'was_survey_completed': True}
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            f'No response for {user.username} and {project_name} detected', 
            str(form.errors))
    
    def test_is_renewal_survey_completed_returns_true(self):
        user = User.objects.create(
            email='test_user@email.com',
            first_name='Test',
            last_name='User',
            username='test')

        project_name = f'{self._project_prefix}project2'
        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        project = Project.objects.create(
            name=project_name,
            title=project_name,
            status=active_project_status)
        self.project_user = ProjectUser.objects.create(
            project=project,
            role=self.pi_role,
            status=self.active_project_user_status,
            user=user)
        
        form=ProjectRenewalSurveyForm(
            project_name=project_name,
            pi_username=user.username,
            allocation_period_name=self.allocation_period.name,
            data={'was_survey_completed': True}
        )

        self.assertTrue(form.is_valid())

class DummyRenewalSurveyBackend(BaseRenewalSurveyBackend):
    """A backend similar to PermissiveRenewalSurveyBackend except 
    is_renewal_survey_completed returns True/False based on pi_username."""

    def is_renewal_survey_completed(self, allocation_period_name, project_name,
                                    pi_username):
        """Return whether the pi_username is less than 5 characters long."""
        return len(pi_username) < 5

    def get_renewal_survey_response(self, allocation_period_name, project_name, 
                                    pi_username):
        """Return an empty list of responses."""
        return []

    def get_renewal_survey_url(self, allocation_period_name, pi, project_name,
                               requester):
        """Return an empty string."""
        return ''
