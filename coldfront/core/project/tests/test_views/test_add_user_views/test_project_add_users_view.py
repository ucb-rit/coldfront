from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.utils.tests.test_base import TestBase

from django.urls import reverse
from django.contrib.messages import get_messages


class TestProjectAddUsersView(TestBase):
    """A class for testing ProjectAddUsersView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)
        self.user.is_superuser = True
        self.user.save()

    def test_error_raised_for_non_active_project(self):
        """Test that an error and error message appear when trying to add users
        to 'Archived', 'New', or 'Inactive' Projects and doesn't appear for 
        'Active' Projects"""
        statuses = ['Active', 'Inactive', 'Archived', 'New']
        projects = []
        for status in statuses:
            name = f'{status.lower()}_project'
            status_obj = ProjectStatusChoice.objects.get(name=status)
            projects.append(Project.objects.create(
                name=name, title=name, status=status_obj))
        
        # Check that for the active project there is no error message.
        url = reverse('project-add-users', kwargs={'pk': projects[0].pk})
        response = self.client.get(url)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 0)

        for i in range(1, len(projects)):
            url = reverse('project-add-users', kwargs={'pk': projects[i].pk})
            response = self.client.get(url)
            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), i)
            self.assertEqual(str(messages[i - 1]), 
                f'You cannot add users to a project with status {statuses[i]}')

