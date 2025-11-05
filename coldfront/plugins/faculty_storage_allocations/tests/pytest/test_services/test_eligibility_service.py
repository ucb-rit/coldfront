"""Tests for FSARequestEligibilityService.

This module contains both unit tests (mocked) and component tests (with DB)
for the eligibility service.

Unit tests focus on business logic by mocking the database.
Component tests verify actual database queries work correctly.
"""

import pytest
from unittest.mock import Mock, patch, PropertyMock

from coldfront.plugins.faculty_storage_allocations.services import (
    FSARequestEligibilityService
)


# ============================================================================
# Unit Tests (No Database - Fast)
# ============================================================================

@pytest.mark.unit
class TestEligibilityServiceUnit:
    """Unit tests for eligibility checking logic (mocked DB)."""

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.settings')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.EmailAddress')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.FacultyStorageAllocationRequest')
    def test_is_eligible_when_no_existing_requests_and_whitelist_disabled(
        self, mock_request_model, mock_email_address, mock_settings, mock_user
    ):
        """Test PI is eligible when they have no existing requests and
        whitelist is disabled."""
        # Mock settings - whitelist disabled
        mock_settings.ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED = False

        # Mock the database query to return no results
        mock_request_model.objects.filter.return_value.exclude.return_value\
            .exists.return_value = False

        # Execute
        is_eligible, reason = FSARequestEligibilityService\
            .is_eligible_for_request(mock_user)

        # Assert
        assert is_eligible is True
        assert reason == ''

        # Verify email whitelist was not checked
        mock_email_address.objects.filter.assert_not_called()

        # Verify the query was constructed correctly
        mock_request_model.objects.filter.assert_called_once_with(
            pi=mock_user
        )
        mock_request_model.objects.filter.return_value.exclude\
            .assert_called_once_with(status__name='Denied')

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.settings')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.EmailAddress')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.FacultyStorageAllocationRequest')
    def test_is_eligible_when_on_whitelist_and_no_existing_requests(
        self, mock_request_model, mock_email_address, mock_settings, mock_user
    ):
        """Test PI is eligible when they're on whitelist and have no
        existing requests."""
        # Mock settings - whitelist enabled
        mock_settings.ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED = True
        mock_settings.ELIGIBLE_PI_EMAIL_WHITELIST = ['pi@berkeley.edu']

        # Mock user's email addresses
        mock_queryset = Mock()
        mock_queryset.values_list.return_value = ['pi@berkeley.edu']
        mock_email_address.objects.filter.return_value = mock_queryset

        # Mock no existing requests
        mock_request_model.objects.filter.return_value.exclude.return_value\
            .exists.return_value = False

        # Execute
        is_eligible, reason = FSARequestEligibilityService\
            .is_eligible_for_request(mock_user)

        # Assert
        assert is_eligible is True
        assert reason == ''

        # Verify email was checked
        mock_email_address.objects.filter.assert_called_once_with(
            user=mock_user
        )

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.settings')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.EmailAddress')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.FacultyStorageAllocationRequest')
    def test_is_not_eligible_when_not_on_whitelist(
        self, mock_request_model, mock_email_address, mock_settings, mock_user
    ):
        """Test PI is not eligible when they're not on the whitelist."""
        # Mock settings - whitelist enabled
        mock_settings.ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED = True
        mock_settings.ELIGIBLE_PI_EMAIL_WHITELIST = ['other@berkeley.edu']

        # Mock user's email addresses - not on whitelist
        mock_queryset = Mock()
        mock_queryset.values_list.return_value = ['pi@berkeley.edu']
        mock_email_address.objects.filter.return_value = mock_queryset

        # Execute
        is_eligible, reason = FSARequestEligibilityService\
            .is_eligible_for_request(mock_user)

        # Assert
        assert is_eligible is False
        assert 'not on the whitelist' in reason

        # Verify we didn't check for existing requests since whitelist
        # check failed first
        mock_request_model.objects.filter.assert_not_called()

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.settings')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.EmailAddress')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.FacultyStorageAllocationRequest')
    def test_is_eligible_when_any_email_on_whitelist(
        self, mock_request_model, mock_email_address, mock_settings, mock_user
    ):
        """Test PI is eligible when ANY of their emails is on whitelist."""
        # Mock settings - whitelist enabled
        mock_settings.ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED = True
        mock_settings.ELIGIBLE_PI_EMAIL_WHITELIST = ['pi@berkeley.edu']

        # Mock user has multiple emails, one is on whitelist
        mock_queryset = Mock()
        mock_queryset.values_list.return_value = [
            'pi@gmail.com',
            'pi@berkeley.edu',  # This one is on whitelist
            'pi@lbl.gov'
        ]
        mock_email_address.objects.filter.return_value = mock_queryset

        # Mock no existing requests
        mock_request_model.objects.filter.return_value.exclude.return_value\
            .exists.return_value = False

        # Execute
        is_eligible, reason = FSARequestEligibilityService\
            .is_eligible_for_request(mock_user)

        # Assert
        assert is_eligible is True
        assert reason == ''

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.settings')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.EmailAddress')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.FacultyStorageAllocationRequest')
    def test_is_not_eligible_when_has_non_denied_request(
        self, mock_request_model, mock_email_address, mock_settings, mock_user
    ):
        """Test PI is not eligible when they have existing non-denied
        request."""
        # Mock settings - whitelist disabled
        mock_settings.ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED = False

        # Mock the database query to return existing request
        mock_request_model.objects.filter.return_value.exclude.return_value\
            .exists.return_value = True

        # Execute
        is_eligible, reason = FSARequestEligibilityService\
            .is_eligible_for_request(mock_user)

        # Assert
        assert is_eligible is False
        assert 'already has an existing non-denied' in reason

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.settings')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.EmailAddress')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.FacultyStorageAllocationRequest')
    def test_excludes_denied_status_from_check(
        self, mock_request_model, mock_email_address, mock_settings, mock_user
    ):
        """Test that denied requests are excluded from eligibility check."""
        # Mock settings - whitelist disabled
        mock_settings.ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED = False

        # Mock the query chain
        mock_queryset = Mock()
        mock_request_model.objects.filter.return_value = mock_queryset
        mock_queryset.exclude.return_value.exists.return_value = False

        # Execute
        FSARequestEligibilityService.is_eligible_for_request(mock_user)

        # Verify that exclude was called with correct status
        mock_queryset.exclude.assert_called_once_with(status__name='Denied')

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.settings')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.EmailAddress')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.FacultyStorageAllocationRequest')
    def test_whitelist_takes_precedence_over_existing_requests(
        self, mock_request_model, mock_email_address, mock_settings, mock_user
    ):
        """Test that whitelist check happens before existing request check."""
        # Mock settings - whitelist enabled
        mock_settings.ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED = True
        mock_settings.ELIGIBLE_PI_EMAIL_WHITELIST = ['other@berkeley.edu']

        # Mock user's email addresses - not on whitelist
        mock_queryset = Mock()
        mock_queryset.values_list.return_value = ['pi@berkeley.edu']
        mock_email_address.objects.filter.return_value = mock_queryset

        # Execute
        is_eligible, reason = FSARequestEligibilityService\
            .is_eligible_for_request(mock_user)

        # Assert - should fail on whitelist, not check requests
        assert is_eligible is False
        assert 'whitelist' in reason
        mock_request_model.objects.filter.assert_not_called()


# ============================================================================
# Component Tests (With Database - Integration)
# ============================================================================

@pytest.mark.component
class TestEligibilityServiceComponent:
    """Component tests for eligibility service (real DB queries)."""

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.settings')
    def test_is_eligible_when_no_existing_requests(
        self, mock_settings, test_pi
    ):
        """Test PI is eligible when they have no existing requests in DB."""
        # Mock settings - whitelist disabled
        mock_settings.ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED = False

        # Execute
        is_eligible, reason = FSARequestEligibilityService\
            .is_eligible_for_request(test_pi)

        # Assert
        assert is_eligible is True
        assert reason == ''

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.settings')
    def test_is_not_eligible_when_has_under_review_request(
        self, mock_settings, test_pi, test_project, test_user,
        fsa_request_status_pending
    ):
        """Test PI is not eligible when they have 'Under Review' request."""
        # Mock settings - whitelist disabled
        mock_settings.ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED = False

        # Setup - Create existing request with 'Under Review' status
        from coldfront.plugins.faculty_storage_allocations.models import (
            FacultyStorageAllocationRequest,
            faculty_storage_allocation_request_state_schema,
        )

        FacultyStorageAllocationRequest.objects.create(
            status=fsa_request_status_pending,
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000,
            state=faculty_storage_allocation_request_state_schema(),
        )

        # Execute
        is_eligible, reason = FSARequestEligibilityService\
            .is_eligible_for_request(test_pi)

        # Assert
        assert is_eligible is False
        assert 'already has an existing non-denied' in reason

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.settings')
    def test_is_not_eligible_when_has_approved_request(
        self, mock_settings, test_pi, approved_fsa_request
    ):
        """Test PI is not eligible when they have approved request."""
        # Mock settings - whitelist disabled
        mock_settings.ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED = False

        # Setup - approved_fsa_request fixture creates request in DB
        # Verify the fixture created the request
        assert approved_fsa_request.pi == test_pi
        assert approved_fsa_request.status.name == 'Approved - Queued'

        # Execute
        is_eligible, reason = FSARequestEligibilityService\
            .is_eligible_for_request(test_pi)

        # Assert
        assert is_eligible is False
        assert 'already has an existing non-denied' in reason

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.settings')
    def test_is_eligible_when_only_has_denied_requests(
        self, mock_settings, test_pi, test_project, test_user,
        fsa_request_status_denied
    ):
        """Test PI is eligible when they only have denied requests."""
        # Mock settings - whitelist disabled
        mock_settings.ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED = False

        # Setup - Create denied request
        from coldfront.plugins.faculty_storage_allocations.models import (
            FacultyStorageAllocationRequest,
            faculty_storage_allocation_request_state_schema,
        )

        state = faculty_storage_allocation_request_state_schema()
        state['eligibility']['status'] = 'Denied'
        state['eligibility']['justification'] = 'Not eligible'

        FacultyStorageAllocationRequest.objects.create(
            status=fsa_request_status_denied,
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000,
            state=state,
        )

        # Execute
        is_eligible, reason = FSARequestEligibilityService\
            .is_eligible_for_request(test_pi)

        # Assert
        assert is_eligible is True
        assert reason == ''

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.settings')
    def test_is_eligible_when_has_multiple_denied_requests(
        self, mock_settings, test_pi, test_project, test_user,
        fsa_request_status_denied
    ):
        """Test PI is eligible even with multiple denied requests."""
        # Mock settings - whitelist disabled
        mock_settings.ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED = False

        # Setup - Create multiple denied requests
        from coldfront.plugins.faculty_storage_allocations.models import (
            FacultyStorageAllocationRequest,
            faculty_storage_allocation_request_state_schema,
        )

        state = faculty_storage_allocation_request_state_schema()
        state['eligibility']['status'] = 'Denied'

        for _ in range(3):
            FacultyStorageAllocationRequest.objects.create(
                status=fsa_request_status_denied,
                project=test_project,
                requester=test_user,
                pi=test_pi,
                requested_amount_gb=1000,
                state=state,
            )

        # Execute
        is_eligible, reason = FSARequestEligibilityService\
            .is_eligible_for_request(test_pi)

        # Assert
        assert is_eligible is True
        assert reason == ''

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.settings')
    @pytest.mark.parametrize('status_name', [
        'Under Review',
        'Approved - Queued',
        'Approved - Processing',
        'Approved - Complete',
    ])
    def test_is_not_eligible_for_each_non_denied_status(
        self, mock_settings, test_pi, test_project, test_user, status_name
    ):
        """Test PI is not eligible for any non-denied status."""
        # Mock settings - whitelist disabled
        mock_settings.ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED = False

        # Setup - Create request with parametrized status
        from coldfront.plugins.faculty_storage_allocations.models import (
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
        is_eligible, reason = FSARequestEligibilityService\
            .is_eligible_for_request(test_pi)

        # Assert
        assert is_eligible is False
        assert 'already has an existing non-denied' in reason

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.settings')
    def test_whitelist_enabled_with_matching_email(
        self, mock_settings, test_pi
    ):
        """Test PI is eligible when whitelist is enabled and email matches."""
        from allauth.account.models import EmailAddress

        # Mock settings - whitelist enabled
        mock_settings.ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED = True
        mock_settings.ELIGIBLE_PI_EMAIL_WHITELIST = ['pi@berkeley.edu']

        # Setup - Create email address for PI
        EmailAddress.objects.create(
            user=test_pi,
            email='pi@berkeley.edu',
            verified=True,
            primary=True
        )

        # Execute
        is_eligible, reason = FSARequestEligibilityService\
            .is_eligible_for_request(test_pi)

        # Assert
        assert is_eligible is True
        assert reason == ''

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.settings')
    def test_whitelist_enabled_with_non_matching_email(
        self, mock_settings, test_pi
    ):
        """Test PI is not eligible when whitelist is enabled and email
        doesn't match."""
        from allauth.account.models import EmailAddress

        # Mock settings - whitelist enabled
        mock_settings.ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED = True
        mock_settings.ELIGIBLE_PI_EMAIL_WHITELIST = ['other@berkeley.edu']

        # Setup - Create email address for PI that's NOT on whitelist
        EmailAddress.objects.create(
            user=test_pi,
            email='pi@berkeley.edu',
            verified=True,
            primary=True
        )

        # Execute
        is_eligible, reason = FSARequestEligibilityService\
            .is_eligible_for_request(test_pi)

        # Assert
        assert is_eligible is False
        assert 'not on the whitelist' in reason

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.settings')
    def test_whitelist_enabled_with_multiple_emails_one_matches(
        self, mock_settings, test_pi
    ):
        """Test PI is eligible when they have multiple emails and one
        matches whitelist."""
        from allauth.account.models import EmailAddress

        # Mock settings - whitelist enabled
        mock_settings.ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED = True
        mock_settings.ELIGIBLE_PI_EMAIL_WHITELIST = ['pi@berkeley.edu']

        # Setup - Create multiple email addresses, one matches
        EmailAddress.objects.create(
            user=test_pi,
            email='pi@gmail.com',
            verified=True,
            primary=True
        )
        EmailAddress.objects.create(
            user=test_pi,
            email='pi@berkeley.edu',  # This one matches
            verified=True,
            primary=False
        )
        EmailAddress.objects.create(
            user=test_pi,
            email='pi@lbl.gov',
            verified=True,
            primary=False
        )

        # Execute
        is_eligible, reason = FSARequestEligibilityService\
            .is_eligible_for_request(test_pi)

        # Assert
        assert is_eligible is True
        assert reason == ''

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'eligibility_service.settings')
    def test_whitelist_prevents_check_even_with_no_existing_requests(
        self, mock_settings, test_pi
    ):
        """Test that whitelist rejection happens even if PI has no
        existing requests."""
        from allauth.account.models import EmailAddress

        # Mock settings - whitelist enabled
        mock_settings.ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED = True
        mock_settings.ELIGIBLE_PI_EMAIL_WHITELIST = ['other@berkeley.edu']

        # Setup - Create email NOT on whitelist
        EmailAddress.objects.create(
            user=test_pi,
            email='pi@berkeley.edu',
            verified=True,
            primary=True
        )

        # Execute - PI has no existing requests but should still fail
        is_eligible, reason = FSARequestEligibilityService\
            .is_eligible_for_request(test_pi)

        # Assert
        assert is_eligible is False
        assert 'whitelist' in reason
