from django.urls import reverse
from django.contrib.messages import get_messages

from coldfront.core.billing.tests.test_billing_base import TestBillingBase
from coldfront.core.billing.tests.test_commands.test_billing_ids import BillingIdsCommand
from coldfront.core.billing.utils.queries import get_billing_activity_from_full_id
from coldfront.core.billing.utils.queries import is_billing_id_well_formed
from coldfront.core.billing.utils.validation import is_billing_id_valid

from http import HTTPStatus

class TestBillingIDValidateView(TestBillingBase):
    """A class for testing BillingIDValidateView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

        self.url = reverse('billing-id-validate')

        self.command = BillingIdsCommand()

    def test_permissions_get(self):
        """Test that the correct users have permissions to perform GET
        requests."""

        # Unauthenticated user.
        self.client.logout()
        response = self.client.get(self.url)
        self.assert_redirects_to_login(response, next_url=self.url)

        # Non superuser
        self.client.login(username=self.user.username, password=self.password)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

        # Superuser
        self.user.is_superuser = True
        self.user.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.user.is_superuser = False
        self.user.save()

    def test_billing_ids_correctness(self):
        """Test that, given a variety of billing IDs, the
            'validate' outputs correctly."""

        self.user.is_superuser = True
        self.user.save()
        
        malformed_billing_id = '12345-67'
        self.assertFalse(is_billing_id_well_formed(malformed_billing_id))

        invalid_billing_id = '123456-789'
        self.assertTrue(is_billing_id_well_formed(invalid_billing_id))
        self.assertFalse(is_billing_id_valid(invalid_billing_id))

        valid_billing_id = '123456-788'
        self.assertTrue(is_billing_id_well_formed(valid_billing_id))
        self.assertTrue(is_billing_id_valid(valid_billing_id))

        billing_ids = malformed_billing_id + '\n' + invalid_billing_id + \
                        '\n' + valid_billing_id
        response = self.client.post(self.url, data={'billing_ids': billing_ids})
        messages = list(get_messages(response.wsgi_request))
        
        self.assertEqual(len(messages), 1)

        self.assertIn(malformed_billing_id + ': Malformed', messages[0].message)
        self.assertIn(invalid_billing_id + ': Invalid', messages[0].message)
        self.assertIn(valid_billing_id + ': Valid', messages[0].message)
