"""Unit tests for FacultyStorageAllocationRequest model."""

import pytest

from coldfront.plugins.faculty_storage_allocations.tests.pytest.utils import (
    create_fsa_request,
)


@pytest.mark.unit
class TestFacultyStorageAllocationRequestModel:
    """Unit tests for model methods and properties."""

    def test_denial_reason_returns_correct_category_for_eligibility_denial(
        self, test_project, test_pi, test_user
    ):
        """Test denial_reason() returns eligibility category when denied at eligibility stage."""
        # Create a denied request with eligibility denial
        request = create_fsa_request(
            status='Denied',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Set eligibility as the denial reason
        request.state['eligibility']['status'] = 'Denied'
        request.state['eligibility']['justification'] = 'PI not eligible'
        request.state['eligibility']['timestamp'] = '2024-01-15T10:30:00Z'
        request.save()

        # Get denial reason
        reason = request.denial_reason()

        assert reason.category == 'Eligibility'
        assert reason.justification == 'PI not eligible'
        assert reason.timestamp == '2024-01-15T10:30:00Z'

    def test_denial_reason_returns_correct_category_for_intake_consistency_denial(
        self, test_project, test_pi, test_user
    ):
        """Test denial_reason() returns intake consistency category when denied at that stage."""
        # Create a denied request with intake consistency denial
        request = create_fsa_request(
            status='Denied',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Set intake consistency as the denial reason
        request.state['intake_consistency']['status'] = 'Denied'
        request.state['intake_consistency']['justification'] = \
            'Amount does not match external form'
        request.state['intake_consistency']['timestamp'] = '2024-01-16T14:00:00Z'
        request.save()

        # Get denial reason
        reason = request.denial_reason()

        assert reason.category == 'Intake Consistency'
        assert reason.justification == 'Amount does not match external form'
        assert reason.timestamp == '2024-01-16T14:00:00Z'

    def test_denial_reason_returns_correct_category_for_other_denial(
        self, test_project, test_pi, test_user
    ):
        """Test denial_reason() returns 'Other' category when denied for other reasons."""
        # Create a denied request with 'other' denial
        request = create_fsa_request(
            status='Denied',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Set 'other' as the denial reason
        request.state['other']['justification'] = 'Some other reason'
        request.state['other']['timestamp'] = '2024-01-17T09:15:00Z'
        request.save()

        # Get denial reason
        reason = request.denial_reason()

        assert reason.category == 'Other'
        assert reason.justification == 'Some other reason'
        assert reason.timestamp == '2024-01-17T09:15:00Z'

    def test_denial_reason_raises_error_if_not_denied(
        self, test_project, test_pi, test_user
    ):
        """Test denial_reason() raises ValueError if request status is not 'Denied'."""
        # Create a non-denied request
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Should raise ValueError
        with pytest.raises(ValueError, match='unexpected status'):
            request.denial_reason()

    def test_denial_reason_raises_error_if_state_is_inconsistent(
        self, test_project, test_pi, test_user
    ):
        """Test denial_reason() raises ValueError if state doesn't have denial information."""
        # Create a denied request with no denial reason in state
        request = create_fsa_request(
            status='Denied',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # State has all fields as 'Pending' with no denial reason
        # This is an inconsistent state (status='Denied' but no field marked as denied)

        # Should raise ValueError due to inconsistent state
        with pytest.raises(ValueError, match='unexpected state'):
            request.denial_reason()

    def test_latest_update_timestamp_returns_most_recent(
        self, test_project, test_pi, test_user
    ):
        """Test latest_update_timestamp() returns the most recent timestamp from all stages."""
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Set different timestamps for different stages
        request.state['eligibility']['timestamp'] = '2024-01-10T10:00:00Z'
        request.state['intake_consistency']['timestamp'] = '2024-01-15T14:30:00Z'
        request.state['setup']['timestamp'] = '2024-01-12T09:00:00Z'
        request.state['other']['timestamp'] = ''  # Empty timestamp
        request.save()

        # Should return the most recent (intake_consistency)
        latest = request.latest_update_timestamp()
        assert latest == '2024-01-15T14:30:00Z'

    def test_latest_update_timestamp_returns_empty_string_if_no_timestamps(
        self, test_project, test_pi, test_user
    ):
        """Test latest_update_timestamp() returns empty string when no timestamps set."""
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # All timestamps are empty by default
        latest = request.latest_update_timestamp()
        assert latest == ''

    def test_str_representation_includes_project_pi_and_amount(
        self, test_project, test_pi, test_user
    ):
        """Test __str__() returns string with project name, PI name, and amount."""
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=2500
        )

        # Convert to string
        str_repr = str(request)

        # Should contain project name, PI name, and amount
        assert test_project.name in str_repr
        assert test_pi.first_name in str_repr
        assert test_pi.last_name in str_repr
        assert '2500 GB' in str_repr
