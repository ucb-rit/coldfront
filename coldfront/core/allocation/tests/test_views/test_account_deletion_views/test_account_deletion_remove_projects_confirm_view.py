from http import HTTPStatus

from django.urls import reverse
from iso8601 import iso8601

from coldfront.core.allocation.tests.test_account_deletion_base import \
    TestAccountDeletionBase
from coldfront.core.project.models import ProjectUserStatusChoice, ProjectUser
from coldfront.core.utils.common import utc_now_offset_aware


class TestAccountDeletionRequestRemoveProjectsConfirmView(TestAccountDeletionBase):
    """Testing class for AccountDeletionRequestRemoveProjectsConfirmView"""

    def setUp(self):
        super().setUp()
        self.create_account_deletion_request(self.user, 'Queued', 'User')
        self.url = reverse('cluster-account-deletion-request-project-removal-confirm',
                           kwargs={'pk': self.request.pk})

        self.proj_removal_url = reverse('cluster-account-deletion-request-project-removal',
                                        kwargs={'pk': self.request.pk})

        self.detail_url = reverse('cluster-account-deletion-request-detail',
                                  kwargs={'pk': self.request.pk})

    def remove_projects(self):
        proj_users = ProjectUser.objects.filter(user=self.user)
        for proj_user in proj_users:
            proj_user.status = ProjectUserStatusChoice.objects.get(name='Removed')
            proj_user.save()

    def test_access(self):
        def _assert_has_access(url, user, has_access):
            self.client.login(username=user.username, password=self.password)
            status_code = HTTPStatus.FOUND if has_access else HTTPStatus.FORBIDDEN
            response = self.client.post(url, {})
            self.assertEqual(response.status_code, status_code)
            self.client.logout()

        self.remove_projects()
        _assert_has_access(self.url, self.superuser, True)
        _assert_has_access(self.url, self.staff_user, False)
        _assert_has_access(self.url, self.user, False)
        _assert_has_access(self.url, self.user2, False)

    def test_redirect(self):
        """Test that the correct redirect is performed."""
        # User is still part of 3 projects.
        response = self.post_response(self.superuser, self.url, {})
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response, self.proj_removal_url)

        # Remove user from all projects.
        self.remove_projects()
        response = self.post_response(self.superuser, self.url, {})
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response, self.detail_url)

    def test_post_updates_request(self):
        """Test that a valid POST request updates the request."""
        self.remove_projects()
        pre_time = utc_now_offset_aware()
        response = self.post_response(self.superuser, self.url, {})
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response, self.detail_url)

        self.request.refresh_from_db()
        self.assertEqual(self.request.status.name, 'Processing')
        self.assertEqual(self.request.state['project_removal']['status'],
                         'Complete')

        timestamp = \
            iso8601.parse_date(self.request.state['project_removal']['timestamp'])
        post_time = utc_now_offset_aware()
        self.assertTrue(pre_time <= timestamp <= post_time)
