"""Unit tests for secure directory user management runners."""

from unittest.mock import MagicMock, patch
from urllib.parse import urljoin

from django.test import override_settings
import pytest

_MODULE = "coldfront.core.allocation.utils_.secure_dir_utils.user_management"

_CENTER_BASE_URL = "https://portal.example.com"
_EMAIL_SENDER = "noreply@example.com"
_ADMIN_RECIPIENTS = ["admin0@example.com", "admin1@example.com"]
_DIRECTORY_PATH = "/global/scratch/p2/test_dir"

_EXPECTED_SUBJECTS = {
    "add": "New Secure Directory Add User Request",
    "remove": "New Secure Directory Remove User Request",
}
_EXPECTED_TEMPLATES = {
    "add": "email/secure_dir_request/new_secure_dir_add_user_request.txt",
    "remove": "email/secure_dir_request/new_secure_dir_remove_user_request.txt",
}
_EXPECTED_RECIPIENTS_KEY = {
    "add": "secure_directory_add_user_requests",
    "remove": "secure_directory_remove_user_requests",
}


def _make_runner(action):
    """Instantiate the appropriate runner without calling ``__init__``."""
    from coldfront.core.allocation.utils_.secure_dir_utils.user_management import (
        SecureDirectoryAddUserRequestRunner,
        SecureDirectoryRemoveUserRequestRunner,
    )

    cls = (
        SecureDirectoryAddUserRequestRunner
        if action == "add"
        else SecureDirectoryRemoveUserRequestRunner
    )
    runner = cls.__new__(cls)
    runner._secure_directory = MagicMock()
    runner._secure_directory.get_path.return_value = _DIRECTORY_PATH
    runner._user = MagicMock()
    runner._user.first_name = "Jane"
    runner._user.last_name = "Doe"
    runner._user.email = "jane.doe@example.com"
    runner._email_strategy = MagicMock()
    runner._request_obj = None
    return runner


@pytest.mark.unit
class TestSendEmailToAdmins:
    """Unit tests for ``_send_email_to_admins`` on the add and remove runners.

    Each test runs twice — once with ``action='add'`` and once with
    ``action='remove'`` — via the parametrized ``action`` fixture.
    """

    @pytest.fixture(params=["add", "remove"])
    def action(self, request):
        return request.param

    @pytest.fixture
    def fake_path(self, action):
        return f"/allocation/secure-dir/manage-users/{action}/pending/"

    @pytest.fixture
    def email_send_data(self, action, fake_path):
        """Run ``_send_email_to_admins`` with all dependencies patched.

        Returns a dict with:
          ``send_call_args``    – positional args passed to send_email_template
          ``reverse_call_args`` – call args passed to reverse
          ``recipients_call_args`` – call args passed to
                                     get_email_admin_notification_recipients
        """
        with (
            patch(f"{_MODULE}.reverse", return_value=fake_path) as mock_reverse,
            patch(
                f"{_MODULE}.get_email_admin_notification_recipients",
                return_value=_ADMIN_RECIPIENTS,
            ) as mock_recipients,
            patch(f"{_MODULE}.send_email_template") as mock_send,
            override_settings(
                CENTER_BASE_URL=_CENTER_BASE_URL,
                EMAIL_SENDER=_EMAIL_SENDER,
            ),
        ):
            runner = _make_runner(action)
            runner._send_email_to_admins()
            return {
                "send_call_args": mock_send.call_args,
                "reverse_call_args": mock_reverse.call_args,
                "recipients_call_args": mock_recipients.call_args,
            }

    # ------------------------------------------------------------------
    # Review URL
    # ------------------------------------------------------------------

    def test_review_url_is_absolute(self, email_send_data):
        """``review_url`` in the email context must start with CENTER_BASE_URL."""
        context = email_send_data["send_call_args"][0][2]
        assert context["review_url"].startswith(_CENTER_BASE_URL)

    def test_review_url_equals_urljoin_of_base_and_path(
        self, email_send_data, fake_path
    ):
        """``review_url`` must equal ``urljoin(CENTER_BASE_URL, reversed_path)``."""
        context = email_send_data["send_call_args"][0][2]
        assert context["review_url"] == urljoin(_CENTER_BASE_URL, fake_path)

    def test_review_url_is_not_just_a_relative_path(self, email_send_data, fake_path):
        """``review_url`` must not be a bare relative path."""
        context = email_send_data["send_call_args"][0][2]
        assert context["review_url"] != fake_path

    # ------------------------------------------------------------------
    # reverse() called with the correct action-specific kwargs
    # ------------------------------------------------------------------

    def test_reverse_called_with_action_kwarg(self, action, email_send_data):
        """``reverse`` must be called with ``action`` matching the runner's action."""
        reverse_kwargs = email_send_data["reverse_call_args"][1]["kwargs"]
        assert reverse_kwargs["action"] == action

    def test_reverse_called_with_pending_status(self, email_send_data):
        """``reverse`` must target the pending request list."""
        reverse_kwargs = email_send_data["reverse_call_args"][1]["kwargs"]
        assert reverse_kwargs["status"] == "pending"

    # ------------------------------------------------------------------
    # Email context
    # ------------------------------------------------------------------

    def test_user_str_in_context(self, email_send_data):
        """``user_str`` must be formatted as 'First Last (email)'."""
        context = email_send_data["send_call_args"][0][2]
        assert context["user_str"] == "Jane Doe (jane.doe@example.com)"

    def test_directory_name_in_context(self, email_send_data):
        """``directory_name`` must come from ``secure_directory.get_path()``."""
        context = email_send_data["send_call_args"][0][2]
        assert context["directory_name"] == _DIRECTORY_PATH

    # ------------------------------------------------------------------
    # send_email_template call signature
    # ------------------------------------------------------------------

    def test_subject(self, action, email_send_data):
        """Subject line must match the action."""
        subject = email_send_data["send_call_args"][0][0]
        assert subject == _EXPECTED_SUBJECTS[action]

    def test_template_name(self, action, email_send_data):
        """Template must match the action."""
        template = email_send_data["send_call_args"][0][1]
        assert template == _EXPECTED_TEMPLATES[action]

    def test_sender(self, email_send_data):
        """Sender must come from ``settings.EMAIL_SENDER``."""
        sender = email_send_data["send_call_args"][0][3]
        assert sender == _EMAIL_SENDER

    def test_recipients(self, email_send_data):
        """Recipients must be those returned by ``get_email_admin_notification_recipients``."""
        recipients = email_send_data["send_call_args"][0][4]
        assert recipients == _ADMIN_RECIPIENTS

    def test_recipients_fetched_with_action_specific_key(self, action, email_send_data):
        """``get_email_admin_notification_recipients`` must be called with
        the correct action-specific notification key."""
        args = email_send_data["recipients_call_args"][0]
        assert args[0] == _EXPECTED_RECIPIENTS_KEY[action]
        assert args[1] == "created"
