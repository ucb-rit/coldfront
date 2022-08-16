from datetime import datetime
from http import HTTPStatus

from django.urls import reverse
from iso8601 import iso8601

from coldfront.core.allocation.models import AccountDeletionRequestStatusChoice, \
    AccountDeletionRequestReasonChoice
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
        """Test that the correct redirect and message are performed."""
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
