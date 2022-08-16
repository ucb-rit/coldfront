from http import HTTPStatus

from django.core import mail
from django.urls import reverse
from iso8601 import iso8601

from coldfront.config import settings
from coldfront.core.allocation.tests.test_account_deletion_base import \
    TestAccountDeletionBase
from coldfront.core.utils.common import utc_now_offset_aware


class TestAccountDeletionRequestCancellationView(TestAccountDeletionBase):
    """Testing class for AccountDeletionRequestCancellationView"""

    def setUp(self):
        super().setUp()
        self.create_account_deletion_request(self.user, 'Queued', 'User')
        self.url = reverse('cluster-account-deletion-request-cancel',
                           kwargs={'pk': self.request.pk})

        self.detail_url = reverse('cluster-account-deletion-request-detail',
                                           kwargs={'pk': self.request.pk})

    def test_access(self):
        self.assert_has_access(self.url, self.superuser, True)
        self.assert_has_access(self.url, self.staff_user, False)
        self.assert_has_access(self.url, self.user, True)
        self.assert_has_access(self.url, self.user2, False)

    def test_redirect(self):
        """Test that the correct redirect is performed."""
        def _assert_redirect(user, redirect):
            response = self.get_response(user, self.url)
            if redirect:
                self.assertEqual(response.status_code, HTTPStatus.FOUND)
                self.assertRedirects(response, self.detail_url)
            else:
                self.assertEqual(response.status_code, HTTPStatus.OK)

        for status in ['Queued', 'Ready']:
            self.change_request_status(status)
            for reason in ['Admin', 'LastProject', 'BadPID']:
                self.change_request_reason(reason)
                _assert_redirect(self.superuser, False)
                _assert_redirect(self.user, True)

            reason = 'User'
            self.change_request_reason(reason)
            _assert_redirect(self.superuser, False)
            _assert_redirect(self.user, False)

        for status in ['Processing', 'Complete', 'Cancelled']:
            self.change_request_status(status)
            _assert_redirect(self.superuser, True)
            _assert_redirect(self.user, True)

    def test_post_cancels_request(self):
        """Test that a valid POST request cancels the request."""
        pre_time = utc_now_offset_aware()
        for user in [self.user, self.superuser]:
            data = {'justification': 'This is a test justification.'}
            response = self.post_response(user, self.url, data)
            self.assertEqual(response.status_code, HTTPStatus.FOUND)

            self.request.refresh_from_db()
            self.assertEqual(self.request.status.name, 'Cancelled')

            timestamp = \
                iso8601.parse_date(self.request.state['other']['timestamp'])
            post_time = utc_now_offset_aware()
            self.assertTrue(pre_time <= timestamp <= post_time)

    def test_post_sends_admin_emails(self):
        """Test that a valid POST request sends the correct emails when
        the user requests the cancellation."""

        self.assertEqual(len(mail.outbox), 0)

        data = {'justification': 'This is a test justification.'}
        response = self.post_response(self.user, self.url, data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        email_body = ['The cluster account deletion request for User Test '
                      'User was cancelled by Test User with the '
                      'following justification',
                      data.get('justification')]

        for section in email_body:
            self.assertIn(section, email.body)
        self.assertIn('Cluster Account Deletion Request Cancelled',
                      email.subject)
        self.assertEqual(email.to, settings.EMAIL_ADMIN_LIST)
        self.assertEqual(settings.EMAIL_SENDER, email.from_email)

    def test_post_sends_user_emails(self):
        """Test that a valid POST request sends the correct emails when
        an admin requests the cancellation."""

        self.assertEqual(len(mail.outbox), 0)

        data = {'justification': 'This is a test justification.'}
        response = self.post_response(self.superuser, self.url, data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        email_body = ['The request to delete your cluster account was '
                      'cancelled by a system administrator with the '
                      'following justification',
                      'If this is a mistake, or you have any '
                      'questions, please contact us at',
                      data.get('justification')]

        for section in email_body:
            self.assertIn(section, email.body)
        self.assertIn('Cluster Account Deletion Request Cancelled',
                      email.subject)
        self.assertEqual(email.to, [self.request.user.email])
        self.assertEqual(settings.EMAIL_SENDER, email.from_email)
