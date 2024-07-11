from django.contrib.messages import get_messages

from coldfront.core.billing.tests.test_billing_base import TestBillingBase
from coldfront.core.billing.tests.test_commands.test_billing_ids import BillingIdsCommand
from coldfront.core.billing.utils.queries import get_billing_activity_from_full_id

class TestBillingIDValidateManyForm(TestBillingBase):
    """A class for testing BillingIDValidateManyForm."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)
        self.user.is_superuser = True
        self.user.save()

        self.command = BillingIdsCommand()

    def test_malformed_billing_ids(self):
        malformed_billing_id = "12345-78"
        response = self.client.post("/billing/validate/", data={"billing_ids": malformed_billing_id})
        messages = list(get_messages(response.wsgi_request))
        
        self.assertEqual(len(messages), 1)

        self.assertIn(malformed_billing_id + ": Malformed", messages[0].message)

    def test_billing_ids_correctness(self):
        unused_id = "123456-789"
        self.assertIsNone(get_billing_activity_from_full_id(unused_id))

        used_id_invalid = "123456-001"
        self.assertIsNone(get_billing_activity_from_full_id(used_id_invalid))
        _, error = self.command.create(used_id_invalid, ignore_invalid=True)
        self.assertFalse(error)

        used_id_valid = "123456-002"
        self.assertIsNone(get_billing_activity_from_full_id(used_id_valid))
        _, error = self.command.create(used_id_valid)
        self.assertFalse(error)

        billing_ids = unused_id + '\n' + used_id_invalid + '\n' + used_id_valid
        response = self.client.post("/billing/validate/", data={"billing_ids": billing_ids})
        messages = list(get_messages(response.wsgi_request))
        
        self.assertEqual(len(messages), 1)

        self.assertIn(unused_id + ": Invalid", messages[0].message)
        self.assertIn(used_id_invalid + ": Invalid", messages[0].message)
        self.assertIn(used_id_valid + ": Valid", messages[0].message)





