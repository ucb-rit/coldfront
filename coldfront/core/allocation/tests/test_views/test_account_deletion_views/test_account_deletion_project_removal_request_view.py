import re
from http import HTTPStatus

from django.urls import reverse

from coldfront.core.allocation.tests.test_account_deletion_base import \
    TestAccountDeletionBase
from coldfront.core.project.models import ProjectUserStatusChoice, \
    ProjectUserRemovalRequest


class TestAccountDeletionRequestRemoveProjectsView(TestAccountDeletionBase):
    """Testing class for AccountDeletionRequestRemoveProjectsView"""

    def setUp(self):
        super().setUp()
        self.create_account_deletion_request(self.user, 'Processing', 'User')
        self.url = reverse('cluster-account-deletion-request-project-removal',
                           kwargs={'pk': self.request.pk})

        self.detail_url = reverse('cluster-account-deletion-request-detail',
                                  kwargs={'pk': self.request.pk})

    def remove_proj_user(self, proj_user):
        proj_user.status = ProjectUserStatusChoice.objects.get(name='Removed')
        proj_user.save()

    def test_access(self):
        self.assert_has_access(self.url, self.superuser, True)
        self.assert_has_access(self.url, self.staff_user, False)
        self.assert_has_access(self.url, self.user, False)
        self.assert_has_access(self.url, self.user2, False)

    def test_projects_displayed_correctly(self):
        """Test that active projects are displayed and superuse has
        the option to request removals."""
        self.remove_proj_user(self.project_user2)

        response = self.get_response(self.superuser, self.url)
        self.assertTrue(response.status_code, HTTPStatus.OK)

        html = response.content.decode('utf-8')

        # Active projects are normally displayed
        for proj_user in [self.project_user0, self.project_user1]:
            proj_name = f'<td>{proj_user.project.name}</td>'
            self.assertIn(proj_name, html)

        # Active badge should appear 2 times.
        badge_regex = '<td><span class="badge badge-success">Active<\/span><\/td>'
        occurences = re.findall(badge_regex, html)
        self.assertEqual(len(occurences), 2)

        # Removed projects are muted.
        proj_name = f'<td><div class="text-muted">' \
                    f'{self.project_user2.project.name}</div></td>'
        badge = '<td><div class="text-muted"><span class="badge badge-danger">' \
                'Removed</span></div></td>'
        self.assertIn(proj_name, html)
        self.assertIn(badge, html)

    def test_request_proj_removal_button(self):
        """Tests that the button to request project removals is
        correctly displayed."""

        # Button is not disabled if there are active projects users.
        for proj_user in [self.project_user0, self.project_user1]:
            self.remove_proj_user(proj_user)

        # There is one project user left to remove.
        response = self.get_response(self.superuser, self.url)
        self.assertTrue(response.status_code, HTTPStatus.OK)
        html = response.content.decode('utf-8')
        self.assertIn('Request Project Removal', html)

        # Remove the last project.
        self.remove_proj_user(self.project_user2)
        response = self.get_response(self.superuser, self.url)
        self.assertTrue(response.status_code, HTTPStatus.OK)
        html = response.content.decode('utf-8')
        self.assertNotIn('Request Project Removal', html)

    def test_post_request_creates_removal_requests(self):
        """Tests that POST requests create the correct project removal
        request."""
        # Requesting to remove user from project0 and project2.
        form_data = {'projectform-TOTAL_FORMS': ['3'],
                     'projectform-INITIAL_FORMS': ['1'],
                     'projectform-MIN_NUM_FORMS': ['0'],
                     'projectform-MAX_NUM_FORMS': ['3'],
                     'projectform-0-selected': ['on'],
                     'projectform-1-selected': ['off'],
                     'projectform-2-selected': ['on']}

        response = self.post_response(self.superuser, self.url, form_data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response, self.url)

        # ProjectUserRemovalRequest should be created. ProjectUser status
        # should be 'Pending - Remove'
        for proj_user in [self.project_user0, self.project_user2]:
            proj_removal_requests = \
                ProjectUserRemovalRequest.objects.filter(
                    project_user=proj_user)
            self.assertTrue(proj_removal_requests.exists())
            proj_user.refresh_from_db()
            self.assertEqual(proj_user.status.name, 'Pending - Remove')

        self.assertEqual(self.project_user1.status.name, 'Active')
