from copy import deepcopy

from django.conf import settings
from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse
from flags.state import flag_enabled

from coldfront.core.utils.tests.test_base import TestBase

_DEV_FLAGS = deepcopy(settings.FLAGS)
_DEV_FLAGS["DEV_AUTH_ENABLED"] = [{"condition": "boolean", "value": True}]
_DEV_FLAGS["SSO_ENABLED"] = [{"condition": "boolean", "value": False}]
_DEV_FLAGS["BASIC_AUTH_ENABLED"] = [{"condition": "boolean", "value": False}]

_BASIC_FLAGS = deepcopy(settings.FLAGS)
_BASIC_FLAGS["BASIC_AUTH_ENABLED"] = [{"condition": "boolean", "value": True}]
_BASIC_FLAGS["SSO_ENABLED"] = [{"condition": "boolean", "value": False}]
_BASIC_FLAGS["DEV_AUTH_ENABLED"] = [{"condition": "boolean", "value": False}]

_SSO_FLAGS = deepcopy(settings.FLAGS)
_SSO_FLAGS["SSO_ENABLED"] = [{"condition": "boolean", "value": True}]
_SSO_FLAGS["BASIC_AUTH_ENABLED"] = [{"condition": "boolean", "value": False}]
_SSO_FLAGS["DEV_AUTH_ENABLED"] = [{"condition": "boolean", "value": False}]


class _UserLoginViewBase(TestBase):
    """Shared helpers for UserLoginView test classes."""

    @staticmethod
    def _url():
        return reverse("login")


@override_settings(FLAGS=_DEV_FLAGS)
class TestUserLoginViewDevAuth(_UserLoginViewBase):
    """UserLoginView routing when DEV_AUTH_ENABLED is True."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username="user", is_active=True)

    def test_expected_flags(self):
        """Sanity: correct flag state for this class."""
        self.assertTrue(flag_enabled("DEV_AUTH_ENABLED"))
        self.assertFalse(flag_enabled("SSO_ENABLED"))
        self.assertFalse(flag_enabled("BASIC_AUTH_ENABLED"))

    def test_anonymous_redirected_to_dev_login(self):
        """Anonymous request is routed to the dev login page."""
        response = self.client.get(self._url())
        self.assertRedirects(
            response, reverse("dev-login"), fetch_redirect_response=False
        )

    def test_next_forwarded_to_dev_login(self):
        """A ?next= parameter is preserved in the redirect to dev login."""
        next_url = "/some/path/"
        response = self.client.get(f"{self._url()}?next={next_url}")
        expected = f"{reverse('dev-login')}?next={next_url}"
        self.assertRedirects(response, expected, fetch_redirect_response=False)

    def test_authenticated_user_redirected_to_home(self):
        """An authenticated user is redirected to home regardless of flag."""
        self.client.force_login(self.user)
        response = self.client.get(self._url())
        self.assertRedirects(response, reverse("home"))

    def test_authenticated_user_redirected_to_next(self):
        """An authenticated user with ?next= is redirected to next."""
        self.client.force_login(self.user)
        next_url = "/some/path/"
        response = self.client.get(f"{self._url()}?next={next_url}")
        self.assertRedirects(response, next_url, fetch_redirect_response=False)


@override_settings(FLAGS=_BASIC_FLAGS)
class TestUserLoginViewBasicAuth(_UserLoginViewBase):
    """UserLoginView routing when BASIC_AUTH_ENABLED is True."""

    def test_expected_flags(self):
        """Sanity: correct flag state for this class."""
        self.assertTrue(flag_enabled("BASIC_AUTH_ENABLED"))
        self.assertFalse(flag_enabled("SSO_ENABLED"))
        self.assertFalse(flag_enabled("DEV_AUTH_ENABLED"))

    def test_anonymous_redirected_to_basic_auth_login(self):
        """Anonymous request is routed to the basic auth login page."""
        response = self.client.get(self._url())
        self.assertRedirects(
            response, reverse("basic-auth-login"), fetch_redirect_response=False
        )

    def test_next_forwarded_to_basic_auth_login(self):
        """A ?next= parameter is preserved in the redirect to basic auth."""
        next_url = "/some/path/"
        response = self.client.get(f"{self._url()}?next={next_url}")
        expected = f"{reverse('basic-auth-login')}?next={next_url}"
        self.assertRedirects(response, expected, fetch_redirect_response=False)


@override_settings(FLAGS=_SSO_FLAGS)
class TestUserLoginViewSSO(_UserLoginViewBase):
    """UserLoginView routing when SSO_ENABLED is True."""

    def test_expected_flags(self):
        """Sanity: correct flag state for this class."""
        self.assertTrue(flag_enabled("SSO_ENABLED"))
        self.assertFalse(flag_enabled("BASIC_AUTH_ENABLED"))
        self.assertFalse(flag_enabled("DEV_AUTH_ENABLED"))

    def test_anonymous_redirected_to_sso_login(self):
        """Anonymous request is routed to the SSO login page."""
        response = self.client.get(self._url())
        self.assertRedirects(
            response, reverse("sso-login"), fetch_redirect_response=False
        )

    def test_next_forwarded_to_sso_login(self):
        """A ?next= parameter is preserved in the redirect to SSO login."""
        next_url = "/some/path/"
        response = self.client.get(f"{self._url()}?next={next_url}")
        expected = f"{reverse('sso-login')}?next={next_url}"
        self.assertRedirects(response, expected, fetch_redirect_response=False)
