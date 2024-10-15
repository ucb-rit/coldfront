from coldfront.core.project.models import Project
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectExistingPIForm
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.plugins.ucb_departments.models import Department
from coldfront.plugins.ucb_departments.models import UserDepartment
from coldfront.core.utils.tests.test_base import enable_deployment
from coldfront.core.utils.tests.test_base import TestBase
from django.urls import reverse
from http import HTTPStatus


class TestSavioProjectRequestWizard(TestBase):
    """A class for testing SavioProjectRequestWizard."""

    @enable_deployment('BRC')
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

        self.interface = ComputingAllowanceInterface()

    @staticmethod
    def request_url():
        """Return the URL for requesting to create a new Savio
        project."""
        return reverse('new-project-request')

    @enable_deployment('BRC')
    def test_post_creates_request(self):
        """Test that a POST request creates a
        SavioProjectAllocationRequest."""
        self.assertEqual(SavioProjectAllocationRequest.objects.count(), 0)
        self.assertEqual(Project.objects.count(), 0)

        computing_allowance = self.get_predominant_computing_allowance()
        allocation_period = get_current_allowance_year_period()

        kwargs = {
            'computing_allowance': computing_allowance,
            'allocation_period': allocation_period,
        }

        # The PI should not be selectable.
        self.user.is_active = False
        self.user.save()
        form = SavioProjectExistingPIForm(**kwargs)
        pi_field_queryset = \
            form.fields['PI'].queryset
        self.assertNotIn(self.user, pi_field_queryset)

        # The PI should be selectable.
        self.user.is_active = True
        self.user.save()
        form = SavioProjectExistingPIForm(**kwargs)
        pi_field_queryset = \
            form.fields['PI'].queryset
        self.assertIn(self.user, pi_field_queryset)

        selected_dept = Department.objects.get_or_create(name='Department 1', code='DEPT1')[0]
        not_selected_dept = Department.objects.get_or_create(name='Department 2', code='DEPT2')[0]

        view_name = 'savio_project_request_wizard'
        current_step_key = f'{view_name}-current_step'
        computing_allowance_form_data = {
            '0-computing_allowance': computing_allowance.pk,
            current_step_key: '0',
        }
        allocation_period_form_data = {
            '1-allocation_period': allocation_period.pk,
            current_step_key: '1',
        }
        existing_pi_form_data = {
            '2-PI': self.user.pk,
            current_step_key: '2',
        }
        pi_department_form_data = {
            '4-departments': [selected_dept.pk],
            current_step_key: '4'
        }
        pool_allocations_data = {
            '7-pool': False,
            current_step_key: '7',
        }
        details_data = {
            '9-name': 'name',
            '9-title': 'title',
            '9-description': 'a' * 20,
            current_step_key: '9',
        }
        survey_data = {
            '11-scope_and_intent': 'b' * 20,
            '11-computational_aspects': 'c' * 20,
            current_step_key: '11',
        }
        form_data = [
            computing_allowance_form_data,
            allocation_period_form_data,
            existing_pi_form_data,
            pi_department_form_data,
            pool_allocations_data,
            details_data,
            survey_data,
        ]

        url = self.request_url()
        for i, data in enumerate(form_data):
            response = self.client.post(url, data)
            if i == len(form_data) - 1:
                self.assertRedirects(response, reverse('home'))
            else:
                self.assertEqual(response.status_code, HTTPStatus.OK)

        requests = SavioProjectAllocationRequest.objects.all()
        self.assertEqual(requests.count(), 1)
        projects = Project.objects.all()
        self.assertEqual(projects.count(), 1)
        self.assertEqual(UserDepartment.objects.count(), 1)
        self.assertTrue(UserDepartment.objects.filter(
                                        userprofile=self.user.userprofile,
                                        department=selected_dept,
                                        is_authoritative=False).exists())
        request = requests.first()
        project = projects.first()
        self.assertEqual(request.requester, self.user)
        self.assertEqual(
            request.allocation_type,
            self.interface.name_short_from_name(computing_allowance.name))
        self.assertEqual(request.computing_allowance, computing_allowance)
        self.assertEqual(request.allocation_period, allocation_period)
        self.assertEqual(request.pi, self.user)
        self.assertEqual(request.project, project)
        self.assertEqual(project.name, f'fc_{details_data["9-name"]}')
        self.assertEqual(project.title, details_data['9-title'])
        self.assertEqual(project.description, details_data['9-description'])
        self.assertFalse(request.pool)
        self.assertEqual(
            request.survey_answers['scope_and_intent'],
            survey_data['11-scope_and_intent'])
        self.assertEqual(
            request.survey_answers['computational_aspects'],
            survey_data['11-computational_aspects'])
        self.assertEqual(request.status.name, 'Under Review')



    
    # TODO
