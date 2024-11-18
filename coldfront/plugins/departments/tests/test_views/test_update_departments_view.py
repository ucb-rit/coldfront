from http import HTTPStatus

from django.urls import reverse

from coldfront.core.utils.tests.test_base import TestBase
from coldfront.plugins.departments.models import Department
from coldfront.plugins.departments.models import HistoricalUserDepartment
from coldfront.plugins.departments.models import UserDepartment


class TestUpdateDepartmentsView(TestBase):
    """A class for testing UpdateDepartmentsView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

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

    def test_post_updates_departments(self):
        """Test that a POST request updates the user's non-authoritative
        departments, retaining history."""
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
            self.user, self.department2, ['+'])
        self._assert_historical_user_departments(
            self.user, self.department3, ['+', '-'])

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
