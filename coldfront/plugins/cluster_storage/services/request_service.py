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
        request.save()

        StorageRequestNotificationService.send_approval_email(
            request, email_strategy=email_strategy)

    @staticmethod
    def complete_request(request, directory_name, email_strategy=None):
        status = FacultyStorageAllocationRequestStatusChoice.objects.get(
            name='Approved - Complete')
        request.status = status
        request.save()

        directory_service = DirectoryService(request.project, directory_name)

        if directory_service.directory_exists():
            # Directory already exists, add to existing quota
            directory_service.add_to_directory_quota(
                request.requested_amount_gb)
            logger.info(
                f'Added {request.requested_amount_gb} GB to existing directory '
                f'for project {request.project.name}')
        else:
            # New directory, create it and set initial quota
            directory_service.create_directory()
            directory_service.set_directory_quota(request.requested_amount_gb)
            logger.info(
                f'Created new directory with {request.requested_amount_gb} GB '
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
    def deny_request(request, justification, email_strategy=None):
        status = FacultyStorageAllocationRequestStatusChoice.objects.get(
            name='Denied')
        request.status = status
        request.save()

        StorageRequestNotificationService.send_denial_email(
            request, justification, email_strategy=email_strategy)

    @staticmethod
    def undeny_request(request):
        status = FacultyStorageAllocationRequestStatusChoice.objects.get(
            name='Under Review')
        request.status = status
        request.save()

        return request
