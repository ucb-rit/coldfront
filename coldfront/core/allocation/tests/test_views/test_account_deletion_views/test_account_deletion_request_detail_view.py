from http import HTTPStatus

from django.urls import reverse

from coldfront.core.allocation.models import AccountDeletionRequestStatusChoice, \
    AccountDeletionRequestReasonChoice
from coldfront.core.allocation.tests.test_account_deletion_base import \
    TestAccountDeletionBase


class TestAccountDeletionRequestDetailView(TestAccountDeletionBase):
    """Testing class for AccountDeletionRequestDetailView"""

    def setUp(self):
        super().setUp()
        self.create_account_deletion_request(self.user, 'Queued', 'Admin')
        self.url = reverse('cluster-account-deletion-request-detail',
                           kwargs={'pk': self.request.pk})

    def change_request_status(self, status_name):
        self.request.status = \
            AccountDeletionRequestStatusChoice.objects.get(name=status_name)
        self.request.save()

    def change_request_reason(self, reason_name):
        self.request.reason = \
            AccountDeletionRequestReasonChoice.objects.get(name=reason_name)
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
            self.change_request_status(status_name)
            _assert_checklist(self.superuser, False)
            _assert_checklist(self.staff_user, False)
            _assert_checklist(self.user, False)

        # Checklist should be visible only when the request is
        # Ready or Processing.
        for status_name in ['Ready', 'Processing']:
            self.change_request_status(status_name)
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
            self.change_request_status(status_name)
            _assert_checklist(self.superuser, False)
            _assert_checklist(self.staff_user, False)
            _assert_checklist(self.user, False)

        # Checklist should be visible only when the request is
        # Queued, Ready or Processing.
        for status_name in ['Ready', 'Queued', 'Processing']:
            self.change_request_status(status_name)
            _assert_checklist(self.superuser, False)
            _assert_checklist(self.staff_user, False)
            _assert_checklist(self.user, True)

    def test_cancel_button(self):
        """Test that the Cancellation button is correctly visible."""

        def _assert_cancel_button(user, visible, disabled):
            response = self.get_response(user, self.url)
            self.assertEqual(response.status_code, HTTPStatus.OK)
            html = response.content.decode('utf-8')
            if visible:
                if disabled:
                    button = ' <a href="#cancel_button" data-toggle="popover"' \
                             ' title="Request Cancellation"'
                    self.assertIn(button, html)
                else:
                    button = 'class="btn btn-danger">Cancel Request</a>'
                    self.assertIn(button, html)
            else:
                self.assertNotIn('Cancel Request', html)

        for status_name in ['Queued', 'Ready']:
            self.change_request_status(status_name)

            # Cancel button is visible to admins for all reasons when request
            # status is Queued or Ready. It is disabled for users if they
            # did not make the request.
            for reason in ['Admin', 'BadPID', 'LastProject']:
                self.change_request_reason(reason)
                _assert_cancel_button(self.superuser, True, False)
                _assert_cancel_button(self.staff_user, False, False)
                _assert_cancel_button(self.user, True, True)

            # Cancel button only visible to users if they made the request
            # and the request status is Queued or Ready
            reason = 'User'
            self.change_request_reason(reason)
            _assert_cancel_button(self.superuser, True, False)
            _assert_cancel_button(self.staff_user, False, None)
            _assert_cancel_button(self.user, True, False)

        # Disabled cancel button visible to the user and admin for
        # Processing requests.
        status_name = 'Processing'
        self.change_request_status(status_name)
        for reason in ['User', 'Admin', 'BadPID', 'LastProject']:
            self.change_request_reason(reason)
            _assert_cancel_button(self.superuser, True, True)
            _assert_cancel_button(self.staff_user, False, None)
            _assert_cancel_button(self.user, True, True)

        # Cancel button is not visible to any users for finished requests.
        for status_name in ['Complete', 'Cancelled']:
            self.change_request_status(status_name)
            for reason in ['User', 'Admin', 'BadPID', 'LastProject']:
                self.change_request_reason(reason)
                _assert_cancel_button(self.superuser, False, None)
                _assert_cancel_button(self.staff_user, False, None)
                _assert_cancel_button(self.user, False, None)

    def test_post_completes_request(self):
        """Test that a POST request completes the request."""
        self.complete_request_checklist(self.request)
        self.change_request_status('Processing')

        self.assertEqual(self.request.status.name, 'Processing')

        response = self.post_response(self.superuser, self.url, {})
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response,
                             reverse('cluster-account-deletion-request-list'))

        self.request.refresh_from_db()
        self.assertEqual(self.request.status.name, 'Complete')
