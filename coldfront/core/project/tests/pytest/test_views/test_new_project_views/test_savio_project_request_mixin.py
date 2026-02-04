"""Unit tests for SavioProjectRequestMixin.conditionally_send_project_ready_for_processing_email()"""

import pytest
from unittest.mock import Mock, patch
from coldfront.core.project.views_.new_project_views.approval_views import (
    SavioProjectRequestMixin,
)


@pytest.mark.unit
class TestConditionallySendProjectReadyForProcessingEmail:
    """Unit tests for conditionally sending ready-for-processing
    email."""

    SEND_EMAIL_PATH = (
        'coldfront.core.project.views_.new_project_views.approval_views.'
        'send_project_request_ready_for_processing_email'
    )

    @pytest.fixture(autouse=True)
    def mock_computing_allowance(self):
        """Patch ComputingAllowanceInterface to avoid DB access during
        mixin init."""
        with patch(
                'coldfront.core.project.views_.new_project_views.'
                'approval_views.ComputingAllowanceInterface'):
            yield

    def _create_mixin(self):
        """Create a mixin instance (relies on mock_computing_allowance
        fixture)."""
        mixin = SavioProjectRequestMixin()
        mixin.logger = Mock()
        return mixin

    def test_sends_email_if_status_is_approved_processing(self):
        """Test email is sent when status is 'Approved - Processing'."""
        # Setup
        mixin = self._create_mixin()
        mock_request_obj = Mock()
        mock_request_obj.status.name = 'Approved - Processing'
        mixin.request_obj = mock_request_obj

        # Execute
        with patch(self.SEND_EMAIL_PATH) as mock_send:
            mixin.conditionally_send_project_ready_for_processing_email()

        # Assert
        mock_send.assert_called_once_with(mock_request_obj)

    def test_handles_email_send_exception_gracefully(self):
        """Test that exceptions during email send are logged but not
        raised."""
        # Setup
        mixin = self._create_mixin()
        mock_request_obj = Mock()
        mock_request_obj.status.name = 'Approved - Processing'
        mixin.request_obj = mock_request_obj

        # Execute
        with patch(self.SEND_EMAIL_PATH) as mock_send:
            mock_send.side_effect = Exception('Email service error')
            # Should not raise
            mixin.conditionally_send_project_ready_for_processing_email()

        # Assert - exception was logged
        mixin.logger.error.assert_called_once()
        mixin.logger.exception.assert_called_once()

    @pytest.mark.parametrize('status_name', [
        'Under Review',
        'Approved - Complete',
        'Approved - Scheduled',
        'Denied',
    ])
    def test_does_not_send_email_for_non_processing_statuses(self, status_name):
        """Test email is not sent for any status other than 'Approved -
        Processing'."""
        # Setup
        mixin = self._create_mixin()
        mock_request_obj = Mock()
        mock_request_obj.status.name = status_name
        mixin.request_obj = mock_request_obj

        # Execute
        with patch(self.SEND_EMAIL_PATH) as mock_send:
            mixin.conditionally_send_project_ready_for_processing_email()

        # Assert
        mock_send.assert_not_called()
