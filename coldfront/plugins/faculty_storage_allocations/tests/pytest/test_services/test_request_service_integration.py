"""Component tests for FacultyStorageAllocationRequestService with database.

These tests use real database operations to verify that the request service
correctly manages the entire request lifecycle.
"""

import pytest
from datetime import timedelta
from django.utils import timezone
from unittest.mock import Mock, patch

from coldfront.plugins.faculty_storage_allocations.models import (
    FacultyStorageAllocationRequest,
    FacultyStorageAllocationRequestStatusChoice,
    faculty_storage_allocation_request_state_schema,
)
from coldfront.plugins.faculty_storage_allocations.services import (
    FacultyStorageAllocationRequestService
)
from coldfront.plugins.faculty_storage_allocations.tests.pytest.utils import (
    create_fsa_request,
    update_request_state,
)


@pytest.mark.component
class TestRequestServiceCreate:
    """Test request creation with database."""

    def test_create_request_persists_to_database(
        self, test_project, test_user, test_pi
    ):
        """Test create_request() creates request in database."""
        # Setup
        data = {
            'status': 'Under Review',
            'project': test_project,
            'requester': test_user,
            'pi': test_pi,
            'requested_amount_gb': 1000,
            'state': faculty_storage_allocation_request_state_schema(),
        }

        # Execute
        request = FacultyStorageAllocationRequestService.create_request(data)

        # Assert - verify in database
        db_request = FacultyStorageAllocationRequest.objects.get(id=request.id)
        assert db_request.project == test_project
        assert db_request.requester == test_user
        assert db_request.pi == test_pi
        assert db_request.requested_amount_gb == 1000
        assert db_request.status.name == 'Under Review'

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.StorageRequestNotificationService')
    def test_create_request_sends_notification(
        self, mock_notification, test_project, test_user, test_pi
    ):
        """Test create_request() triggers notification."""
        # Setup
        data = {
            'status': 'Under Review',
            'project': test_project,
            'requester': test_user,
            'pi': test_pi,
            'requested_amount_gb': 1000,
            'state': faculty_storage_allocation_request_state_schema(),
        }

        # Execute
        request = FacultyStorageAllocationRequestService.create_request(data)

        # Assert - notification was called
        mock_notification.send_request_created_email.assert_called_once()
        call_args = mock_notification.send_request_created_email.call_args
        assert call_args[0][0].id == request.id


@pytest.mark.component
class TestRequestServiceApproval:
    """Test request approval with database."""

    def test_approve_request_updates_database(
        self, test_project, test_user, test_pi
    ):
        """Test approve_request() persists changes to database."""
        # Setup - create request
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Execute
        FacultyStorageAllocationRequestService.approve_request(request)

        # Assert - verify in database
        db_request = FacultyStorageAllocationRequest.objects.get(id=request.id)
        assert db_request.status.name == 'Approved - Queued'
        assert db_request.approved_amount_gb == 1000
        assert db_request.approval_time is not None

    def test_approve_request_sets_approved_amount_default(
        self, test_project, test_user, test_pi
    ):
        """Test approve_request() defaults approved_amount to
        requested_amount."""
        # Setup
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1500
        )
        # approved_amount_gb is None initially

        # Execute
        FacultyStorageAllocationRequestService.approve_request(request)

        # Assert
        db_request = FacultyStorageAllocationRequest.objects.get(id=request.id)
        assert db_request.approved_amount_gb == 1500

    def test_approve_request_keeps_custom_approved_amount(
        self, test_project, test_user, test_pi
    ):
        """Test approve_request() preserves existing approved_amount."""
        # Setup
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=2000,
            approved_amount_gb=1000  # Custom amount
        )

        # Execute
        FacultyStorageAllocationRequestService.approve_request(request)

        # Assert - custom amount preserved
        db_request = FacultyStorageAllocationRequest.objects.get(id=request.id)
        assert db_request.approved_amount_gb == 1000


@pytest.mark.component
class TestRequestServiceStateManagement:
    """Test state update methods with database."""

    def test_update_eligibility_state_persists_changes(
        self, test_fsa_request
    ):
        """Test update_eligibility_state() saves to database."""
        # Execute
        FacultyStorageAllocationRequestService.update_eligibility_state(
            test_fsa_request, 'Approved', 'PI is eligible'
        )

        # Assert - verify in database
        db_request = FacultyStorageAllocationRequest.objects.get(
            id=test_fsa_request.id
        )
        assert db_request.state['eligibility']['status'] == 'Approved'
        assert db_request.state['eligibility']['justification'] == \
            'PI is eligible'
        assert db_request.state['eligibility']['timestamp'] is not None

    def test_update_intake_consistency_state_persists_changes(
        self, test_fsa_request
    ):
        """Test update_intake_consistency_state() saves to database."""
        # Execute
        FacultyStorageAllocationRequestService\
            .update_intake_consistency_state(
                test_fsa_request, 'Denied', 'Inconsistent data'
            )

        # Assert
        db_request = FacultyStorageAllocationRequest.objects.get(
            id=test_fsa_request.id
        )
        assert db_request.state['intake_consistency']['status'] == 'Denied'
        assert 'Inconsistent data' in \
            db_request.state['intake_consistency']['justification']

    def test_update_setup_state_persists_directory_name(
        self, test_fsa_request
    ):
        """Test update_setup_state() saves directory_name to database."""
        # Execute
        FacultyStorageAllocationRequestService.update_setup_state(
            test_fsa_request,
            directory_name='fc_custom_dir',
            status='Complete'
        )

        # Assert
        db_request = FacultyStorageAllocationRequest.objects.get(
            id=test_fsa_request.id
        )
        assert db_request.state['setup']['directory_name'] == 'fc_custom_dir'
        assert db_request.state['setup']['status'] == 'Complete'

    def test_update_other_state_persists_denial_reason(
        self, test_fsa_request
    ):
        """Test update_other_state() saves denial reason to database."""
        # Execute
        FacultyStorageAllocationRequestService.update_other_state(
            test_fsa_request, 'Custom denial reason'
        )

        # Assert
        db_request = FacultyStorageAllocationRequest.objects.get(
            id=test_fsa_request.id
        )
        assert db_request.state['other']['justification'] == \
            'Custom denial reason'


@pytest.mark.component
class TestRequestServiceCompletion:
    """Test request completion workflow with database."""

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.DirectoryService')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.StorageRequestNotificationService')
    def test_complete_request_updates_status_and_timestamp(
        self, mock_notification, mock_directory_service,
        approved_fsa_request
    ):
        """Test complete_request() updates request status and completion
        time."""
        # Setup
        mock_service_instance = Mock()
        mock_service_instance.directory_exists.return_value = False
        mock_service_instance.create_directory.return_value = Mock()
        mock_service_instance.set_directory_quota.return_value = None
        mock_service_instance.add_project_users_to_directory.return_value = []  # Return empty list
        mock_directory_service.return_value = mock_service_instance

        # Execute
        FacultyStorageAllocationRequestService.complete_request(
            approved_fsa_request, 'fc_test_dir'
        )

        # Assert
        db_request = FacultyStorageAllocationRequest.objects.get(
            id=approved_fsa_request.id
        )
        assert db_request.status.name == 'Approved - Complete'
        assert db_request.completion_time is not None
        assert db_request.state['setup']['directory_name'] == 'fc_test_dir'

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.DirectoryService')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.StorageRequestNotificationService')
    def test_complete_request_is_idempotent(
        self, mock_notification, mock_directory_service,
        approved_fsa_request
    ):
        """Test complete_request() can be called multiple times safely."""
        # Setup
        mock_service_instance = Mock()
        mock_service_instance.directory_exists.return_value = False
        mock_service_instance.create_directory.return_value = Mock()
        mock_service_instance.set_directory_quota.return_value = None
        mock_service_instance.add_project_users_to_directory.return_value = []  # Return empty list
        mock_directory_service.return_value = mock_service_instance

        # Execute - complete twice
        FacultyStorageAllocationRequestService.complete_request(
            approved_fsa_request, 'fc_test_dir'
        )

        first_completion_time = approved_fsa_request.completion_time

        # Refresh from DB
        approved_fsa_request.refresh_from_db()

        FacultyStorageAllocationRequestService.complete_request(
            approved_fsa_request, 'fc_test_dir'
        )

        # Assert - completion time shouldn't change
        # (second call should be skipped)
        assert approved_fsa_request.completion_time == first_completion_time


@pytest.mark.component
class TestRequestServiceDenial:
    """Test request denial with database."""

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.StorageRequestNotificationService')
    def test_deny_request_updates_database(
        self, mock_notification, test_fsa_request
    ):
        """Test deny_request() persists denial to database."""
        # Execute
        FacultyStorageAllocationRequestService.deny_request(
            test_fsa_request
        )

        # Assert
        db_request = FacultyStorageAllocationRequest.objects.get(
            id=test_fsa_request.id
        )
        assert db_request.status.name == 'Denied'

    def test_undeny_request_resets_state(
        self, test_project, test_user, test_pi
    ):
        """Test undeny_request() resets denied state back to Under Review."""
        # Setup - create and deny a request
        request = create_fsa_request(
            status='Denied',
            project=test_project,
            requester=test_user,
            pi=test_pi
        )

        # Set denial state
        update_request_state(
            request, 'eligibility', 'Denied',
            justification='Not eligible'
        )
        request.save()

        # Execute
        FacultyStorageAllocationRequestService.undeny_request(request)

        # Assert - status reset
        db_request = FacultyStorageAllocationRequest.objects.get(id=request.id)
        assert db_request.status.name == 'Under Review'
        assert db_request.state['eligibility']['status'] == 'Pending'


@pytest.mark.component
class TestRequestServiceClaiming:
    """Test request claiming with database."""

    def test_claim_next_request_returns_oldest_queued(
        self, test_project, test_user, test_pi
    ):
        """Test claim_next_request() returns oldest queued request."""
        # Setup - create 3 queued requests
        request1 = create_fsa_request(
            status='Approved - Queued',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            approved_amount_gb=1000
        )
        request1.approval_time = timezone.now() - timedelta(hours=2)
        request1.save()

        request2 = create_fsa_request(
            status='Approved - Queued',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            approved_amount_gb=1000
        )
        request2.approval_time = timezone.now() - timedelta(hours=1)
        request2.save()

        request3 = create_fsa_request(
            status='Approved - Queued',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            approved_amount_gb=1000
        )
        request3.approval_time = timezone.now()
        request3.save()

        # Execute
        claimed = FacultyStorageAllocationRequestService.claim_next_request()

        # Assert - oldest request (request1) is claimed
        assert claimed.id == request1.id
        assert claimed.status.name == 'Approved - Processing'

        # Verify in database
        db_request = FacultyStorageAllocationRequest.objects.get(
            id=request1.id
        )
        assert db_request.status.name == 'Approved - Processing'

    def test_claim_next_request_returns_none_when_queue_empty(self, db):
        """Test claim_next_request() returns None when no requests queued."""
        # Execute - no queued requests exist
        claimed = FacultyStorageAllocationRequestService.claim_next_request()

        # Assert
        assert claimed is None

    def test_claim_next_request_recovers_stale_processing_requests(
        self, test_project, test_user, test_pi
    ):
        """Test claim_next_request() reclaims stuck Processing requests."""
        # Setup - create request stuck in Processing state for 35 minutes
        # (past the 30-minute timeout)
        request = create_fsa_request(
            status='Approved - Processing',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            approved_amount_gb=1000
        )

        # Manually set modified time to 35 minutes ago
        old_time = timezone.now() - timedelta(minutes=35)
        FacultyStorageAllocationRequest.objects.filter(
            id=request.id
        ).update(modified=old_time)

        # Execute
        claimed = FacultyStorageAllocationRequestService.claim_next_request()

        # Assert - stale request was reclaimed
        assert claimed is not None
        assert claimed.id == request.id
        assert claimed.status.name == 'Approved - Processing'


@pytest.mark.component
class TestRequestServiceWorkflows:
    """Test complete end-to-end workflows with database."""

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.DirectoryService')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.StorageRequestNotificationService')
    def test_full_approval_workflow(
        self, mock_notification, mock_directory_service,
        test_project, test_user, test_pi
    ):
        """Test complete workflow: create → approve → claim → complete."""
        # Setup
        mock_service_instance = Mock()
        mock_service_instance.directory_exists.return_value = False
        mock_service_instance.create_directory.return_value = Mock()
        mock_service_instance.set_directory_quota.return_value = None
        mock_service_instance.add_project_users_to_directory.return_value = []  # Return empty list
        mock_directory_service.return_value = mock_service_instance

        # Step 1: Create request
        data = {
            'status': 'Under Review',
            'project': test_project,
            'requester': test_user,
            'pi': test_pi,
            'requested_amount_gb': 1000,
            'state': faculty_storage_allocation_request_state_schema(),
        }
        request = FacultyStorageAllocationRequestService.create_request(data)
        assert request.status.name == 'Under Review'

        # Step 2: Approve request
        FacultyStorageAllocationRequestService.approve_request(request)
        request.refresh_from_db()
        assert request.status.name == 'Approved - Queued'
        assert request.approved_amount_gb == 1000

        # Step 3: Claim request
        claimed = FacultyStorageAllocationRequestService.claim_next_request()
        assert claimed.id == request.id
        assert claimed.status.name == 'Approved - Processing'

        # Step 4: Complete request
        FacultyStorageAllocationRequestService.complete_request(
            claimed, 'fc_test_dir'
        )
        claimed.refresh_from_db()
        assert claimed.status.name == 'Approved - Complete'
        assert claimed.completion_time is not None

    def test_denial_workflow(self, test_project, test_user, test_pi):
        """Test denial workflow: create → review → deny → undeny."""
        # Step 1: Create request
        data = {
            'status': 'Under Review',
            'project': test_project,
            'requester': test_user,
            'pi': test_pi,
            'requested_amount_gb': 1000,
            'state': faculty_storage_allocation_request_state_schema(),
        }
        request = FacultyStorageAllocationRequestService.create_request(data)

        # Step 2: Update eligibility to denied
        FacultyStorageAllocationRequestService.update_eligibility_state(
            request, 'Denied', 'PI not eligible'
        )

        # Step 3: Deny request
        FacultyStorageAllocationRequestService.deny_request(request)
        request.refresh_from_db()
        assert request.status.name == 'Denied'

        # Step 4: Undeny request (admin changes mind)
        FacultyStorageAllocationRequestService.undeny_request(request)
        request.refresh_from_db()
        assert request.status.name == 'Under Review'
        assert request.state['eligibility']['status'] == 'Pending'
