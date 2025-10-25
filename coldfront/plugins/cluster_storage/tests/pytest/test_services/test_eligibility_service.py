"""Tests for StorageRequestEligibilityService.

This module contains both unit tests (mocked) and component tests (with DB)
for the eligibility service.

Unit tests focus on business logic by mocking the database.
Component tests verify actual database queries work correctly.
"""

import pytest
from unittest.mock import Mock, patch

from coldfront.plugins.cluster_storage.services import (
    StorageRequestEligibilityService
)


# ============================================================================
# Unit Tests (No Database - Fast)
# ============================================================================

@pytest.mark.unit
class TestEligibilityServiceUnit:
    """Unit tests for eligibility checking logic (mocked DB)."""

    @patch('coldfront.plugins.cluster_storage.services.'
           'eligibility_service.FacultyStorageAllocationRequest')
    def test_is_eligible_when_no_existing_requests(
        self, mock_request_model, mock_user
    ):
        """Test PI is eligible when they have no existing requests."""
        # Mock the database query to return no results
        mock_request_model.objects.filter.return_value.exclude.return_value\
            .exists.return_value = False

        # Execute
        is_eligible, reason = StorageRequestEligibilityService\
            .is_eligible_for_request(mock_user)

        # Assert
        assert is_eligible is True
        assert reason == ''

        # Verify the query was constructed correctly
        mock_request_model.objects.filter.assert_called_once_with(
            pi=mock_user
        )
        mock_request_model.objects.filter.return_value.exclude\
            .assert_called_once_with(status__name='Denied')

    @patch('coldfront.plugins.cluster_storage.services.'
           'eligibility_service.FacultyStorageAllocationRequest')
    def test_is_not_eligible_when_has_non_denied_request(
        self, mock_request_model, mock_user
    ):
        """Test PI is not eligible when they have existing non-denied
        request."""
        # Mock the database query to return existing request
        mock_request_model.objects.filter.return_value.exclude.return_value\
            .exists.return_value = True

        # Execute
        is_eligible, reason = StorageRequestEligibilityService\
            .is_eligible_for_request(mock_user)

        # Assert
        assert is_eligible is False
        assert 'already has an existing non-denied' in reason

    @patch('coldfront.plugins.cluster_storage.services.'
           'eligibility_service.FacultyStorageAllocationRequest')
    def test_excludes_denied_status_from_check(
        self, mock_request_model, mock_user
    ):
        """Test that denied requests are excluded from eligibility check."""
        # Mock the query chain
        mock_queryset = Mock()
        mock_request_model.objects.filter.return_value = mock_queryset
        mock_queryset.exclude.return_value.exists.return_value = False

        # Execute
        StorageRequestEligibilityService.is_eligible_for_request(mock_user)

        # Verify that exclude was called with correct status
        mock_queryset.exclude.assert_called_once_with(status__name='Denied')


# ============================================================================
# Component Tests (With Database - Integration)
# ============================================================================

@pytest.mark.component
class TestEligibilityServiceComponent:
    """Component tests for eligibility service (real DB queries)."""

    def test_is_eligible_when_no_existing_requests(self, test_pi):
        """Test PI is eligible when they have no existing requests in DB."""
        # Execute
        is_eligible, reason = StorageRequestEligibilityService\
            .is_eligible_for_request(test_pi)

        # Assert
        assert is_eligible is True
        assert reason == ''

    def test_is_not_eligible_when_has_under_review_request(
        self, test_pi, test_project, test_user,
        storage_request_status_pending
    ):
        """Test PI is not eligible when they have 'Under Review' request."""
        # Setup - Create existing request with 'Under Review' status
        from coldfront.plugins.cluster_storage.models import (
            FacultyStorageAllocationRequest,
            faculty_storage_allocation_request_state_schema,
        )

        FacultyStorageAllocationRequest.objects.create(
            status=storage_request_status_pending,
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000,
            state=faculty_storage_allocation_request_state_schema(),
        )

        # Execute
        is_eligible, reason = StorageRequestEligibilityService\
            .is_eligible_for_request(test_pi)

        # Assert
        assert is_eligible is False
        assert 'already has an existing non-denied' in reason

    def test_is_not_eligible_when_has_approved_request(
        self, test_pi, approved_storage_request
    ):
        """Test PI is not eligible when they have approved request."""
        # Setup - approved_storage_request fixture creates request in DB
        # Verify the fixture created the request
        assert approved_storage_request.pi == test_pi
        assert approved_storage_request.status.name == 'Approved - Queued'

        # Execute
        is_eligible, reason = StorageRequestEligibilityService\
            .is_eligible_for_request(test_pi)

        # Assert
        assert is_eligible is False
        assert 'already has an existing non-denied' in reason

    def test_is_eligible_when_only_has_denied_requests(
        self, test_pi, test_project, test_user, storage_request_status_denied
    ):
        """Test PI is eligible when they only have denied requests."""
        # Setup - Create denied request
        from coldfront.plugins.cluster_storage.models import (
            FacultyStorageAllocationRequest,
            faculty_storage_allocation_request_state_schema,
        )

        state = faculty_storage_allocation_request_state_schema()
        state['eligibility']['status'] = 'Denied'
        state['eligibility']['justification'] = 'Not eligible'

        FacultyStorageAllocationRequest.objects.create(
            status=storage_request_status_denied,
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000,
            state=state,
        )

        # Execute
        is_eligible, reason = StorageRequestEligibilityService\
            .is_eligible_for_request(test_pi)

        # Assert
        assert is_eligible is True
        assert reason == ''

    def test_is_eligible_when_has_multiple_denied_requests(
        self, test_pi, test_project, test_user, storage_request_status_denied
    ):
        """Test PI is eligible even with multiple denied requests."""
        # Setup - Create multiple denied requests
        from coldfront.plugins.cluster_storage.models import (
            FacultyStorageAllocationRequest,
            faculty_storage_allocation_request_state_schema,
        )

        state = faculty_storage_allocation_request_state_schema()
        state['eligibility']['status'] = 'Denied'

        for _ in range(3):
            FacultyStorageAllocationRequest.objects.create(
                status=storage_request_status_denied,
                project=test_project,
                requester=test_user,
                pi=test_pi,
                requested_amount_gb=1000,
                state=state,
            )

        # Execute
        is_eligible, reason = StorageRequestEligibilityService\
            .is_eligible_for_request(test_pi)

        # Assert
        assert is_eligible is True
        assert reason == ''

    @pytest.mark.parametrize('status_name', [
        'Under Review',
        'Approved - Queued',
        'Approved - Processing',
        'Approved - Complete',
    ])
    def test_is_not_eligible_for_each_non_denied_status(
        self, test_pi, test_project, test_user, status_name
    ):
        """Test PI is not eligible for any non-denied status."""
        # Setup - Create request with parametrized status
        from coldfront.plugins.cluster_storage.models import (
            FacultyStorageAllocationRequest,
            FacultyStorageAllocationRequestStatusChoice,
            faculty_storage_allocation_request_state_schema,
        )

        status, _ = FacultyStorageAllocationRequestStatusChoice.objects\
            .get_or_create(name=status_name)

        FacultyStorageAllocationRequest.objects.create(
            status=status,
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000,
            state=faculty_storage_allocation_request_state_schema(),
        )

        # Execute
        is_eligible, reason = StorageRequestEligibilityService\
            .is_eligible_for_request(test_pi)

        # Assert
        assert is_eligible is False
        assert 'already has an existing non-denied' in reason
