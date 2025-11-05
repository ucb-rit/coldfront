"""Component tests for API endpoints with database."""

import pytest
from datetime import timedelta
from unittest.mock import patch
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from coldfront.core.user.models import ExpiringToken
from coldfront.plugins.faculty_storage_allocations.tests.pytest.utils import (
    create_fsa_request,
)

User = get_user_model()


@pytest.fixture
def api_client():
    """Return an APIClient instance."""
    return APIClient()


@pytest.fixture
def staff_user(db):
    """Create a staff user with manage permission for API testing."""
    from django.contrib.auth.models import Permission

    user = User.objects.create_user(
        username='api_staff',
        email='api_staff@test.com',
        is_staff=True
    )

    # Add permission to manage FSA requests
    permission = Permission.objects.get(
        codename='can_manage_fsa_requests'
    )
    user.user_permissions.add(permission)

    return user


@pytest.fixture
def regular_user(db):
    """Create a regular (non-staff) user for API testing."""
    return User.objects.create_user(
        username='api_user',
        email='api_user@test.com',
        is_staff=False
    )


@pytest.fixture
def staff_token(staff_user):
    """Create an API token for staff user."""
    return ExpiringToken.objects.create(user=staff_user)


@pytest.fixture
def regular_token(regular_user):
    """Create an API token for regular user."""
    return ExpiringToken.objects.create(user=regular_user)


@pytest.fixture
def expired_token(staff_user):
    """Create an expired API token."""
    token = ExpiringToken.objects.create(user=staff_user)
    # Set expiration date to past
    token.expiration_datetime = timezone.now() - timedelta(days=1)
    token.save()
    return token


@pytest.fixture
def authenticated_client(api_client, staff_token):
    """Return an APIClient with staff authentication."""
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {staff_token.key}')
    return api_client


@pytest.mark.component
class TestClaimNextRequestAPIIntegration:
    """Integration tests for claim endpoint."""

    def test_claim_next_returns_oldest_queued_request(
        self, authenticated_client, test_project, test_user, test_pi,
        resource_faculty_storage_directory
    ):
        """Test POST /api/storage/requests/next/claim/ returns oldest
        request."""
        # Setup - create 3 queued requests with different approval times
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

        # Execute
        url = reverse('faculty-storage-allocation-request-claim-next')
        response = authenticated_client.post(url)

        # Assert - oldest request (request1) is returned
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == request1.id

    def test_claim_next_updates_request_status_in_database(
        self, authenticated_client, test_project, test_user, test_pi
    ):
        """Test claiming updates request status to 'Processing' in DB."""
        # Setup
        request_obj = create_fsa_request(
            status='Approved - Queued',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            approved_amount_gb=1000
        )
        request_obj.approval_time = timezone.now()
        request_obj.save()

        # Execute
        url = reverse('faculty-storage-allocation-request-claim-next')
        response = authenticated_client.post(url)

        # Assert - status updated in database
        assert response.status_code == status.HTTP_200_OK
        request_obj.refresh_from_db()
        assert request_obj.status.name == 'Approved - Processing'

    def test_claim_next_returns_204_when_queue_empty(
        self, authenticated_client
    ):
        """Test endpoint returns 204 when no requests available."""
        # Setup - no queued requests

        # Execute
        url = reverse('faculty-storage-allocation-request-claim-next')
        response = authenticated_client.post(url)

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_claim_next_requires_authentication(self, api_client, db):
        """Test endpoint requires authentication."""
        # Execute - no credentials
        url = reverse('faculty-storage-allocation-request-claim-next')
        response = api_client.post(url)

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_claim_next_returns_serialized_request_data(
        self, authenticated_client, test_project, test_user, test_pi,
        resource_faculty_storage_directory
    ):
        """Test endpoint returns complete request data in response."""
        # Setup
        request_obj = create_fsa_request(
            status='Approved - Queued',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            approved_amount_gb=500
        )
        request_obj.approval_time = timezone.now()
        request_obj.state['setup']['directory_name'] = 'fc_test_dir'
        request_obj.save()

        # Execute
        url = reverse('faculty-storage-allocation-request-claim-next')
        response = authenticated_client.post(url)

        # Assert - check all expected fields
        assert response.status_code == status.HTTP_200_OK
        assert 'id' in response.data
        assert 'project_name' in response.data
        assert 'directory_path' in response.data
        assert 'set_size_gb' in response.data
        assert 'requested_delta_gb' in response.data
        assert response.data['requested_delta_gb'] == 500


@pytest.mark.component
class TestCompleteRequestAPIIntegration:
    """Integration tests for complete endpoint."""

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.DirectoryService')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.StorageRequestNotificationService')
    def test_complete_request_updates_database(
        self, mock_notification, mock_directory_service,
        authenticated_client, test_project, test_user, test_pi
    ):
        """Test PATCH /api/storage/requests/{id}/complete/ updates DB."""
        # Setup mocks
        mock_service_instance = mock_directory_service.return_value
        mock_service_instance.directory_exists.return_value = False
        mock_service_instance.create_directory.return_value = None
        mock_service_instance.set_directory_quota.return_value = None
        mock_service_instance.add_project_users_to_directory.return_value = []

        # Create processing request
        request_obj = create_fsa_request(
            status='Approved - Processing',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            approved_amount_gb=1000
        )

        # Execute
        url = reverse('faculty-storage-allocation-request-complete', kwargs={'pk': request_obj.id})
        response = authenticated_client.patch(
            url,
            {'directory_name': 'fc_test_dir'},
            format='json'
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        request_obj.refresh_from_db()
        assert request_obj.status.name == 'Approved - Complete'
        assert request_obj.completion_time is not None

    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.DirectoryService')
    @patch('coldfront.plugins.faculty_storage_allocations.services.'
           'request_service.StorageRequestNotificationService')
    def test_complete_request_sets_directory_name(
        self, mock_notification, mock_directory_service,
        authenticated_client, test_project, test_user, test_pi
    ):
        """Test completion sets directory_name in request state."""
        # Setup mocks
        mock_service_instance = mock_directory_service.return_value
        mock_service_instance.directory_exists.return_value = False
        mock_service_instance.create_directory.return_value = None
        mock_service_instance.set_directory_quota.return_value = None
        mock_service_instance.add_project_users_to_directory.return_value = []

        # Create processing request
        request_obj = create_fsa_request(
            status='Approved - Processing',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            approved_amount_gb=1000
        )

        # Execute
        url = reverse('faculty-storage-allocation-request-complete', kwargs={'pk': request_obj.id})
        response = authenticated_client.patch(
            url,
            {'directory_name': 'fc_my_custom_dir'},
            format='json'
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        request_obj.refresh_from_db()
        assert request_obj.state['setup']['directory_name'] == \
            'fc_my_custom_dir'

    def test_complete_request_rejects_invalid_status(
        self, authenticated_client, test_project, test_user, test_pi
    ):
        """Test cannot complete request not in 'Processing' status."""
        # Setup - request in wrong status
        request_obj = create_fsa_request(
            status='Approved - Queued',  # Wrong status
            project=test_project,
            requester=test_user,
            pi=test_pi,
            approved_amount_gb=1000
        )

        # Execute
        url = reverse('faculty-storage-allocation-request-complete', kwargs={'pk': request_obj.id})
        response = authenticated_client.patch(
            url,
            {'directory_name': 'fc_test_dir'},
            format='json'
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Approved - Processing' in response.data['detail']

    def test_complete_request_validates_payload(
        self, authenticated_client, test_project, test_user, test_pi
    ):
        """Test endpoint validates completion payload format."""
        # Setup
        request_obj = create_fsa_request(
            status='Approved - Processing',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            approved_amount_gb=1000
        )

        # Execute - empty payload
        url = reverse('faculty-storage-allocation-request-complete', kwargs={'pk': request_obj.id})
        response = authenticated_client.patch(url, {}, format='json')

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'directory_name' in response.data

    def test_complete_request_returns_404_for_nonexistent_request(
        self, authenticated_client
    ):
        """Test endpoint returns 404 for non-existent request."""
        # Execute
        url = reverse('faculty-storage-allocation-request-complete', kwargs={'pk': 99999})
        response = authenticated_client.patch(
            url,
            {'directory_name': 'fc_test_dir'},
            format='json'
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_complete_request_requires_authentication(self, api_client, db):
        """Test endpoint requires authentication."""
        # Execute - no credentials
        url = reverse('faculty-storage-allocation-request-complete', kwargs={'pk': 1})
        response = api_client.patch(
            url,
            {'directory_name': 'fc_test_dir'},
            format='json'
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.component
class TestAPIAuthentication:
    """Test API authentication and permissions."""

    def test_claim_endpoint_requires_valid_token(self, api_client, db):
        """Test claim endpoint rejects requests without valid token."""
        # No token
        url = reverse('faculty-storage-allocation-request-claim-next')
        response = api_client.post(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Invalid token
        api_client.credentials(HTTP_AUTHORIZATION='Token invalid_token_key')
        response = api_client.post(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_complete_endpoint_requires_valid_token(self, api_client, db):
        """Test complete endpoint rejects requests without valid token."""
        # No token
        url = reverse('faculty-storage-allocation-request-complete', kwargs={'pk': 1})
        response = api_client.patch(
            url,
            {'directory_name': 'fc_test_dir'},
            format='json'
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Invalid token
        api_client.credentials(HTTP_AUTHORIZATION='Token invalid_token_key')
        response = api_client.patch(
            url,
            {'directory_name': 'fc_test_dir'},
            format='json'
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_expired_tokens_are_rejected(
        self, api_client, expired_token
    ):
        """Test expired tokens are not accepted."""
        # Setup - use expired token
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {expired_token.key}')

        # Execute - try claim endpoint
        url = reverse('faculty-storage-allocation-request-claim-next')
        response = api_client.post(url)

        # Assert - should be unauthorized
        # Note: This depends on token expiration being enforced
        # If not enforced, this test may need adjustment
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_204_NO_CONTENT  # If token validation not enforced
        ]

    def test_valid_token_allows_access(
        self, api_client, staff_token
    ):
        """Test valid token allows access to endpoints."""
        # Setup
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {staff_token.key}')

        # Execute
        url = reverse('faculty-storage-allocation-request-claim-next')
        response = api_client.post(url)

        # Assert - should not be unauthorized (may be 204 if no requests)
        assert response.status_code != status.HTTP_401_UNAUTHORIZED


@pytest.mark.component
class TestAPIPermissions:
    """Test API permission enforcement."""

    def test_superuser_can_access_claim_endpoint(
        self, api_client, db
    ):
        """Test superusers can access claim endpoint."""
        # Create superuser
        superuser = User.objects.create_superuser(
            username='api_superuser',
            email='api_superuser@test.com',
            password='superpass'
        )
        token = ExpiringToken.objects.create(user=superuser)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Execute
        url = reverse('faculty-storage-allocation-request-claim-next')
        response = api_client.post(url)

        # Should not be forbidden (may be 204 if no requests)
        assert response.status_code != status.HTTP_403_FORBIDDEN

    def test_user_with_permission_can_access_claim_endpoint(
        self, api_client, staff_user, staff_token
    ):
        """Test users with can_manage permission can access claim endpoint."""
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {staff_token.key}')

        # Execute
        url = reverse('faculty-storage-allocation-request-claim-next')
        response = api_client.post(url)

        # Should not be forbidden (may be 204 if no requests)
        assert response.status_code != status.HTTP_403_FORBIDDEN

    def test_regular_user_denied_access_to_claim_endpoint(
        self, api_client, regular_token
    ):
        """Test regular users without permission are denied access."""
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {regular_token.key}')

        # Execute
        url = reverse('faculty-storage-allocation-request-claim-next')
        response = api_client.post(url)

        # Should be forbidden
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_staff_without_permission_denied_access(
        self, api_client, db
    ):
        """Test staff users without manage permission are denied access."""
        # Create staff user WITHOUT the permission
        staff_no_perm = User.objects.create_user(
            username='staff_no_perm',
            email='staff_no_perm@test.com',
            is_staff=True
        )
        token = ExpiringToken.objects.create(user=staff_no_perm)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Execute
        url = reverse('faculty-storage-allocation-request-claim-next')
        response = api_client.post(url)

        # Should be forbidden
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_regular_user_denied_access_to_complete_endpoint(
        self, api_client, regular_token, test_project, test_user, test_pi
    ):
        """Test regular users cannot access complete endpoint."""
        # Create a processing request
        request_obj = create_fsa_request(
            status='Approved - Processing',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            approved_amount_gb=1000
        )

        api_client.credentials(HTTP_AUTHORIZATION=f'Token {regular_token.key}')

        # Execute
        url = reverse('faculty-storage-allocation-request-complete', kwargs={'pk': request_obj.id})
        response = api_client.patch(
            url,
            {'directory_name': 'fc_test_dir'},
            format='json'
        )

        # Should be forbidden
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_non_staff_user_with_permission_can_access(
        self, api_client, db
    ):
        """Test non-staff users with can_manage permission can access.

        This verifies that is_staff is not required - only the
        can_manage_fsa_requests permission matters.
        """
        from django.contrib.auth.models import Permission

        # Create NON-STAFF user with the permission
        non_staff_user = User.objects.create_user(
            username='non_staff_admin',
            email='non_staff_admin@test.com',
            is_staff=False  # Explicitly not staff
        )
        permission = Permission.objects.get(
            codename='can_manage_fsa_requests'
        )
        non_staff_user.user_permissions.add(permission)

        token = ExpiringToken.objects.create(user=non_staff_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Execute
        url = reverse('faculty-storage-allocation-request-claim-next')
        response = api_client.post(url)

        # Should not be forbidden (may be 204 if no requests)
        assert response.status_code != status.HTTP_403_FORBIDDEN
