from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.utils.tests.test_base import TestBase

from django.urls import reverse
from django.contrib.messages import get_messages


class TestProjectAddUsersSearchView(TestBase):
    """A class for testing ProjectAddUsersSearchView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)
    
    def test_error_raised_for_non_active_project(self):
        """TODO"""
        statuses = ['Active', 'Inactive', 'Archived', 'New']
        projects = []
        for status in statuses:
            name = f'{status.lower()}_project'
            status_obj = ProjectStatusChoice.objects.get(name=status)
            projects.append(Project.objects.create(
                name=name, title=name, status=status_obj))
        
        for i in range(1, len(projects)):
            url = reverse('project-add-users-search', 
                          kwargs={'pk': projects[i].pk})
            response = self.client.get(url)
            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), i)
            self.assertEqual(str(messages[i - 1]), 
                f'You cannot add users to a project with status {statuses[i]}')