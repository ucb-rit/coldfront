from copy import deepcopy
from http import HTTPStatus
from importlib import reload
from unittest.mock import patch

from django.conf import settings as django_settings
from django.test import override_settings
from django.urls import reverse

from coldfront.core.utils.tests.test_base import TransactionTestBase
from coldfront.plugins.departments.conf import settings
from coldfront.plugins.departments.models import Department
from coldfront.plugins.departments.models import HistoricalUserDepartment
from coldfront.plugins.departments.models import UserDepartment


Q_CLUSTER_COPY = deepcopy(django_settings.Q_CLUSTER)
Q_CLUSTER_COPY['sync'] = True


@override_settings(
    Q_CLUSTER=Q_CLUSTER_COPY,
    DEPARTMENTS_DEPARTMENT_DATA_SOURCE=(
        'coldfront.plugins.departments.utils.data_sources.backends.dummy.'
        'DummyDataSourceBackend')
)
class TestUpdateDepartmentsView(TransactionTestBase):
    """A class for testing UpdateDepartmentsView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # conf.settings needs to be reloaded after the override.
        reload(settings)

        self.create_test_user()
        self.client.login(username=self.user.username, password=self.password)

        self.department1, _ = Department.objects.get_or_create(
            name='Department 1', code='DEPT1')
        self.department2, _ = Department.objects.get_or_create(
            name='Department 2', code='DEPT2')
        self.department3, _ = Department.objects.get_or_create(
            name='Department 3', code='DEPT3')

    def _assert_historical_user_departments(self, user, department,
                                            expected_history_types):
        """Assert that there are HistoricalUserDepartments between the
        given User and Department, with history types matching the ones
        in the given ordered list."""
        historical_user_departments = HistoricalUserDepartment.objects.filter(
            user=user, department=department).order_by('history_id')
        self.assertEqual(
            historical_user_departments.count(), len(expected_history_types))
        actual_history_types = list(
            historical_user_departments.values_list('history_type', flat=True))
        self.assertEqual(actual_history_types, expected_history_types)

    def _assert_user_departments(self, user,
                                 expected_departments_name_and_is_authoritative):
        """Given a User and a dict mapping the names of departments the
        user is expected to be in to whether the association is expected
        to be authoritative, return whether the user is in those
        departments with the expected association."""
        user_departments = UserDepartment.objects.filter(user=user)
        for user_department in user_departments:
            department_name = user_department.department.name
            self.assertIn(
                department_name, expected_departments_name_and_is_authoritative)
            expected_is_authoritative = \
                expected_departments_name_and_is_authoritative.pop(
                    department_name)
            self.assertEqual(
                user_department.is_authoritative, expected_is_authoritative)
        self.assertFalse(expected_departments_name_and_is_authoritative)

    def _assert_redirects(self, response):
        """Assert that the given response involves being redirected to
        the expected success URL (the user profile)."""
        success_url = reverse('user-profile')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response, success_url)

    @staticmethod
    def _request_url():
        """Return the URL for requesting to update the user's
        departments."""
        return reverse('update-departments')

    def test_departments_required(self):
        """Test that an error is raised if no departments are provided."""
        UserDepartment.objects.create(
            user=self.user,
            department=self.department1)

        form_data = {
            'departments': [],
        }
        response = self.client.post(self._request_url(), form_data)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, 'This field is required.')

        self.assertEqual(UserDepartment.objects.count(), 1)

        try:
            UserDepartment.objects.get(
                user=self.user, department=self.department1)
        except UserDepartment.DoesNotExist:
            self.fail('The user\'s UserDepartment should not have been unset.')

    def test_sets_selected_departments_non_authoritatively(self):
        """Test that a POST request updates the user's non-authoritative
        departments, retaining history."""
        self.user.first_name = ''
        self.user.last_name = ''
        self.user.save()

        self.assertEqual(UserDepartment.objects.count(), 0)
        self.assertEqual(HistoricalUserDepartment.objects.count(), 0)

        # Set department1.
        form_data = {
            'departments': [self.department1.pk],
        }
        response = self.client.post(self._request_url(), form_data)
        self._assert_redirects(response)

        user_departments = UserDepartment.objects.filter(user=self.user)
        self.assertEqual(user_departments.count(), 1)

        user_department_1 = user_departments.first()
        self.assertEqual(user_department_1.department, self.department1)
        self.assertFalse(user_department_1.is_authoritative)

        self._assert_historical_user_departments(
            self.user, self.department1, ['+'])

        # Set department2 and department3, unsetting department 1.
        form_data = {
            'departments': [self.department2.pk, self.department3.pk],
        }
        response = self.client.post(self._request_url(), form_data)
        self._assert_redirects(response)

        user_departments = UserDepartment.objects.filter(user=self.user)
        self.assertEqual(user_departments.count(), 2)

        user_department_2 = user_departments.get(department=self.department2)
        user_department_3 = user_departments.get(department=self.department3)
        self.assertFalse(user_department_2.is_authoritative)
        self.assertFalse(user_department_3.is_authoritative)

        self._assert_historical_user_departments(
            self.user, self.department1, ['+', '-'])
        self._assert_historical_user_departments(
            self.user, self.department2, ['+'])
        self._assert_historical_user_departments(
            self.user, self.department3, ['+'])

        # Set department2, unsetting department3.
        form_data = {
            'departments': [self.department2.pk],
        }
        response = self.client.post(self._request_url(), form_data)
        self._assert_redirects(response)

        user_departments = UserDepartment.objects.filter(user=self.user)
        self.assertEqual(user_departments.count(), 1)

        user_department_2 = user_departments.get(department=self.department2)
        self.assertFalse(user_department_2.is_authoritative)

        self._assert_historical_user_departments(
            self.user, self.department1, ['+', '-'])
        self._assert_historical_user_departments(
            self.user, self.department2, ['+', '~'])
        self._assert_historical_user_departments(
            self.user, self.department3, ['+', '-'])

    @override_settings(
        DEPARTMENTS_DEPARTMENT_DATA_SOURCE=(
            'coldfront.plugins.departments.utils.data_sources.backends.dummy.'
            'DummyDataSourceBackend'))
    def test_creates_data_source_departments_and_sets_authoritatively(self):
        """Test that a POST request attempts to fetch departments from a
        data source backend, creates Departments, and updates the user's
        authoritative departments."""
        self.user.first_name = 'First'
        self.user.last_name = 'Last'
        self.user.save()

        self.assertFalse(UserDepartment.objects.filter(user=self.user).exists())
        self.assertFalse(
            Department.objects.filter(name='Department F').exists())
        self.assertFalse(
            Department.objects.filter(name='Department L').exists())

        form_data = {
            'departments': [self.department1.pk],
        }
        response = self.client.post(self._request_url(), form_data)
        self._assert_redirects(response)

        self.assertTrue(Department.objects.filter(name='Department F').exists())
        self.assertTrue(Department.objects.filter(name='Department L').exists())

        expected_departments_name_and_is_authoritative = {
            'Department 1': False,
            'Department F': True,
            'Department L': True,
        }
        self._assert_user_departments(
            self.user, expected_departments_name_and_is_authoritative)

    def test_no_departments_found_in_data_source(self):
        """Test that, if no departments for the user are found in the
        data source backend, none are set authoritatively."""
        self.user.first_name = '1'
        self.user.last_name = '2'
        self.user.save()

        self.assertFalse(UserDepartment.objects.filter(user=self.user).exists())

        form_data = {
            'departments': [self.department1.pk],
        }
        response = self.client.post(self._request_url(), form_data)
        self._assert_redirects(response)

        expected_departments_name_and_is_authoritative = {
            'Department 1': False,
        }
        self._assert_user_departments(
            self.user, expected_departments_name_and_is_authoritative)

    def test_authoritative_not_overridden_as_non_authoritative(self):
        """Test that, if a department is set authoritatively for a user,
        the user cannot set it as non-authoritative."""
        self.user.first_name = 'First'
        self.user.last_name = 'Last'
        self.user.save()

        # The user is not already associated with Department F.
        department_f = Department.objects.create(
            name='Department F', code='DEPTF')

        # The user attempts to set F as non-authoritative.
        form_data = {
            'departments': [self.department1.pk, department_f.pk],
        }
        response = self.client.post(self._request_url(), form_data)
        self._assert_redirects(response)

        # F is still set authoritatively.
        expected_departments_name_and_is_authoritative = {
            'Department 1': False,
            'Department F': True,
            'Department L': True,
        }
        self._assert_user_departments(
            self.user, expected_departments_name_and_is_authoritative)

        # The user is already associated with Department F. The user attempts
        # to set F as non-authoritative.
        form_data = {
            'departments': [self.department1.pk, department_f.pk],
        }
        response = self.client.post(self._request_url(), form_data)
        self._assert_redirects(response)

        # F is still set authoritatively.
        expected_departments_name_and_is_authoritative = {
            'Department 1': False,
            'Department F': True,
            'Department L': True,
        }
        self._assert_user_departments(
            self.user, expected_departments_name_and_is_authoritative)

    def test_outdated_authoritative_departments_unset(self):
        """Test that the view removes any authoritatively-associated
        departments that are no longer returned by the data source."""
        self.user.first_name = 'First'
        self.user.last_name = 'Last'
        self.user.save()

        # The user is already authoritatively associated with Department M.
        department_m = Department.objects.create(
            name='Department M', code='DEPTM')
        UserDepartment.objects.create(
            user=self.user, department=department_m, is_authoritative=True)

        form_data = {
            'departments': [self.department1.pk],
        }
        response = self.client.post(self._request_url(), form_data)
        self._assert_redirects(response)

        # M is no longer set.
        expected_departments_name_and_is_authoritative = {
            'Department 1': False,
            'Department F': True,
            'Department L': True,
        }
        self._assert_user_departments(
            self.user, expected_departments_name_and_is_authoritative)

    def test_data_source_error_authoritative_unaffected(self):
        """Test that, if an error occurs when fetching department data
        from the data source, authoritative department associations are
        unaffected."""
        self.user.first_name = 'First'
        self.user.last_name = 'Last'
        self.user.save()

        # The user is already authoritatively associated with Department M.
        department_m = Department.objects.create(
            name='Department M', code='DEPTM')
        UserDepartment.objects.create(
            user=self.user, department=department_m, is_authoritative=True)

        form_data = {
            'departments': [self.department1.pk],
        }

        def raise_exception(*args, **kwargs):
            raise Exception('Test exception.')

        method_to_patch = (
            'coldfront.plugins.departments.utils.queries.'
            'fetch_departments_for_user')
        with patch(method_to_patch) as patched_method:
            patched_method.side_effect = raise_exception
            response = self.client.post(self._request_url(), form_data)
            self._assert_redirects(response)

        # M is still set authoritatively.
        expected_departments_name_and_is_authoritative = {
            'Department 1': False,
            'Department M': True,
        }
        self._assert_user_departments(
            self.user, expected_departments_name_and_is_authoritative)
