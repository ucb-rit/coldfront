from coldfront.core.utils.common import utc_now_offset_aware

from coldfront.plugins.cluster_storage.models import FacultyStorageAllocationRequest
from coldfront.plugins.cluster_storage.models import FacultyStorageAllocationRequestStatusChoice
from coldfront.plugins.cluster_storage.services import DirectoryService
from coldfront.plugins.cluster_storage.services import StorageRequestNotificationService

import logging

logger = logging.getLogger(__name__)

class FacultyStorageAllocationRequestService:

    @staticmethod
    def create_request(data, email_strategy=None):
        # Directly create the request, relying on Django's built-in validation
        data['status'] = \
            FacultyStorageAllocationRequestStatusChoice.objects.get(
                name=data['status'])
        faculty_scratch_storage_request = \
            FacultyStorageAllocationRequest.objects.create(**data)

        StorageRequestNotificationService.send_request_created_email(
            faculty_scratch_storage_request, email_strategy=email_strategy)

        return faculty_scratch_storage_request

    @staticmethod
    def approve_request(request, email_strategy=None):
        status = FacultyStorageAllocationRequestStatusChoice.objects.get(
            name='Approved - Processing')
        request.status = status
        request.approval_time = utc_now_offset_aware()
        request.save()

    @staticmethod
    def complete_request(request, directory_name, email_strategy=None):
        # Check if already completed to avoid double-processing
        if request.status.name == 'Approved - Complete':
            logger.warning(
                f'Request {request.pk} is already completed, skipping')
            return

        # If approved amount wasn't explicitly set, set it to requested amount
        if request.approved_amount_gb is None:
            request.approved_amount_gb = request.requested_amount_gb
            logger.info(
                f'Request {request.pk}: approved_amount_gb not set, '
                f'defaulting to requested_amount_gb ({request.requested_amount_gb} GB)')

        status = FacultyStorageAllocationRequestStatusChoice.objects.get(
            name='Approved - Complete')
        request.status = status
        request.completion_time = utc_now_offset_aware()
        request.save()

        directory_service = DirectoryService(request.project, directory_name)

        # Use the approved amount (now guaranteed to be set)
        amount_gb = request.approved_amount_gb

        if directory_service.directory_exists():
            # Directory already exists, add to existing quota
            directory_service.add_to_directory_quota(amount_gb)
            logger.info(
                f'Added {amount_gb} GB to existing directory '
                f'for project {request.project.name}')
        else:
            # New directory, create it and set initial quota
            directory_service.create_directory()
            directory_service.set_directory_quota(amount_gb)
            logger.info(
                f'Created new directory with {amount_gb} GB '
                f'for project {request.project.name}')

        # Add all active project users to the allocation
        FacultyStorageAllocationRequestService._add_project_users_to_allocation(
            request)

        StorageRequestNotificationService.send_completion_email(
            request, email_strategy=email_strategy)

    @staticmethod
    def _add_project_users_to_allocation(request):
        """Add all active ProjectUsers to the faculty storage allocation.

        This is called when the request is completed to ensure all existing
        project members have access. Future members will be added automatically
        via the project_user_added signal handler.
        """
        try:
            # Use the DirectoryService to add all project users
            directory_name = request.state['setup']['directory_name']
            directory_service = DirectoryService(
                request.project, directory_name)
            allocation_users = \
                directory_service.add_project_users_to_directory()
            logger.info(
                f'Added {len(allocation_users)} users to faculty storage '
                f'allocation for project {request.project.name}')
        except Exception as e:
            logger.exception(
                f'Error adding users to faculty storage allocation for '
                f'project {request.project.name}: {e}')
            raise

    @staticmethod
    def deny_request(request, email_strategy=None):
        status = FacultyStorageAllocationRequestStatusChoice.objects.get(
            name='Denied')
        request.status = status
        request.save()

        StorageRequestNotificationService.send_denial_email(
            request, email_strategy=email_strategy)

    @staticmethod
    def undeny_request(request):
        """Undeny a request by resetting review statuses to Pending.

        If a review step was denied, reset it to Pending. Also clear any
        'other' denial reason. Then update the overall request status to
        Under Review.
        """
        state = request.state

        # Reset eligibility to Pending if it was denied
        eligibility = state['eligibility']
        if eligibility['status'] == 'Denied':
            eligibility['status'] = 'Pending'

        # Reset intake_consistency to Pending if it was denied
        intake_consistency = state['intake_consistency']
        if intake_consistency['status'] == 'Denied':
            intake_consistency['status'] = 'Pending'

        # Clear any 'other' denial reason if it exists
        other = state['other']
        if other['timestamp']:
            state['other']['justification'] = ''
            state['other']['timestamp'] = ''

        request.state = state

        # Update overall status to Under Review
        status = FacultyStorageAllocationRequestStatusChoice.objects.get(
            name='Under Review')
        request.status = status
        request.save()

        return request
