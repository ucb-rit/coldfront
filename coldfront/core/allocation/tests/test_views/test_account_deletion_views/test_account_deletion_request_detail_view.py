from http import HTTPStatus

from django.urls import reverse

from coldfront.core.allocation.models import AccountDeletionRequestStatusChoice
from coldfront.core.allocation.tests.test_account_deletion_base import \
    TestAccountDeletionBase


class TestAccountDeletionRequestDetailView(TestAccountDeletionBase):
    """Testing class for AccountDeletionRequestDetailView"""

    def setUp(self):
        super().setUp()
        self.create_account_deletion_request(self.user, 'Queued', 'Admin')
        self.url = reverse('cluster-account-deletion-request-detail',
                           kwargs={'pk': self.request.pk})

    def _change_request_status(self, status_name):
        self.request.status = \
            AccountDeletionRequestStatusChoice.objects.get(name=status_name)
        self.request.save()

    def test_access(self):
        self.assert_has_access(self.url, self.superuser, True)
        self.assert_has_access(self.url, self.staff_user, True)
        self.assert_has_access(self.url, self.user, True)
        self.assert_has_access(self.url, self.user2, False)

    def test_admin_checklist(self):
        """Test that the admin checklist is shown depending on the
        state of the request."""

        def _assert_checklist(user, visible):
            response = self.get_response(user, self.url)
            self.assertEqual(response.status_code, HTTPStatus.OK)
            html = response.content.decode('utf-8')
            if visible:
                self.assertIn('System Administrator Checklist', html)
            else:
                self.assertNotIn('System Administrator Checklist', html)

        # Checklist should not be visible when the request is
        # Queued, Complete or Cancelled.
        for status_name in ['Queued', 'Complete', 'Cancelled']:
            self._change_request_status(status_name)
            _assert_checklist(self.superuser, False)
            _assert_checklist(self.staff_user, False)
            _assert_checklist(self.user, False)

        # Checklist should be visible only when the request is
        # Ready or Processing.
        for status_name in ['Ready', 'Processing']:
            self._change_request_status(status_name)
            _assert_checklist(self.superuser, True)
            _assert_checklist(self.staff_user, False)
            _assert_checklist(self.user, False)

    def test_user_checklist(self):
        """Test that the admin checklist is shown depending on the
        state of the request."""

        def _assert_checklist(user, visible):
            response = self.get_response(user, self.url)
            self.assertEqual(response.status_code, HTTPStatus.OK)
            html = response.content.decode('utf-8')
            if visible:
                self.assertIn('User Checklist', html)
            else:
                self.assertNotIn('User Checklist', html)

        # Checklist should not be visible when the request is
        # Complete or Cancelled.
        for status_name in ['Complete', 'Cancelled']:
            self._change_request_status(status_name)
            _assert_checklist(self.superuser, False)
            _assert_checklist(self.staff_user, False)
            _assert_checklist(self.user, False)

        # Checklist should be visible only when the request is
        # Queued, Ready or Processing.
        for status_name in ['Ready', 'Queued', 'Processing']:
            self._change_request_status(status_name)
            _assert_checklist(self.superuser, False)
            _assert_checklist(self.staff_user, False)
            _assert_checklist(self.user, True)

    def test_post_completes_request(self):
        """Test that a POST request completes the request."""
        self.complete_request_checklist(self.request)
        self._change_request_status('Processing')

        self.assertEqual(self.request.status.name, 'Processing')

        response = self.post_response(self.superuser, self.url, {})
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response,
                             reverse('cluster-account-deletion-request-list'))

        self.request.refresh_from_db()
        self.assertEqual(self.request.status.name, 'Complete')
