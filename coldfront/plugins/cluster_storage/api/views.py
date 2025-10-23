"""API views for cluster storage management."""
import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from coldfront.plugins.cluster_storage.models import FacultyStorageAllocationRequest
from coldfront.plugins.cluster_storage.services import FacultyStorageAllocationRequestService
from coldfront.plugins.cluster_storage.api.serializers import StorageRequestNextSerializer
from coldfront.plugins.cluster_storage.api.serializers import StorageRequestCompletionSerializer


logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def claim_next_storage_request(request):
    """Claim the next storage request to be processed by the agent.

    This endpoint atomically:
    1. Finds the oldest request with status 'Approved - Queued'
    2. Transitions it to 'Approved - Processing' to claim it
    3. Returns the request details with set_size_gb for idempotent quota setting

    If no requests are available, returns 204 No Content.

    Returns:
        200 OK: Next request details
        204 No Content: No requests available
    """
    # Use the service to atomically claim the next request
    storage_request = FacultyStorageAllocationRequestService.claim_next_request()

    if not storage_request:
        return Response(
            {'detail': 'No storage requests available for processing.'},
            status=status.HTTP_204_NO_CONTENT
        )

    # Serialize and return the claimed request
    serializer = StorageRequestNextSerializer(storage_request)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def complete_storage_request(request, pk):
    """Mark a storage request as complete after processing.

    This endpoint:
    1. Validates the request is in 'Approved - Processing' status
    2. Validates the provided directory_name
    3. Calls the existing complete_request service method
    4. Returns success

    Args:
        pk: The ID of the storage request to complete

    Request Body:
        directory_name: The directory name used for the storage allocation

    Returns:
        200 OK: Request completed successfully
        400 Bad Request: Request is not in the correct status or invalid input
        404 Not Found: Request does not exist
    """
    try:
        storage_request = FacultyStorageAllocationRequest.objects.get(pk=pk)
    except FacultyStorageAllocationRequest.DoesNotExist:
        return Response(
            {'detail': f'Storage request {pk} not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Validate the request is in Processing status
    if storage_request.status.name != 'Approved - Processing':
        return Response(
            {
                'detail': (
                    f'Request {pk} is in status "{storage_request.status.name}", '
                    f'expected "Approved - Processing". Cannot complete.'
                )
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate the request body
    serializer = StorageRequestCompletionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    directory_name = serializer.validated_data['directory_name']

    try:
        # Call the existing service to complete the request
        # This will update setup state, database quota, and send notification emails
        FacultyStorageAllocationRequestService.complete_request(
            storage_request,
            directory_name,
            email_strategy=None
        )

        logger.info(
            f'Storage request {pk} completed successfully for '
            f'project {storage_request.project.name} with directory {directory_name}'
        )

        return Response(
            {'detail': f'Storage request {pk} completed successfully.'},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        logger.exception(
            f'Error completing storage request {pk}: {e}'
        )
        return Response(
            {'detail': f'Error completing request: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
