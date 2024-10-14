from copy import deepcopy

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import Client
from django.test import override_settings

from allauth.account.models import EmailAddress
from flags.state import enable_flag

from coldfront.core.user.tests.utils import TestUserBase
from coldfront.core.user.utils import account_activation_url


FLAGS_COPY = deepcopy(settings.FLAGS)
FLAGS_COPY['SSO_ENABLED'] = {'condition': 'boolean', 'value': False}


@override_settings(FLAGS=FLAGS_COPY)
class TestActivateUserAccount(TestUserBase):
    """A class for testing the view for activating a user's account."""

    password = 'test1234'

    def setUp(self):
        """Set up test data."""
        enable_flag('BASIC_AUTH_ENABLED')
        super().setUp()

        self.user = User.objects.create(
            email='user@email.com',
            first_name='First',
            last_name='Last',
            username='user')
        self.user.set_password(self.password)
        self.user.save()

        self.client = Client()

    @staticmethod
    def expected_success_message(email):
        """Return the success message expected when activation succeeds,
        which should include the given email."""
        return (
            f'Your account has been activated. You may now log in. {email} '
            f'has been verified and set as your primary email address. You '
            f'may modify this in the User Profile.')

    @staticmethod
    def get_message_strings(response):
        """Return messages included in the given response as a list of
        strings."""
        return [str(m) for m in get_messages(response.wsgi_request)]

    def test_creates_verified_primary_email_address(self):
        """Test that account activation includes the creation of a
        verified, primary EmailAddress corresponding to the User's
        "email" field."""
        url = account_activation_url(self.user)
        response = self.client.get(url)
        self.assert_redirects_to_login(response, target_status_code=302)
        message = self.expected_success_message(self.user.email)
        self.assertEqual(message, self.get_message_strings(response)[0])

        email_address = EmailAddress.objects.get(email=self.user.email)
        self.assertEqual(email_address.user, self.user)
        self.assertTrue(email_address.verified)
        self.assertTrue(email_address.primary)

    def test_updates_existing_email_addresses(self):
        """Test that account activation updates EmailAddresses so that
        each user has exactly one primary EmailAddress."""
        # Create an unverified, non-primary EmailAddress for the User.
        kwargs = {
            'user': self.user,
            'verified': False,
            'primary': False,
        }
        email_address = EmailAddress.objects.create(
            user=self.user,
            email=self.user.email,
            verified=False,
            primary=False)

        # Create other primary EmailAddresses.
        other_email_addresses = []
        kwargs['verified'] = True
        for i in range(3):
            kwargs['email'] = f'{i}@email.com'
            other_email_addresses.append(
                EmailAddress.objects.create(**kwargs))
        # Bypass the "save" method, which prevents multiple primary addresses,
        # by using the "update" method.
        EmailAddress.objects.filter(
            pk__in=[ea.pk for ea in other_email_addresses]).update(
                primary=True)

        url = account_activation_url(self.user)
        response = self.client.get(url)
        self.assert_redirects_to_login(response, target_status_code=302)
        message = self.expected_success_message(self.user.email)
        self.assertEqual(message, self.get_message_strings(response)[0])

        email_address.refresh_from_db()
        self.assertEqual(email_address.user, self.user)
        self.assertTrue(email_address.verified)
        self.assertTrue(email_address.primary)

        for ea in other_email_addresses:
            ea.refresh_from_db()
            self.assertFalse(ea.primary)

    # TODO
