from coldfront.core.utils.tests.test_base import TestBase

from http import HTTPStatus

class TestBillingIDValidateView(TestBase):
    """A class for testing BillingIDValidateView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

    def test_permissions_get(self):
        """Test that the correct users have permissions to perform GET
        requests."""

        url = "/billing/validate/"

        # Unauthenticated user.
        self.client.logout()
        response = self.client.get(url)
        self.assert_redirects_to_login(response, next_url=url)

        # Non superuser
        self.client.login(username=self.user.username, password=self.password)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

        # Superuser
        self.user.is_superuser = True
        self.user.save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.user.is_superuser = False
        self.user.save()


