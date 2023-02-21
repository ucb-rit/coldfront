from coldfront.core.utils.tests.test_base import TestBase
from coldfront.core.department.models import Department
from coldfront.core.department.models import UserDepartment
from django.urls import reverse

from http import HTTPStatus

class TestAddDepartments(TestBase):
    """A class for testing the "Update Departments" section of
    the User Profile."""
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.client.login(username=self.user.username, password=self.password)
    
    @staticmethod
    def request_url():
        """Return the URL for requesting to update the user's
        departments."""
        return reverse('update-departments')
    
    def test_post_updates_departments(self):
        """Test that a POST request updates the user's
        departments."""
        self.assertEqual(UserDepartment.objects.count(), 0)
        department = Department.objects.get_or_create(name='Department 1', code='DEPT1')[0]
        form_data = {
            'departments': [department.pk],
        }
        response = self.client.post(self.request_url(), form_data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(UserDepartment.objects.count(), 1)
        self.assertTrue(UserDepartment.objects.filter(
                                        userprofile=self.user.userprofile,
                                        department=department,
                                        is_authoritative=False).exists())

        department2 = Department.objects.get_or_create(name='Department 2', code='DEPT2')[0]
        form_data = {
            'departments': [department2.pk],
        }
        response = self.client.post(self.request_url(), form_data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(UserDepartment.objects.count(), 1)
        self.assertTrue(UserDepartment.objects.filter(
                                        userprofile=self.user.userprofile,
                                        department=department2,
                                        is_authoritative=False).exists())

        form_data = {
            'departments': [],
        }
        response = self.client.post(self.request_url(), form_data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(UserDepartment.objects.count(), 0)