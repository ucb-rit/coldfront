"""API views for Faculty Storage Allocations management."""
import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from coldfront.plugins.faculty_storage_allocations.models import FacultyStorageAllocationRequest
from coldfront.plugins.faculty_storage_allocations.services import FacultyStorageAllocationRequestService
from coldfront.plugins.faculty_storage_allocations.api.serializers import FSARequestNextSerializer
from coldfront.plugins.faculty_storage_allocations.api.serializers import FSARequestCompletionSerializer
from coldfront.plugins.faculty_storage_allocations.api.permissions import IsSuperuserOrHasManagePermission


logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsSuperuserOrHasManagePermission])
def claim_next_fsa_request(request):
    """Claim the next FSA request to be processed by the agent.

    This endpoint atomically:
    1. Finds the oldest request with status 'Approved - Queued'
    2. Transitions it to 'Approved - Processing' to claim it
    3. Returns the request details with set_size_gb for idempotent quota setting

    If no requests are available, returns 204 No Content.

    Returns:
        200 OK: Next request details
        204 No Content: No requests available
    """
    from django.db import transaction

    # Wrap entire operation in transaction so serialization errors rollback
    with transaction.atomic():
        # Use the service to atomically claim the next request
        fsa_request = FacultyStorageAllocationRequestService.claim_next_request()

        if not fsa_request:
            return Response(
                {'detail': 'No FSA requests available for processing.'},
                status=status.HTTP_204_NO_CONTENT
            )

        # Serialize and return the claimed request
        # If serialization fails, the transaction will rollback
        serializer = FSARequestNextSerializer(fsa_request)
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PATCH'])
@permission_classes([IsSuperuserOrHasManagePermission])
def complete_fsa_request(request, pk):
    """Mark a FSA request as complete after processing.

    This endpoint:
    1. Validates the request is in 'Approved - Processing' status
    2. Validates the provided directory_name
    3. Calls the existing complete_request service method
    4. Returns success

    Args:
        pk: The ID of the FSA request to complete

    Request Body:
        directory_name: The directory name used for the storage allocation

    Returns:
        200 OK: Request completed successfully
        400 Bad Request: Request is not in the correct status or invalid input
        404 Not Found: Request does not exist
    """
    from django.db import transaction

    try:
        fsa_request = FacultyStorageAllocationRequest.objects.get(pk=pk)
    except FacultyStorageAllocationRequest.DoesNotExist:
        return Response(
            {'detail': f'FSA request {pk} not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Validate the request is in Processing status
    if fsa_request.status.name != 'Approved - Processing':
        return Response(
            {
                'detail': (
                    f'Request {pk} is in status "{fsa_request.status.name}", '
                    f'expected "Approved - Processing". Cannot complete.'
                )
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate the request body
    serializer = FSARequestCompletionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    directory_name = serializer.validated_data['directory_name']

    try:
        # Wrap in transaction to ensure atomicity
        with transaction.atomic():
            # Call the existing service to complete the request
            # This will update setup state, database quota, and send notification emails
            FacultyStorageAllocationRequestService.complete_request(
                fsa_request,
                directory_name,
                email_strategy=None
            )

            logger.info(
                f'FSA request {pk} completed successfully for '
                f'project {fsa_request.project.name} with directory {directory_name}'
            )

        return Response(
            {'detail': f'FSA request {pk} completed successfully.'},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        logger.exception(
            f'Error completing FSA request {pk}: {e}'
        )
        return Response(
            {'detail': f'Error completing request: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
