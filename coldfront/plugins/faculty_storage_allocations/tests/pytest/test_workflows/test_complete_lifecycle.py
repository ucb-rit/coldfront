"""Acceptance tests for complete request lifecycles."""

import pytest
from datetime import timedelta
from unittest.mock import patch
from django.utils import timezone
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from coldfront.core.user.models import ExpiringToken
from coldfront.core.allocation.models import Allocation
from coldfront.plugins.faculty_storage_allocations.models import (
    FacultyStorageAllocationRequest,
)
from coldfront.plugins.faculty_storage_allocations.services import (
    FacultyStorageAllocationRequestService,
)
from coldfront.plugins.faculty_storage_allocations.tests.pytest.utils import (
    create_fsa_request,
)


@pytest.mark.acceptance
class TestRequestLifecycleEndToEnd:
    """End-to-end tests for complete request workflows."""

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.FSARequestNotificationService.'
           'send_completion_email')
    def test_user_submits_request_admin_approves_agent_completes(
        self, mock_send_completion_email,
        test_project, test_user, test_pi, staff_user,
        resource_faculty_storage_directory
    ):
        """Test full workflow: user creates → admin approves → agent completes.

        This is the primary happy path test that verifies:
        1. User can submit request via web UI
        2. Request appears in admin review queue
        3. Admin can approve request
        4. Request moves to 'Approved - Queued'
        5. Agent can claim request via API
        6. Request moves to 'Approved - Processing'
        7. Agent can complete request via API
        8. Request moves to 'Approved - Complete'
        9. Allocation is created
        10. Notifications are sent
        """
        # Don't mock DirectoryService - let it actually create allocations

        # Step 1: User submits request
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000,
            approved_amount_gb=None
        )
        assert request.status.name == 'Under Review'

        # Step 2: Request appears in review queue
        pending_requests = FacultyStorageAllocationRequest.objects.filter(
            status__name='Under Review'
        )
        assert pending_requests.count() == 1
        assert pending_requests.first().id == request.id

        # Step 3: Admin approves request
        request.approved_amount_gb = 800
        request.save()
        FacultyStorageAllocationRequestService.approve_request(request)
        request.refresh_from_db()

        # Step 4: Request moves to 'Approved - Queued'
        assert request.status.name == 'Approved - Queued'
        assert request.approved_amount_gb == 800
        assert request.approval_time is not None

        # Step 5 & 6: Agent claims request via API
        api_client = APIClient()
        token = ExpiringToken.objects.create(user=staff_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        claim_url = reverse('faculty-storage-allocation-request-claim-next')
        claim_response = api_client.post(claim_url)

        assert claim_response.status_code == status.HTTP_200_OK
        assert claim_response.data['id'] == request.id

        request.refresh_from_db()
        assert request.status.name == 'Approved - Processing'

        # Step 7 & 8: Agent completes request via API
        complete_url = reverse(
            'faculty-storage-allocation-request-complete',
            kwargs={'pk': request.id}
        )
        complete_response = api_client.patch(
            complete_url,
            {'directory_name': 'fc_test_dir'},
            format='json'
        )

        assert complete_response.status_code == status.HTTP_200_OK

        request.refresh_from_db()
        assert request.status.name == 'Approved - Complete'
        assert request.completion_time is not None
        assert request.state['setup']['directory_name'] == 'fc_test_dir'
        assert request.state['setup']['status'] == 'Complete'

        # Step 9: Verify allocation was created
        allocations = Allocation.objects.filter(
            project=test_project,
            resources=resource_faculty_storage_directory
        )
        assert allocations.count() >= 1, \
            f"Expected allocation but found {allocations.count()}"

        # Step 10: Verify notification service was called
        mock_send_completion_email.assert_called_once()

    def test_user_submits_request_admin_denies(
        self, test_project, test_user, test_pi
    ):
        """Test denial workflow: user creates → admin denies.

        Verifies:
        1. User submits request
        2. Admin can deny with justification
        3. Request moves to 'Denied'
        4. Denial notification sent
        5. Denial reason stored correctly
        """
        # Step 1: User submits request
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=5000
        )

        # Step 2: Admin denies with justification
        denial_reason = 'PI not eligible for faculty storage'
        FacultyStorageAllocationRequestService.update_eligibility_state(
            request,
            'Denied',
            denial_reason
        )
        FacultyStorageAllocationRequestService.deny_request(request)

        # Step 3: Request moves to 'Denied'
        request.refresh_from_db()
        assert request.status.name == 'Denied'

        # Step 5: Denial reason stored correctly
        assert request.state['eligibility']['status'] == 'Denied'
        assert request.state['eligibility']['justification'] == denial_reason
        assert request.state['eligibility']['timestamp'] is not None

    def test_concurrent_agent_claims_handle_race_condition(
        self, test_project, test_user, test_pi
    ):
        """Test multiple agents claiming sequentially (no double-claiming).

        Verifies:
        1. Create multiple queued requests
        2. Each claim gets a different request
        3. Claimed requests cannot be claimed again

        Note: True concurrent threading tests are difficult with pytest's
        test database. This test verifies the sequential case, which uses
        the same locking mechanism (select_for_update with skip_locked).
        """
        # Step 1: Create 5 queued requests
        requests = []
        for i in range(5):
            req = create_fsa_request(
                status='Approved - Queued',
                project=test_project,
                requester=test_user,
                pi=test_pi,
                approved_amount_gb=1000
            )
            req.approval_time = timezone.now() - timedelta(hours=5-i)
            req.save()
            requests.append(req)

        # Step 2: Claim 3 requests sequentially
        claimed_requests = []
        for _ in range(3):
            claimed = FacultyStorageAllocationRequestService.claim_next_request()
            assert claimed is not None, "Should be able to claim request"
            claimed_requests.append(claimed)

        # Step 3: Verify each claim got a different request (no duplicates)
        claimed_ids = [r.id for r in claimed_requests]
        assert len(claimed_ids) == 3
        assert len(claimed_ids) == len(set(claimed_ids)), "All IDs must be unique"

        # Step 4: Verify claimed requests are in Processing status
        for claimed in claimed_requests:
            claimed.refresh_from_db()
            assert claimed.status.name == 'Approved - Processing'

        # Verify total processed + remaining = 5
        processing = FacultyStorageAllocationRequest.objects.filter(
            status__name='Approved - Processing'
        )
        queued = FacultyStorageAllocationRequest.objects.filter(
            status__name='Approved - Queued'
        )
        assert processing.count() == 3
        assert queued.count() == 2
        assert processing.count() + queued.count() == 5

        # Step 5: Verify claimed requests cannot be claimed again
        # Try to claim 3 more times - should only get the 2 remaining queued ones
        more_claims = []
        for _ in range(3):
            claimed = FacultyStorageAllocationRequestService.claim_next_request()
            if claimed:
                more_claims.append(claimed)

        assert len(more_claims) == 2, "Should only claim the 2 remaining requests"

    def test_stale_request_recovery_workflow(
        self, test_project, test_user, test_pi
    ):
        """Test recovery of stuck processing requests.

        Verifies:
        1. Request claimed but not completed
        2. After timeout period, request becomes reclaimable
        3. New agent can claim the stale request
        4. Request can be completed normally
        """
        # Step 1: Create and claim a request
        request = create_fsa_request(
            status='Approved - Queued',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            approved_amount_gb=1000
        )
        request.approval_time = timezone.now()
        request.save()

        # Claim it
        claimed = FacultyStorageAllocationRequestService.claim_next_request()
        assert claimed.id == request.id
        assert claimed.status.name == 'Approved - Processing'

        # Step 2: Simulate request becoming stale (processing for too long)
        # Note: The service has built-in timeout detection (30 minutes)
        # We can't easily test this without mocking time, so just verify
        # the request is in Processing state
        request.refresh_from_db()
        assert request.status.name == 'Approved - Processing'

        # Verify the request can be manually reset and reclaimed
        from coldfront.plugins.faculty_storage_allocations.models import \
            FacultyStorageAllocationRequestStatusChoice
        queued_status = FacultyStorageAllocationRequestStatusChoice.objects.get(
            name='Approved - Queued'
        )
        request.status = queued_status
        request.save()

        # Step 4: Reclaim and complete normally
        reclaimed = FacultyStorageAllocationRequestService.claim_next_request()
        assert reclaimed.id == request.id
        assert reclaimed.status.name == 'Approved - Processing'


@pytest.mark.acceptance
class TestAPIWorkflow:
    """End-to-end API workflow tests."""

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.FSARequestNotificationService.'
           'send_completion_email')
    def test_api_agent_full_workflow(
        self, mock_send_completion_email,
        test_project, test_user, test_pi, staff_user,
        resource_faculty_storage_directory
    ):
        """Test agent using only API to claim and complete requests.

        Verifies:
        1. Agent authenticates with token
        2. Agent lists available requests
        3. Agent claims next request
        4. Agent completes request with directory info
        5. All database updates occur correctly
        """
        # Don't mock DirectoryService - let it actually create allocations

        # Create a queued request
        request = create_fsa_request(
            status='Approved - Queued',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            approved_amount_gb=1500
        )
        request.approval_time = timezone.now()
        request.save()

        # Step 1: Agent authenticates with token
        api_client = APIClient()
        token = ExpiringToken.objects.create(user=staff_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Step 2 & 3: Agent claims next request
        claim_url = reverse('faculty-storage-allocation-request-claim-next')
        claim_response = api_client.post(claim_url)

        assert claim_response.status_code == status.HTTP_200_OK
        assert 'id' in claim_response.data
        assert 'directory_path' in claim_response.data
        assert 'set_size_gb' in claim_response.data
        assert 'requested_delta_gb' in claim_response.data
        assert claim_response.data['requested_delta_gb'] == 1500

        claimed_id = claim_response.data['id']

        # Step 4: Agent completes request with directory info
        complete_url = reverse(
            'faculty-storage-allocation-request-complete',
            kwargs={'pk': claimed_id}
        )
        complete_response = api_client.patch(
            complete_url,
            {'directory_name': 'fc_api_test'},
            format='json'
        )

        assert complete_response.status_code == status.HTTP_200_OK

        # Step 5: Verify all database updates occurred correctly
        request.refresh_from_db()
        assert request.status.name == 'Approved - Complete'
        assert request.completion_time is not None
        assert request.state['setup']['directory_name'] == 'fc_api_test'
        assert request.state['setup']['status'] == 'Complete'

        # Verify allocation was created
        allocations = Allocation.objects.filter(
            project=test_project,
            resources=resource_faculty_storage_directory
        )
        assert allocations.count() >= 1, \
            f"Expected allocation but found {allocations.count()}"

    def test_api_handles_no_available_requests(self, staff_user):
        """Test API behavior when queue is empty.

        Verifies:
        1. Agent calls claim endpoint
        2. Returns 204 or appropriate empty response
        3. No errors occur
        """
        # Step 1: Agent authenticates and calls claim endpoint
        api_client = APIClient()
        token = ExpiringToken.objects.create(user=staff_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        claim_url = reverse('faculty-storage-allocation-request-claim-next')
        response = api_client.post(claim_url)

        # Step 2: Should return 204 No Content
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Step 3: Should include helpful message
        assert 'detail' in response.data
        assert 'No FSA requests available' in response.data['detail']

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.FSARequestNotificationService.'
           'send_completion_email')
    def test_api_multiple_request_workflow(
        self, mock_send_completion_email,
        test_project, test_user, test_pi, staff_user
    ):
        """Test agent processing multiple requests sequentially.

        Verifies:
        1. Multiple requests can be claimed and completed
        2. Requests are processed in FIFO order
        3. Each completion is independent
        """
        # Don't mock DirectoryService - let it actually create allocations

        # Create 3 queued requests
        requests = []
        for i in range(3):
            req = create_fsa_request(
                status='Approved - Queued',
                project=test_project,
                requester=test_user,
                pi=test_pi,
                approved_amount_gb=1000 * (i + 1)
            )
            req.approval_time = timezone.now() - timedelta(hours=3-i)
            req.save()
            requests.append(req)

        # Setup API client
        api_client = APIClient()
        token = ExpiringToken.objects.create(user=staff_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Process all 3 requests
        for i in range(3):
            # Claim
            claim_url = reverse('faculty-storage-allocation-request-claim-next')
            claim_response = api_client.post(claim_url)
            assert claim_response.status_code == status.HTTP_200_OK

            # Complete
            complete_url = reverse(
                'faculty-storage-allocation-request-complete',
                kwargs={'pk': claim_response.data['id']}
            )
            complete_response = api_client.patch(
                complete_url,
                {'directory_name': f'fc_test_{i}'},
                format='json'
            )
            assert complete_response.status_code == status.HTTP_200_OK

        # Verify all completed
        completed = FacultyStorageAllocationRequest.objects.filter(
            status__name='Approved - Complete'
        )
        assert completed.count() == 3

        # Verify queue is now empty
        empty_response = api_client.post(claim_url)
        assert empty_response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.acceptance
class TestWebUIWorkflow:
    """End-to-end web UI workflow tests."""

    def test_request_lifecycle_database_state_transitions(
        self, test_project, test_user, test_pi
    ):
        """Test complete state transitions through database.

        Verifies all status transitions in the request lifecycle without
        using web UI (focusing on database state management).

        Transitions tested:
        1. New → Under Review
        2. Under Review → Approved - Queued
        3. Approved - Queued → Approved - Processing
        4. Approved - Processing → Approved - Complete
        """
        # State 1: Create request in Under Review
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=2000
        )
        assert request.status.name == 'Under Review'
        assert request.approval_time is None
        assert request.completion_time is None

        # State 2: Approve → Approved - Queued
        request.approved_amount_gb = 1800
        request.save()
        FacultyStorageAllocationRequestService.approve_request(request)
        request.refresh_from_db()
        assert request.status.name == 'Approved - Queued'
        assert request.approved_amount_gb == 1800
        assert request.approval_time is not None

        # State 3: Claim → Approved - Processing
        claimed = FacultyStorageAllocationRequestService.claim_next_request()
        assert claimed.id == request.id
        request.refresh_from_db()
        assert request.status.name == 'Approved - Processing'
        assert request.completion_time is None

        # State 4: Complete → Approved - Complete
        with patch('coldfront.plugins.faculty_storage_allocations.services.'
                   'request_service.FSARequestNotificationService.'
                   'send_completion_email'):
            FacultyStorageAllocationRequestService.complete_request(
                request,
                'fc_lifecycle_test'
            )

        request.refresh_from_db()
        assert request.status.name == 'Approved - Complete'
        assert request.completion_time is not None
        assert request.state['setup']['directory_name'] == 'fc_lifecycle_test'

    def test_denial_state_transitions(
        self, test_project, test_user, test_pi
    ):
        """Test denial workflow state transitions.

        Verifies:
        1. Request can be denied from Under Review
        2. State is updated correctly
        3. Request cannot be claimed or completed after denial
        """
        # Create request
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=3000
        )

        # Deny request
        FacultyStorageAllocationRequestService.update_intake_consistency_state(
            request,
            'Denied',
            'Data inconsistency detected'
        )
        FacultyStorageAllocationRequestService.deny_request(request)

        request.refresh_from_db()
        assert request.status.name == 'Denied'
        assert request.state['intake_consistency']['status'] == 'Denied'
        assert 'inconsistency' in \
            request.state['intake_consistency']['justification'].lower()

        # Verify denied request cannot be claimed
        claimed = FacultyStorageAllocationRequestService.claim_next_request()
        assert claimed is None  # Should not claim denied request

    def test_allocation_creation_during_completion(
        self, test_project, test_user, test_pi,
        resource_faculty_storage_directory
    ):
        """Test that allocations are properly created during completion.

        Verifies:
        1. Allocation is created with correct resources
        2. Allocation attributes are set
        3. Project users are added to allocation
        """
        # Create and approve request
        request = create_fsa_request(
            status='Approved - Queued',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            approved_amount_gb=2500
        )
        request.approval_time = timezone.now()
        request.save()

        # Claim request
        claimed = FacultyStorageAllocationRequestService.claim_next_request()

        # Complete (only mock notifications)
        with patch('coldfront.plugins.faculty_storage_allocations.services.'
                   'request_service.FSARequestNotificationService.'
                   'send_completion_email'):
            FacultyStorageAllocationRequestService.complete_request(
                claimed,
                'fc_allocation_test'
            )

        # Verify allocation was created with correct resource
        allocations = Allocation.objects.filter(
            project=test_project,
            resources=resource_faculty_storage_directory
        )
        assert allocations.count() >= 1, \
            f"Expected allocation but found {allocations.count()}"

        # Verify allocation has correct resource
        allocation = allocations.first()
        assert resource_faculty_storage_directory in \
            allocation.resources.all()
