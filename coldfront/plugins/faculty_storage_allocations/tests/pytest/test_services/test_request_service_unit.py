"""Unit tests for FacultyStorageAllocationRequestService.

These tests mock database operations to test business logic.
For tests with real database operations, see test_request_service_integration.py.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from django.utils import timezone

from coldfront.plugins.faculty_storage_allocations.services import (
    FacultyStorageAllocationRequestService
)


@pytest.mark.unit
class TestRequestServiceCreate:
    """Unit tests for request creation."""

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.FacultyStorageAllocationRequest')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.FacultyStorageAllocationRequestStatusChoice')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.StorageRequestNotificationService')
    def test_create_request_creates_request_object(
        self, mock_notification, mock_status_choice, mock_request_model
    ):
        """Test create_request() creates request with provided data."""
        # Setup
        mock_status = Mock()
        mock_status.name = 'Under Review'
        mock_status_choice.objects.get.return_value = mock_status

        mock_request = Mock()
        mock_request.id = 1
        mock_request_model.objects.create.return_value = mock_request

        data = {
            'status': 'Under Review',
            'requested_amount_gb': 1000,
            'project': Mock(),
            'requester': Mock(),
            'pi': Mock(),
        }

        # Execute
        result = FacultyStorageAllocationRequestService.create_request(data)

        # Assert
        mock_status_choice.objects.get.assert_called_once_with(
            name='Under Review'
        )
        mock_request_model.objects.create.assert_called_once()
        assert result == mock_request

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.FacultyStorageAllocationRequest')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.FacultyStorageAllocationRequestStatusChoice')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.StorageRequestNotificationService')
    def test_create_request_sends_notification_email(
        self, mock_notification, mock_status_choice, mock_request_model
    ):
        """Test create_request() triggers notification email."""
        # Setup
        mock_status = Mock()
        mock_status_choice.objects.get.return_value = mock_status

        mock_request = Mock()
        mock_request_model.objects.create.return_value = mock_request

        data = {'status': 'Under Review', 'requested_amount_gb': 1000}

        # Execute
        FacultyStorageAllocationRequestService.create_request(data)

        # Assert - notification was sent
        mock_notification.send_request_created_email.assert_called_once_with(
            mock_request,
            email_strategy=None
        )

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.FacultyStorageAllocationRequest')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.FacultyStorageAllocationRequestStatusChoice')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.StorageRequestNotificationService')
    def test_create_request_with_custom_email_strategy(
        self, mock_notification, mock_status_choice, mock_request_model
    ):
        """Test create_request() uses provided email strategy."""
        # Setup
        mock_status = Mock()
        mock_status_choice.objects.get.return_value = mock_status

        mock_request = Mock()
        mock_request_model.objects.create.return_value = mock_request

        mock_email_strategy = Mock()
        data = {'status': 'Under Review', 'requested_amount_gb': 1000}

        # Execute
        FacultyStorageAllocationRequestService.create_request(
            data, email_strategy=mock_email_strategy
        )

        # Assert - custom strategy was passed
        mock_notification.send_request_created_email.assert_called_once_with(
            mock_request,
            email_strategy=mock_email_strategy
        )


@pytest.mark.unit
class TestRequestServiceApproval:
    """Unit tests for request approval."""

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.FacultyStorageAllocationRequestStatusChoice')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.utc_now_offset_aware')
    def test_approve_request_sets_approved_amount_if_not_provided(
        self, mock_now, mock_status_choice
    ):
        """Test approve_request() defaults approved_amount to
        requested_amount."""
        # Setup
        mock_status = Mock()
        mock_status.name = 'Approved - Queued'
        mock_status_choice.objects.get.return_value = mock_status

        now = timezone.now()
        mock_now.return_value = now

        mock_request = Mock()
        mock_request.requested_amount_gb = 1000
        mock_request.approved_amount_gb = None  # Not set

        # Execute
        FacultyStorageAllocationRequestService.approve_request(mock_request)

        # Assert
        assert mock_request.approved_amount_gb == 1000
        assert mock_request.status == mock_status
        assert mock_request.approval_time == now
        mock_request.save.assert_called_once()

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.FacultyStorageAllocationRequestStatusChoice')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.utc_now_offset_aware')
    def test_approve_request_keeps_existing_approved_amount(
        self, mock_now, mock_status_choice
    ):
        """Test approve_request() doesn't override existing approved_amount."""
        # Setup
        mock_status = Mock()
        mock_status_choice.objects.get.return_value = mock_status

        now = timezone.now()
        mock_now.return_value = now

        mock_request = Mock()
        mock_request.requested_amount_gb = 1000
        mock_request.approved_amount_gb = 500  # Already set to different value

        # Execute
        FacultyStorageAllocationRequestService.approve_request(mock_request)

        # Assert - approved_amount should stay at 500
        assert mock_request.approved_amount_gb == 500

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.FacultyStorageAllocationRequestStatusChoice')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.utc_now_offset_aware')
    def test_approve_request_sets_approval_time(
        self, mock_now, mock_status_choice
    ):
        """Test approve_request() sets approval_time timestamp."""
        # Setup
        mock_status = Mock()
        mock_status_choice.objects.get.return_value = mock_status

        expected_time = timezone.now()
        mock_now.return_value = expected_time

        mock_request = Mock()
        mock_request.requested_amount_gb = 1000
        mock_request.approved_amount_gb = 1000

        # Execute
        FacultyStorageAllocationRequestService.approve_request(mock_request)

        # Assert
        assert mock_request.approval_time == expected_time

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.FacultyStorageAllocationRequestStatusChoice')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.utc_now_offset_aware')
    def test_approve_request_updates_status_to_approved_queued(
        self, mock_now, mock_status_choice
    ):
        """Test approve_request() changes status to 'Approved - Queued'."""
        # Setup
        expected_status = Mock()
        expected_status.name = 'Approved - Queued'
        mock_status_choice.objects.get.return_value = expected_status

        mock_now.return_value = timezone.now()

        mock_request = Mock()
        mock_request.requested_amount_gb = 1000
        mock_request.approved_amount_gb = 1000

        # Execute
        FacultyStorageAllocationRequestService.approve_request(mock_request)

        # Assert
        mock_status_choice.objects.get.assert_called_once_with(
            name='Approved - Queued'
        )
        assert mock_request.status == expected_status


@pytest.mark.unit
class TestRequestServiceStateUpdates:
    """Unit tests for state update methods."""

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.utc_now_offset_aware')
    def test_update_eligibility_state_sets_status_and_timestamp(
        self, mock_now
    ):
        """Test update_eligibility_state() updates state correctly."""
        # Setup
        now = timezone.now()
        mock_now.return_value = now

        mock_request = Mock()
        mock_request.state = {
            'eligibility': {'status': 'Pending', 'justification': '',
                           'timestamp': ''},
            'intake_consistency': {},
            'setup': {},
            'other': {}
        }

        # Execute
        FacultyStorageAllocationRequestService.update_eligibility_state(
            mock_request, 'Approved', 'PI is eligible'
        )

        # Assert
        assert mock_request.state['eligibility']['status'] == 'Approved'
        assert mock_request.state['eligibility']['justification'] == \
            'PI is eligible'
        assert mock_request.state['eligibility']['timestamp'] == \
            now.isoformat()
        mock_request.save.assert_called_once()

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.utc_now_offset_aware')
    def test_update_eligibility_state_includes_justification(
        self, mock_now
    ):
        """Test update_eligibility_state() stores justification."""
        # Setup
        mock_now.return_value = timezone.now()

        mock_request = Mock()
        mock_request.state = {
            'eligibility': {},
            'intake_consistency': {},
            'setup': {},
            'other': {}
        }

        justification_text = 'Custom denial reason'

        # Execute
        FacultyStorageAllocationRequestService.update_eligibility_state(
            mock_request, 'Denied', justification_text
        )

        # Assert
        assert mock_request.state['eligibility']['justification'] == \
            justification_text

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.utc_now_offset_aware')
    def test_update_intake_consistency_state_sets_status_and_timestamp(
        self, mock_now
    ):
        """Test update_intake_consistency_state() updates state correctly."""
        # Setup
        now = timezone.now()
        mock_now.return_value = now

        mock_request = Mock()
        mock_request.state = {
            'eligibility': {},
            'intake_consistency': {'status': 'Pending'},
            'setup': {},
            'other': {}
        }

        # Execute
        FacultyStorageAllocationRequestService\
            .update_intake_consistency_state(
                mock_request, 'Approved', 'Data is consistent'
            )

        # Assert
        assert mock_request.state['intake_consistency']['status'] == \
            'Approved'
        assert mock_request.state['intake_consistency']['timestamp'] == \
            now.isoformat()

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.utc_now_offset_aware')
    def test_update_setup_state_includes_directory_name(
        self, mock_now
    ):
        """Test update_setup_state() stores directory_name."""
        # Setup
        now = timezone.now()
        mock_now.return_value = now

        mock_request = Mock()
        mock_request.state = {
            'eligibility': {},
            'intake_consistency': {},
            'setup': {},
            'other': {}
        }

        # Execute
        FacultyStorageAllocationRequestService.update_setup_state(
            mock_request, directory_name='fc_test_dir', status='Complete'
        )

        # Assert
        assert mock_request.state['setup']['directory_name'] == 'fc_test_dir'
        assert mock_request.state['setup']['status'] == 'Complete'
        assert mock_request.state['setup']['timestamp'] == now.isoformat()
