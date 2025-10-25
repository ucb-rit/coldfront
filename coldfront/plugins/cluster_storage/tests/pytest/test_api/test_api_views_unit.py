"""Unit tests for API view logic."""

import pytest
from unittest.mock import Mock, patch
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status

from coldfront.plugins.cluster_storage.api.views import (
    claim_next_storage_request,
    complete_storage_request,
)


@pytest.mark.unit
class TestClaimNextRequestView:
    """Unit tests for claim next request API view."""

    def test_view_requires_authentication(self):
        """Test endpoint requires authentication."""
        # Setup
        factory = APIRequestFactory()
        request = factory.post('/api/storage-requests/claim/')

        # Execute - unauthenticated request
        response = claim_next_storage_request(request)

        # Assert - should require authentication (401 Unauthorized)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch('coldfront.plugins.cluster_storage.api.views.'
           'FacultyStorageAllocationRequestService')
    def test_view_calls_service_claim_method(self, mock_service):
        """Test view delegates to RequestService.claim_next_request()."""
        # Setup
        factory = APIRequestFactory()
        request = factory.post('/api/storage-requests/claim/')

        # Authenticate request
        mock_user = Mock()
        force_authenticate(request, user=mock_user)

        # Mock service returning a request
        mock_request = Mock()
        mock_request.id = 1
        mock_request.approved_amount_gb = 1000
        mock_request.approval_time = None
        mock_request.project.name = 'fc_test'
        mock_request.status.name = 'Approved - Processing'
        mock_request.state = {'setup': {'directory_name': 'fc_test_dir'}}
        mock_service.claim_next_request.return_value = mock_request

        # Execute
        with patch('coldfront.plugins.cluster_storage.api.views.'
                   'StorageRequestNextSerializer'):
            response = claim_next_storage_request(request)

        # Assert - service method was called
        mock_service.claim_next_request.assert_called_once()
        assert response.status_code == status.HTTP_200_OK

    @patch('coldfront.plugins.cluster_storage.api.views.'
           'FacultyStorageAllocationRequestService')
    def test_view_returns_204_if_no_requests(self, mock_service):
        """Test view returns 204 when no requests available."""
        # Setup
        factory = APIRequestFactory()
        request = factory.post('/api/storage-requests/claim/')

        # Authenticate request
        mock_user = Mock()
        force_authenticate(request, user=mock_user)

        # Mock service returning None (no requests)
        mock_service.claim_next_request.return_value = None

        # Execute
        response = claim_next_storage_request(request)

        # Assert - should return 204 No Content
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert 'No storage requests available' in response.data['detail']

    @patch('coldfront.plugins.cluster_storage.api.views.'
           'FacultyStorageAllocationRequestService')
    @patch('coldfront.plugins.cluster_storage.api.views.'
           'StorageRequestNextSerializer')
    def test_view_serializes_claimed_request(
        self, mock_serializer_class, mock_service
    ):
        """Test view serializes the claimed request."""
        # Setup
        factory = APIRequestFactory()
        request = factory.post('/api/storage-requests/claim/')

        # Authenticate request
        mock_user = Mock()
        force_authenticate(request, user=mock_user)

        # Mock claimed request
        mock_request = Mock()
        mock_service.claim_next_request.return_value = mock_request

        # Mock serializer
        mock_serializer = Mock()
        mock_serializer.data = {
            'id': 1,
            'project_name': 'fc_test',
            'directory_path': '/global/scratch/projects/fc/fc_test',
            'set_size_gb': 1000,
        }
        mock_serializer_class.return_value = mock_serializer

        # Execute
        response = claim_next_storage_request(request)

        # Assert - serializer was used
        mock_serializer_class.assert_called_once_with(mock_request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == mock_serializer.data


@pytest.mark.unit
class TestCompleteRequestView:
    """Unit tests for complete request API view."""

    def test_view_requires_authentication(self):
        """Test endpoint requires authentication."""
        # Setup
        factory = APIRequestFactory()
        request = factory.patch(
            '/api/storage-requests/1/complete/',
            {'directory_name': 'fc_test_dir'}
        )

        # Execute - unauthenticated request
        response = complete_storage_request(request, pk=1)

        # Assert - should require authentication (401 Unauthorized)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch('coldfront.plugins.cluster_storage.api.views.'
           'FacultyStorageAllocationRequest')
    def test_view_returns_404_if_request_not_found(self, mock_model):
        """Test view returns 404 if request doesn't exist."""
        # Setup
        factory = APIRequestFactory()
        request = factory.patch(
            '/api/storage-requests/999/complete/',
            {'directory_name': 'fc_test_dir'},
            format='json'
        )

        # Authenticate request
        mock_user = Mock()
        force_authenticate(request, user=mock_user)

        # Mock DoesNotExist exception
        mock_model.DoesNotExist = type('DoesNotExist', (Exception,), {})
        mock_model.objects.get.side_effect = mock_model.DoesNotExist

        # Execute
        response = complete_storage_request(request, pk=999)

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'not found' in response.data['detail'].lower()

    @patch('coldfront.plugins.cluster_storage.api.views.'
           'FacultyStorageAllocationRequest')
    def test_view_validates_request_payload(self, mock_model):
        """Test view validates completion payload."""
        # Setup
        factory = APIRequestFactory()
        # Empty payload - missing directory_name
        request = factory.patch(
            '/api/storage-requests/1/complete/',
            {},
            format='json'
        )

        # Authenticate request
        mock_user = Mock()
        force_authenticate(request, user=mock_user)

        # Mock request object
        mock_storage_request = Mock()
        mock_status = Mock()
        mock_status.name = 'Approved - Processing'
        mock_storage_request.status = mock_status
        mock_model.objects.get.return_value = mock_storage_request

        # Execute
        response = complete_storage_request(request, pk=1)

        # Assert - should return 400 for invalid payload
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'directory_name' in response.data

    @patch('coldfront.plugins.cluster_storage.api.views.'
           'FacultyStorageAllocationRequestService')
    @patch('coldfront.plugins.cluster_storage.api.views.'
           'FacultyStorageAllocationRequest')
    def test_view_calls_service_complete_method(
        self, mock_model, mock_service
    ):
        """Test view delegates to RequestService.complete_request()."""
        # Setup
        factory = APIRequestFactory()
        request = factory.patch(
            '/api/storage-requests/1/complete/',
            {'directory_name': 'fc_test_dir'},
            format='json'
        )

        # Authenticate request
        mock_user = Mock()
        force_authenticate(request, user=mock_user)

        # Mock request object
        mock_storage_request = Mock()
        mock_status = Mock()
        mock_status.name = 'Approved - Processing'
        mock_storage_request.status = mock_status
        mock_storage_request.project.name = 'fc_test'
        mock_model.objects.get.return_value = mock_storage_request

        # Execute
        response = complete_storage_request(request, pk=1)

        # Assert - service method was called
        mock_service.complete_request.assert_called_once_with(
            mock_storage_request,
            'fc_test_dir',
            email_strategy=None
        )
        assert response.status_code == status.HTTP_200_OK

    @patch('coldfront.plugins.cluster_storage.api.views.'
           'FacultyStorageAllocationRequest')
    def test_view_returns_error_if_request_not_processing(self, mock_model):
        """Test view returns error if request not in 'Processing' status."""
        # Setup
        factory = APIRequestFactory()
        request = factory.patch(
            '/api/storage-requests/1/complete/',
            {'directory_name': 'fc_test_dir'},
            format='json'
        )

        # Authenticate request
        mock_user = Mock()
        force_authenticate(request, user=mock_user)

        # Mock request with wrong status
        mock_storage_request = Mock()
        mock_status = Mock()
        mock_status.name = 'Approved - Queued'  # Wrong status
        mock_storage_request.status = mock_status
        mock_model.objects.get.return_value = mock_storage_request

        # Execute
        response = complete_storage_request(request, pk=1)

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Approved - Processing' in response.data['detail']

    @patch('coldfront.plugins.cluster_storage.api.views.'
           'FacultyStorageAllocationRequestService')
    @patch('coldfront.plugins.cluster_storage.api.views.'
           'FacultyStorageAllocationRequest')
    def test_view_handles_service_errors(self, mock_model, mock_service):
        """Test view handles errors from service layer."""
        # Setup
        factory = APIRequestFactory()
        request = factory.patch(
            '/api/storage-requests/1/complete/',
            {'directory_name': 'fc_test_dir'},
            format='json'
        )

        # Authenticate request
        mock_user = Mock()
        force_authenticate(request, user=mock_user)

        # Mock request object
        mock_storage_request = Mock()
        mock_status = Mock()
        mock_status.name = 'Approved - Processing'
        mock_storage_request.status = mock_status
        mock_storage_request.project.name = 'fc_test'
        mock_model.objects.get.return_value = mock_storage_request

        # Mock service raising exception
        mock_service.complete_request.side_effect = Exception(
            'Database error'
        )

        # Execute
        response = complete_storage_request(request, pk=1)

        # Assert - should return 500
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert 'Error completing request' in response.data['detail']

    @patch('coldfront.plugins.cluster_storage.api.views.'
           'FacultyStorageAllocationRequestService')
    @patch('coldfront.plugins.cluster_storage.api.views.'
           'FacultyStorageAllocationRequest')
    def test_view_validates_empty_directory_name(
        self, mock_model, mock_service
    ):
        """Test view rejects empty directory_name."""
        # Setup
        factory = APIRequestFactory()
        request = factory.patch(
            '/api/storage-requests/1/complete/',
            {'directory_name': ''},  # Empty string
            format='json'
        )

        # Authenticate request
        mock_user = Mock()
        force_authenticate(request, user=mock_user)

        # Mock request object
        mock_storage_request = Mock()
        mock_status = Mock()
        mock_status.name = 'Approved - Processing'
        mock_storage_request.status = mock_status
        mock_model.objects.get.return_value = mock_storage_request

        # Execute
        response = complete_storage_request(request, pk=1)

        # Assert - should return 400 for validation error
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Service should not be called with invalid data
        mock_service.complete_request.assert_not_called()

    @patch('coldfront.plugins.cluster_storage.api.views.'
           'FacultyStorageAllocationRequestService')
    @patch('coldfront.plugins.cluster_storage.api.views.'
           'FacultyStorageAllocationRequest')
    def test_view_strips_whitespace_from_directory_name(
        self, mock_model, mock_service
    ):
        """Test view strips whitespace from directory_name."""
        # Setup
        factory = APIRequestFactory()
        request = factory.patch(
            '/api/storage-requests/1/complete/',
            {'directory_name': '  fc_test_dir  '},  # With whitespace
            format='json'
        )

        # Authenticate request
        mock_user = Mock()
        force_authenticate(request, user=mock_user)

        # Mock request object
        mock_storage_request = Mock()
        mock_status = Mock()
        mock_status.name = 'Approved - Processing'
        mock_storage_request.status = mock_status
        mock_storage_request.project.name = 'fc_test'
        mock_model.objects.get.return_value = mock_storage_request

        # Execute
        response = complete_storage_request(request, pk=1)

        # Assert - should call service with stripped value
        mock_service.complete_request.assert_called_once_with(
            mock_storage_request,
            'fc_test_dir',  # Stripped
            email_strategy=None
        )
        assert response.status_code == status.HTTP_200_OK
