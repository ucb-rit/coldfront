from coldfront.plugins.cluster_storage.models import FacultyStorageAllocationRequest
from coldfront.plugins.cluster_storage.models import FacultyStorageAllocationRequestStatusChoice
from coldfront.plugins.cluster_storage.services import DirectoryService
from coldfront.plugins.cluster_storage.services import StorageRequestNotificationService


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


        # TODO: Need to add if the directory already exists.


        directory_service.create_directory()
        directory_service.set_directory_quota(request.requested_amount_gb)

        StorageRequestNotificationService.send_completion_email(
            request, email_strategy=email_strategy)

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
