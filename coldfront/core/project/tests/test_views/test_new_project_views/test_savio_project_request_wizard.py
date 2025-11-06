import importlib

from copy import deepcopy
from http import HTTPStatus

from django.conf import settings
from django.urls import clear_url_caches
from django.test import override_settings
from django.urls import reverse

from coldfront.config import urls
from coldfront.core.project.models import Project
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project import urls as project_urls
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.tests.test_base import enable_deployment
from coldfront.core.utils.tests.test_base import TransactionTestBase

from coldfront.plugins.departments.conf import settings as department_settings


FLAGS_COPY = deepcopy(settings.FLAGS)
FLAGS_COPY.pop('LRC_ONLY')
FLAGS_COPY['USER_DEPARTMENTS_ENABLED'] = [
    {'condition': 'boolean', 'value': True}]

INSTALLED_APPS_COPY = deepcopy(settings.INSTALLED_APPS)
if 'coldfront.plugins.departments' not in INSTALLED_APPS_COPY:
    INSTALLED_APPS_COPY.append('coldfront.plugins.departments')


@override_settings(FLAGS=FLAGS_COPY, INSTALLED_APPS=INSTALLED_APPS_COPY)
class TestSavioProjectRequestWizard(TransactionTestBase):
    """A class for testing SavioProjectRequestWizard."""

    @classmethod
    @enable_deployment('BRC')
    def setUpClass(cls):
        super().setUpClass()

        # Manually migrate the departments app.
        from django.core.management import call_command
        call_command('migrate', 'departments')

        # Import and store department models.
        from coldfront.plugins.departments.models import Department
        from coldfront.plugins.departments.models import UserDepartment
        cls._department_model = Department
        cls._user_department_model = UserDepartment

    @enable_deployment('BRC')
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

        self.interface = ComputingAllowanceInterface()

        self._department_1 = self._department_model.objects.create(
            name='Department 1', code='DEPT1')
        self._department_2 = self._department_model.objects.create(
            name='Department 2', code='DEPT2')

    @staticmethod
    def _request_url():
        """Return the URL for requesting to create a new Savio
        project."""
        return reverse('new-project-request')

    def _send_post_data(self, computing_allowance, allocation_period,
                        details_data, survey_data, new_pi_details=None,
                        existing_pi=None, pi_departments=None):
        """Send a POST request to the view with the given parameters.

        TODO: Some POST data should be made configurable (e.g.,
        pooling, etc.).
        """
        # TODO: This sequence of reloads and cache-clearing somehow gets the
        # enabling of the departments flag to be detected when the flag is
        # initially disabled in the settings file (e.g., on LRC development
        # instances). Further investigation is required to understand why.
        importlib.reload(project_urls)
        clear_url_caches()
        importlib.reload(urls)

        form_data = []

        view_name = 'savio_project_request_wizard'
        current_step_key = f'{view_name}-current_step'

        computing_allowance_form_data = {
            '0-computing_allowance': computing_allowance.pk,
            current_step_key: '0',
        }
        form_data.append(computing_allowance_form_data)

        allocation_period_form_data = {
            '1-allocation_period': allocation_period.pk,
            current_step_key: '1',
        }
        form_data.append(allocation_period_form_data)

        if existing_pi is not None:
            existing_pi_form_data = {
                '2-PI': existing_pi.pk,
                current_step_key: '2',
            }
            form_data.append(existing_pi_form_data)
        else:
            existing_pi_form_data = {
                '2-PI': '',
                current_step_key: '2',
            }
            form_data.append(existing_pi_form_data)

        if new_pi_details is not None:
            new_pi_details_form_data = {
                '3-first_name': new_pi_details['first_name'],
                '3-middle_name': new_pi_details.get('middle_name', ''),
                '3-last_name': new_pi_details['last_name'],
                '3-email': new_pi_details['email'],
                current_step_key: '3',
            }
            form_data.append(new_pi_details_form_data)

        if pi_departments is not None:
            pi_department_form_data = {
                '4-departments': [
                    department.pk for department in pi_departments],
                current_step_key: '4'
            }
            form_data.append(pi_department_form_data)

        pool_allocations_data = {
            '7-pool': False,
            current_step_key: '7',
        }
        form_data.append(pool_allocations_data)

        details_data_copy = {
            current_step_key: '9',
        }
        for key in details_data:
            details_data_copy[f'9-{key}'] = details_data[key]
        form_data.append(details_data_copy)

        survey_data_copy = {
            current_step_key: '11',
        }
        for key in survey_data:
            survey_data_copy[f'11-{key}'] = survey_data[key]
        form_data.append(survey_data_copy)

        url = self._request_url()
        for i, data in enumerate(form_data):
            response = self.client.post(url, data)
            if i == len(form_data) - 1:
                self.assertRedirects(response, reverse('home'))
            else:
                self.assertEqual(response.status_code, HTTPStatus.OK)

    @enable_deployment('BRC')
    @override_settings(FLAGS=FLAGS_COPY, INSTALLED_APPS=INSTALLED_APPS_COPY)
    def test_post_creates_pi_user_if_nonexistent(self):
        """Test that a POST creates a new, active User with the
        requester-provided details if the specified PI does not already
        exist."""
        computing_allowance = self.get_predominant_computing_allowance()
        allocation_period = get_current_allowance_year_period()
        details_data = {
            'name': 'name',
            'title': 'title',
            'description': 'a' * 20,
        }
        survey_data = {
            'scope_and_intent': 'b' * 20,
            'computational_aspects': 'c' * 20,
        }
        new_pi_details_data = {
            'first_name': 'Test',
            'middle_name': 'New',
            'last_name': 'PI',
            'email': 'test_pi@email.com',
        }

        self._send_post_data(
            computing_allowance, allocation_period, details_data, survey_data,
            new_pi_details=new_pi_details_data,
            pi_departments=[self._department_1])

        requests = SavioProjectAllocationRequest.objects.all()
        self.assertEqual(requests.count(), 1)
        projects = Project.objects.all()
        self.assertEqual(projects.count(), 1)
        request = requests.first()

        new_pi_user = request.pi
        self.assertEqual(
            new_pi_user.first_name, new_pi_details_data['first_name'])
        self.assertEqual(
            new_pi_user.userprofile.middle_name,
            new_pi_details_data['middle_name'])
        self.assertEqual(
            new_pi_user.last_name, new_pi_details_data['last_name'])
        self.assertEqual(new_pi_user.email, new_pi_details_data['email'])
        self.assertTrue(new_pi_user.is_active)

    @enable_deployment('BRC')
    @override_settings(FLAGS=FLAGS_COPY, INSTALLED_APPS=INSTALLED_APPS_COPY)
    def test_post_creates_request_and_project(self):
        """Test that a POST request creates a
        SavioProjectAllocationRequest and a Project."""
        self.assertEqual(SavioProjectAllocationRequest.objects.count(), 0)
        self.assertEqual(Project.objects.count(), 0)

        computing_allowance = self.get_predominant_computing_allowance()
        allocation_period = get_current_allowance_year_period()
        details_data = {
            'name': 'name',
            'title': 'title',
            'description': 'a' * 20,
        }
        survey_data = {
            'scope_and_intent': 'b' * 20,
            'computational_aspects': 'c' * 20,
        }

        self._send_post_data(
            computing_allowance, allocation_period, details_data, survey_data,
            existing_pi=self.user, pi_departments=[self._department_1])

        requests = SavioProjectAllocationRequest.objects.all()
        self.assertEqual(requests.count(), 1)
        projects = Project.objects.all()
        self.assertEqual(projects.count(), 1)
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

        details_data['name'] = f'fc_{details_data["name"]}'
        for key in details_data:
            self.assertEqual(getattr(project, key), details_data[key])

        self.assertFalse(request.pool)

        for key in survey_data:
            self.assertEqual(request.survey_answers[key], survey_data[key])

        self.assertEqual(request.status.name, 'Under Review')

    @enable_deployment('BRC')
    @override_settings(FLAGS=FLAGS_COPY, INSTALLED_APPS=INSTALLED_APPS_COPY)
    def test_post_sets_user_departments(self):
        """Test that a POST request sets authoritative and
        non-authoritative UserDepartments for the PI."""
        self.user.first_name = 'First'
        self.user.last_name = 'Last'
        self.user.save()

        self.assertFalse(
            self._user_department_model.objects.filter(user=self.user).exists())

        computing_allowance = self.get_predominant_computing_allowance()
        allocation_period = get_current_allowance_year_period()
        details_data = {
            'name': 'name',
            'title': 'title',
            'description': 'a' * 20,
        }
        survey_data = {
            'scope_and_intent': 'b' * 20,
            'computational_aspects': 'c' * 20,
        }

        Q_CLUSTER_COPY = deepcopy(settings.Q_CLUSTER)
        Q_CLUSTER_COPY['sync'] = True
        with override_settings(
                DEPARTMENTS_DEPARTMENT_DATA_SOURCE=(
                    'coldfront.plugins.departments.utils.data_sources.backends.'
                    'dummy.DummyDataSourceBackend'),
                Q_CLUSTER=Q_CLUSTER_COPY):
            # Reload the plugin's settings module to reflect the change in the
            # main app's settings module.
            importlib.reload(department_settings)

            self._send_post_data(
                computing_allowance, allocation_period, details_data,
                survey_data, existing_pi=self.user,
                pi_departments=[self._department_1])

        self.assertEqual(self._user_department_model.objects.count(), 3)
        self.assertTrue(
            self._user_department_model.objects.filter(
                user=self.user,
                department=self._department_1,
                is_authoritative=False).exists())
        self.assertTrue(
            self._user_department_model.objects.filter(
                user=self.user,
                department=self._department_model.objects.get(
                    name='Department F'),
                is_authoritative=True).exists())
        self.assertTrue(
            self._user_department_model.objects.filter(
                user=self.user,
                department=self._department_model.objects.get(
                    name='Department L'),
                is_authoritative=True).exists())

    # TODO
