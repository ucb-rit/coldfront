from copy import deepcopy
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user
from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse
from flags.state import flag_enabled

from coldfront.core.utils.tests.test_base import TestBase

FLAGS_COPY = deepcopy(settings.FLAGS)
FLAGS_COPY["DEV_AUTH_ENABLED"] = [{"condition": "boolean", "value": True}]
FLAGS_COPY["SSO_ENABLED"] = [{"condition": "boolean", "value": False}]


@override_settings(FLAGS=FLAGS_COPY)
class TestDevLoginView(TestBase):
    """Tests for DevLoginView: the dev-only passwordless user picker."""

    def setUp(self):
        super().setUp()
        self.active_user = User.objects.create_user(
            username="active_user", email="active@example.com", is_active=True
        )
        self.inactive_user = User.objects.create_user(
            username="inactive_user", email="inactive@example.com", is_active=False
        )

    @staticmethod
    def _url():
        return reverse("dev-login")

    # --- flag state ---

    def test_expected_flags_enabled(self):
        """DEV_AUTH_ENABLED is on and SSO_ENABLED is off for this test class."""
        self.assertTrue(flag_enabled("DEV_AUTH_ENABLED"))
        self.assertFalse(flag_enabled("SSO_ENABLED"))

    # --- GET ---

    def test_get_returns_200(self):
        """GET returns 200 for an anonymous user."""
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_get_lists_only_active_users(self):
        """GET includes active users and excludes inactive users in context."""
        response = self.client.get(self._url())
        usernames = [u.username for u in response.context["users"]]
        self.assertIn("active_user", usernames)
        self.assertNotIn("inactive_user", usernames)

    def test_get_passes_next_to_context(self):
        """GET with ?next passes the value into the template context."""
        next_url = "/some/path/"
        response = self.client.get(f"{self._url()}?next={next_url}")
        self.assertEqual(response.context["next"], next_url)

    def test_authenticated_user_redirected_to_home_on_get(self):
        """An authenticated user hitting GET is redirected to home."""
        self.client.force_login(self.active_user)
        response = self.client.get(self._url())
        self.assertRedirects(response, reverse("home"))

    def test_authenticated_user_redirected_to_next_on_get(self):
        """An authenticated user hitting GET with ?next is redirected to next."""
        self.client.force_login(self.active_user)
        next_url = "/some/path/"
        response = self.client.get(f"{self._url()}?next={next_url}")
        self.assertRedirects(response, next_url, fetch_redirect_response=False)

    # --- POST ---

    def test_post_logs_in_user_and_redirects_home(self):
        """POST with a valid user_id logs the user in and redirects to home."""
        response = self.client.post(self._url(), {"user_id": self.active_user.pk})
        self.assertRedirects(response, reverse("home"))
        client_user = get_user(self.client)
        self.assertTrue(client_user.is_authenticated)
        self.assertEqual(client_user.pk, self.active_user.pk)

    def test_post_redirects_to_next_after_login(self):
        """POST with a valid user_id and next param redirects to next."""
        next_url = "/some/path/"
        data = {"user_id": self.active_user.pk, "next": next_url}
        response = self.client.post(self._url(), data)
        self.assertRedirects(response, next_url, fetch_redirect_response=False)
        self.assertTrue(get_user(self.client).is_authenticated)

    # --- flag-disabled guard ---

    def test_url_returns_404_when_flag_disabled(self):
        """The dev-login URL returns 404 when DEV_AUTH_ENABLED is False."""
        flags = deepcopy(settings.FLAGS)
        flags["DEV_AUTH_ENABLED"] = [{"condition": "boolean", "value": False}]
        with override_settings(FLAGS=flags):
            self.assertFalse(flag_enabled("DEV_AUTH_ENABLED"))
            response = self.client.get(self._url())
            self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
