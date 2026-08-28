"""Tests for renewal email functions in renewal_utils."""

from unittest.mock import Mock, patch

import pytest

from coldfront.core.project.utils_.renewal_utils import (
    send_allocation_renewal_request_received_email,
)

_RENEWAL_UTILS = "coldfront.core.project.utils_.renewal_utils"


def _make_renewal_request(pk=1):
    """Return a mock AllocationRenewalRequest."""
    request = Mock()
    request.pk = pk
    request.requester.email = "requester@example.com"
    request.requester.first_name = "Requester"
    request.requester.last_name = "User"
    request.pi.email = "pi@example.com"
    request.pi.first_name = "PI"
    request.pi.last_name = "User"
    request.allocation_period.name = "Allowance Year 2025-26"
    request.post_project.name = "fc_project"
    return request


@pytest.mark.unit
class TestSendAllocationRenewalRequestReceivedEmail:
    """Tests for send_allocation_renewal_request_received_email."""

    def test_sends_to_requester(self, settings):
        """A confirmation email is sent to the requester."""
        settings.EMAIL_ENABLED = True
        settings.CENTER_BASE_URL = "https://example.com"
        settings.EMAIL_SENDER = "sender@example.com"
        settings.CENTER_HELP_EMAIL = "help@example.com"
        settings.EMAIL_SIGNATURE = "Test Signature"

        request = _make_renewal_request()

        with patch(f"{_RENEWAL_UTILS}.send_email_template") as mock_send:
            send_allocation_renewal_request_received_email(request)

        mock_send.assert_called_once()
        subject, _template, _context, _sender, receiver_list = mock_send.call_args.args
        assert receiver_list == [request.requester.email]
        assert "Allowance Renewal Request Received" in subject

    def test_does_not_send_to_pi(self, settings):
        """The confirmation email is sent only to the requester, not the PI."""
        settings.EMAIL_ENABLED = True
        settings.CENTER_BASE_URL = "https://example.com"
        settings.EMAIL_SENDER = "sender@example.com"
        settings.CENTER_HELP_EMAIL = "help@example.com"
        settings.EMAIL_SIGNATURE = "Test Signature"

        request = _make_renewal_request()

        with patch(f"{_RENEWAL_UTILS}.send_email_template") as mock_send:
            send_allocation_renewal_request_received_email(request)

        mock_send.assert_called_once()
        _subject, _template, _context, _sender, receiver_list = mock_send.call_args.args
        assert request.pi.email not in receiver_list

    def test_not_sent_when_email_disabled(self, settings):
        """No email is sent when EMAIL_ENABLED is False."""
        settings.EMAIL_ENABLED = False

        with patch(f"{_RENEWAL_UTILS}.send_email_template") as mock_send:
            send_allocation_renewal_request_received_email(_make_renewal_request())

        mock_send.assert_not_called()
