from http import HTTPStatus

from django.urls import reverse
from iso8601 import iso8601

from coldfront.core.allocation.tests.test_account_deletion_base import \
    TestAccountDeletionBase
from coldfront.core.utils.common import utc_now_offset_aware


class TestAccountDeletionRequestDataDeletionView(TestAccountDeletionBase):
    """Testing class for AccountDeletionRequestDataDeletionView"""

    def setUp(self):
        super().setUp()
        self.create_account_deletion_request(self.user, 'Ready', 'User')
        self.url = reverse('cluster-account-deletion-request-data-deletion',
                           kwargs={'pk': self.request.pk})

        self.detail_url = reverse('cluster-account-deletion-request-detail',
                                  kwargs={'pk': self.request.pk})

    def test_access(self):
        self.assert_has_access(self.url, self.superuser, True)
        self.assert_has_access(self.url, self.staff_user, False)
        self.assert_has_access(self.url, self.user, False)
        self.assert_has_access(self.url, self.user2, False)

    def test_redirect(self):
        """Test that the correct redirect is performed."""
        for status in ['Queued', 'Complete', 'Cancelled']:
            self.change_request_status(status)
            response = self.get_response(self.superuser, self.url)
            self.assertEqual(response.status_code, HTTPStatus.FOUND)
            self.assertRedirects(response, self.detail_url)

        for status in ['Ready', 'Processing']:
            self.change_request_status(status)
            response = self.get_response(self.superuser, self.url)
            self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_updates_request(self):
        """Test that a valid POST request updates the request."""
        pre_time = utc_now_offset_aware()
        data = {'status': 'Complete'}
        response = self.post_response(self.superuser, self.url, data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertRedirects(response, self.detail_url)

        self.request.refresh_from_db()
        self.assertEqual(self.request.status.name, 'Processing')
        self.assertEqual(self.request.state['data_deletion']['status'],
                         'Complete')

        timestamp = \
            iso8601.parse_date(self.request.state['data_deletion']['timestamp'])
        post_time = utc_now_offset_aware()
        self.assertTrue(pre_time <= timestamp <= post_time)
