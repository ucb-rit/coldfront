"""Unit tests for StorageRequestNotificationService."""

import pytest
from collections import namedtuple
from unittest.mock import Mock, patch

from coldfront.core.utils.email.email_strategy import SendEmailStrategy

from coldfront.plugins.cluster_storage.services import StorageRequestNotificationService


@pytest.mark.unit
class TestStorageRequestNotificationService:
    """Unit tests for storage request notification service."""

    def setup_method(self):
        """Set up common test data."""
        self.mock_request = Mock()
        self.mock_request.pk = 123
        self.mock_request.project = Mock()
        self.mock_request.project.pk = 456
        self.mock_request.project.name = 'fc_test_project'
        self.mock_request.requester = Mock()
        self.mock_request.requester.email = 'requester@example.com'
        self.mock_request.pi = Mock()
        self.mock_request.pi.email = 'pi@example.com'
        self.mock_request.requested_amount_gb = 5000

    def _get_email_strategy(self):
        return SendEmailStrategy()

    @patch('coldfront.plugins.cluster_storage.services.notification_service.send_email_template')
    @patch('coldfront.plugins.cluster_storage.services.notification_service.django_settings')
    @patch('coldfront.plugins.cluster_storage.services.notification_service.settings')
    def test_send_request_created_email_constructs_correct_parameters(
        self, mock_settings, mock_django_settings, mock_send_email
    ):
        """Test that send_request_created_email constructs correct email parameters."""
        # Setup
        mock_django_settings.CENTER_BASE_URL = 'https://portal.example.com'
        mock_django_settings.EMAIL_SENDER = 'noreply@example.com'
        mock_settings.ADMIN_EMAIL_LIST = ['admin1@example.com', 'admin2@example.com']

        email_strategy = self._get_email_strategy()

        # Execute
        StorageRequestNotificationService.send_request_created_email(
            self.mock_request,
            email_strategy=email_strategy
        )

        # Verify send_email_template was called once
        assert mock_send_email.call_count == 1

        # Get the call arguments
        call_args = mock_send_email.call_args
        args = call_args[0]  # Positional arguments

        # Verify email parameters
        subject = args[0]
        template_name = args[1]
        context = args[2]
        sender = args[3]
        receiver_list = args[4]

        assert subject == 'New Faculty Storage Allocation Request - fc_test_project'
        assert template_name == 'cluster_storage/email/request_created.txt'
        assert sender == 'noreply@example.com'
        assert receiver_list == ['admin1@example.com', 'admin2@example.com']

        # Verify context
        assert context['project'] == self.mock_request.project
        assert context['requester'] == self.mock_request.requester
        assert context['pi'] == self.mock_request.pi
        assert context['amount_tb'] == 5  # 5000 GB // 1000 = 5 TB
        assert 'review_url' in context
        # Verify URL contains request ID
        assert '/123/' in context['review_url']
        assert context['review_url'].startswith('https://portal.example.com')

    @patch('coldfront.plugins.cluster_storage.services.notification_service.send_email_template')
    @patch('coldfront.plugins.cluster_storage.services.notification_service.django_settings')
    @patch('coldfront.plugins.cluster_storage.services.notification_service.settings')
    @patch('coldfront.plugins.cluster_storage.services.notification_service.validate_email_strategy_or_get_default')
    def test_send_request_created_email_uses_default_strategy_when_none_provided(
        self, mock_validate_strategy, mock_settings, mock_django_settings, mock_send_email
    ):
        """Test that send_request_created_email uses default email strategy when none provided."""
        # Setup
        mock_django_settings.CENTER_BASE_URL = 'https://portal.example.com'
        mock_django_settings.EMAIL_SENDER = 'noreply@example.com'
        mock_settings.ADMIN_EMAIL_LIST = ['admin@example.com']

        # Return a real SendEmailStrategy as the default
        mock_validate_strategy.return_value = SendEmailStrategy()

        # Execute - no email_strategy provided
        StorageRequestNotificationService.send_request_created_email(
            self.mock_request
        )

        # Verify default strategy was requested
        mock_validate_strategy.assert_called_once_with(None)

        # Verify send_email_template was called (strategy was used)
        assert mock_send_email.call_count == 1

    @patch('coldfront.plugins.cluster_storage.services.notification_service.send_email_template')
    @patch('coldfront.plugins.cluster_storage.services.notification_service.django_settings')
    def test_send_completion_email_constructs_correct_parameters(
        self, mock_django_settings, mock_send_email
    ):
        """Test that send_completion_email constructs correct email parameters."""
        # Setup
        mock_django_settings.CENTER_BASE_URL = 'https://portal.example.com'
        mock_django_settings.CENTER_NAME = 'Test Center'
        mock_django_settings.EMAIL_SENDER = 'noreply@example.com'
        mock_django_settings.CENTER_HELP_EMAIL = 'help@example.com'
        mock_django_settings.EMAIL_SIGNATURE = 'Test Team'

        email_strategy = self._get_email_strategy()

        # Execute
        StorageRequestNotificationService.send_completion_email(
            self.mock_request,
            email_strategy=email_strategy
        )

        # Verify send_email_template was called once
        assert mock_send_email.call_count == 1

        # Get the call arguments
        call_args = mock_send_email.call_args
        args = call_args[0]

        # Verify email parameters
        subject = args[0]
        template_name = args[1]
        context = args[2]
        sender = args[3]
        receiver_list = args[4]

        assert subject == 'Faculty Storage Allocation Request Complete - fc_test_project'
        assert template_name == 'cluster_storage/email/request_completed.txt'
        assert sender == 'noreply@example.com'
        assert set(receiver_list) == {'requester@example.com', 'pi@example.com'}

        # Verify context
        assert context['center_name'] == 'Test Center'
        assert context['project'] == self.mock_request.project
        assert context['amount_tb'] == 5  # 5000 GB // 1000 = 5 TB
        assert context['support_email'] == 'help@example.com'
        assert context['signature'] == 'Test Team'
        assert 'project_url' in context
        # Verify URL contains project ID
        assert '/456/' in context['project_url']
        assert context['project_url'].startswith('https://portal.example.com')

    @patch('coldfront.plugins.cluster_storage.services.notification_service.send_email_template')
    @patch('coldfront.plugins.cluster_storage.services.notification_service.django_settings')
    def test_send_completion_email_deduplicates_recipient_list(
        self, mock_django_settings, mock_send_email
    ):
        """Test that send_completion_email removes duplicate emails when PI and requester are same."""
        # Setup - PI and requester have same email
        self.mock_request.pi.email = 'same@example.com'
        self.mock_request.requester.email = 'same@example.com'

        mock_django_settings.CENTER_BASE_URL = 'https://portal.example.com'
        mock_django_settings.CENTER_NAME = 'Test Center'
        mock_django_settings.EMAIL_SENDER = 'noreply@example.com'
        mock_django_settings.CENTER_HELP_EMAIL = 'help@example.com'
        mock_django_settings.EMAIL_SIGNATURE = 'Test Team'

        email_strategy = self._get_email_strategy()

        # Execute
        StorageRequestNotificationService.send_completion_email(
            self.mock_request,
            email_strategy=email_strategy
        )

        # Get receiver list
        call_args = mock_send_email.call_args
        receiver_list = call_args[0][4]  # receiver_list is 5th arg (index 4)

        # Verify only one email in list
        assert receiver_list == ['same@example.com']

    @patch('coldfront.plugins.cluster_storage.services.notification_service.send_email_template')
    @patch('coldfront.plugins.cluster_storage.services.notification_service.django_settings')
    def test_send_denial_email_constructs_correct_parameters(
        self, mock_django_settings, mock_send_email
    ):
        """Test that send_denial_email constructs correct email parameters."""
        # Setup
        DenialReason = namedtuple('DenialReason', 'category justification timestamp')
        denial_reason = DenialReason(
            category='Eligibility',
            justification='PI does not meet eligibility criteria',
            timestamp='2025-01-01T12:00:00'
        )
        self.mock_request.denial_reason.return_value = denial_reason

        mock_django_settings.CENTER_NAME = 'Test Center'
        mock_django_settings.EMAIL_SENDER = 'noreply@example.com'
        mock_django_settings.CENTER_HELP_EMAIL = 'help@example.com'
        mock_django_settings.EMAIL_SIGNATURE = 'Test Team'

        email_strategy = self._get_email_strategy()

        # Execute
        StorageRequestNotificationService.send_denial_email(
            self.mock_request,
            email_strategy=email_strategy
        )

        # Verify denial_reason was called
        self.mock_request.denial_reason.assert_called_once()

        # Verify send_email_template was called once
        assert mock_send_email.call_count == 1

        # Get the call arguments
        call_args = mock_send_email.call_args
        args = call_args[0]

        # Verify email parameters
        subject = args[0]
        template_name = args[1]
        context = args[2]
        sender = args[3]
        receiver_list = args[4]

        assert subject == 'Faculty Storage Allocation Request Denied - fc_test_project'
        assert template_name == 'cluster_storage/email/request_denied.txt'
        assert sender == 'noreply@example.com'
        assert set(receiver_list) == {'requester@example.com', 'pi@example.com'}

        # Verify context includes denial reason
        assert context['center_name'] == 'Test Center'
        assert context['project'] == self.mock_request.project
        assert context['amount_tb'] == 5  # 5000 GB // 1000 = 5 TB
        assert context['reason_category'] == 'Eligibility'
        assert context['reason_justification'] == 'PI does not meet eligibility criteria'
        assert context['support_email'] == 'help@example.com'
        assert context['signature'] == 'Test Team'

    @patch('coldfront.plugins.cluster_storage.services.notification_service.send_email_template')
    @patch('coldfront.plugins.cluster_storage.services.notification_service.django_settings')
    def test_send_denial_email_deduplicates_recipient_list(
        self, mock_django_settings, mock_send_email
    ):
        """Test that send_denial_email removes duplicate emails when PI and requester are same."""
        # Setup - PI and requester have same email
        self.mock_request.pi.email = 'same@example.com'
        self.mock_request.requester.email = 'same@example.com'

        DenialReason = namedtuple('DenialReason', 'category justification timestamp')
        denial_reason = DenialReason(
            category='Other',
            justification='Some other reason',
            timestamp='2025-01-01T12:00:00'
        )
        self.mock_request.denial_reason.return_value = denial_reason

        mock_django_settings.CENTER_NAME = 'Test Center'
        mock_django_settings.EMAIL_SENDER = 'noreply@example.com'
        mock_django_settings.CENTER_HELP_EMAIL = 'help@example.com'
        mock_django_settings.EMAIL_SIGNATURE = 'Test Team'

        email_strategy = self._get_email_strategy()

        # Execute
        StorageRequestNotificationService.send_denial_email(
            self.mock_request,
            email_strategy=email_strategy
        )

        # Get receiver list
        call_args = mock_send_email.call_args
        receiver_list = call_args[0][4]  # receiver_list is 5th arg (index 4)

        # Verify only one email in list
        assert receiver_list == ['same@example.com']

    @pytest.mark.parametrize(
        ['amount_gb', 'expected_tb'],
        [
            (1000, 1),
            (5000, 5),
            (10500, 10),  # Integer division
            (999, 0),     # Less than 1 TB
        ]
    )
    @patch('coldfront.plugins.cluster_storage.services.notification_service.send_email_template')
    @patch('coldfront.plugins.cluster_storage.services.notification_service.django_settings')
    def test_amount_gb_to_tb_conversion(
        self, mock_django_settings, mock_send_email, amount_gb, expected_tb
    ):
        """Test that GB to TB conversion is correct in email context."""
        # Setup
        self.mock_request.requested_amount_gb = amount_gb

        mock_django_settings.CENTER_NAME = 'Test Center'
        mock_django_settings.EMAIL_SENDER = 'noreply@example.com'
        mock_django_settings.CENTER_HELP_EMAIL = 'help@example.com'
        mock_django_settings.EMAIL_SIGNATURE = 'Test Team'
        mock_django_settings.CENTER_BASE_URL = 'https://portal.example.com'

        email_strategy = self._get_email_strategy()

        # Execute
        StorageRequestNotificationService.send_completion_email(
            self.mock_request,
            email_strategy=email_strategy
        )

        # Get context
        call_args = mock_send_email.call_args
        context = call_args[0][2]  # context is 3rd arg (index 2)

        # Verify TB conversion
        assert context['amount_tb'] == expected_tb
