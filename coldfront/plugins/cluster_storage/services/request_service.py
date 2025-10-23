from django.db import transaction

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
            name='Approved - Queued')
        request.status = status
        request.approval_time = utc_now_offset_aware()
        request.save()

    @staticmethod
    def claim_next_request():
        """Atomically claim the next queued request for processing.

        This transitions the oldest request from 'Approved - Queued' to
        'Approved - Processing', claiming it for the agent to work on.

        Also handles automatic recovery of requests that were claimed but never
        completed (e.g., due to agent crash). Requests stuck in 'Approved - Processing'
        for more than 30 minutes are automatically reclaimed.

        Uses select_for_update(skip_locked=True) to prevent race conditions
        when multiple agents are running.

        Returns:
            FacultyStorageAllocationRequest: The claimed request, or None if
                no requests are available.
        """
        from django.utils import timezone
        from datetime import timedelta

        # Timeout for stale processing requests (configurable)
        PROCESSING_TIMEOUT_MINUTES = 30

        with transaction.atomic():
            queued_status = FacultyStorageAllocationRequestStatusChoice.objects.get(
                name='Approved - Queued')
            processing_status = FacultyStorageAllocationRequestStatusChoice.objects.get(
                name='Approved - Processing')

            # First priority: Find the oldest queued request
            storage_request = (
                FacultyStorageAllocationRequest.objects
                .filter(status=queued_status)
                .select_for_update(skip_locked=True)
                .order_by('approval_time', 'request_time')
                .first()
            )

            # Second priority: If no queued requests, look for stale processing requests
            if not storage_request:
                timeout_threshold = timezone.now() - timedelta(minutes=PROCESSING_TIMEOUT_MINUTES)

                storage_request = (
                    FacultyStorageAllocationRequest.objects
                    .filter(
                        status=processing_status,
                        modified__lt=timeout_threshold  # Stuck for too long
                    )
                    .select_for_update(skip_locked=True)
                    .order_by('modified')
                    .first()
                )

                if storage_request:
                    logger.warning(
                        f'Reclaiming stale request {storage_request.id} that has been '
                        f'in Processing state since {storage_request.modified} '
                        f'(project: {storage_request.project.name})'
                    )

            if storage_request:
                # Claim or reclaim this request by ensuring it's in Processing state
                storage_request.status = processing_status
                storage_request.save()

                logger.info(
                    f'Request {storage_request.id} claimed for processing '
                    f'(project: {storage_request.project.name})'
                )

            return storage_request

    @staticmethod
    def update_eligibility_state(request, status, justification):
        """Update the eligibility review state.

        This encapsulates the state structure for eligibility checks.

        Args:
            request: The FacultyStorageAllocationRequest to update
            status: The new status ('Pending', 'Approved', or 'Denied')
            justification: The justification text for the decision
        """
        state = request.state
        state['eligibility']['status'] = status
        state['eligibility']['justification'] = justification
        state['eligibility']['timestamp'] = utc_now_offset_aware().isoformat()
        request.state = state
        request.save()

        logger.info(
            f'Request {request.pk}: eligibility state updated to {status}'
        )

    @staticmethod
    def update_intake_consistency_state(request, status, justification):
        """Update the intake consistency review state.

        This encapsulates the state structure for intake consistency checks.

        Args:
            request: The FacultyStorageAllocationRequest to update
            status: The new status ('Pending', 'Approved', or 'Denied')
            justification: The justification text for the decision
        """
        state = request.state
        state['intake_consistency']['status'] = status
        state['intake_consistency']['justification'] = justification
        state['intake_consistency']['timestamp'] = utc_now_offset_aware().isoformat()
        request.state = state
        request.save()

        logger.info(
            f'Request {request.pk}: intake_consistency state updated to {status}'
        )

    @staticmethod
    def update_setup_state(request, directory_name=None, status='Complete'):
        """Update the setup state.

        This encapsulates the state structure and can be called from both
        the manual UI workflow and the automated API workflow.

        Args:
            request: The FacultyStorageAllocationRequest to update
            directory_name: The name of the directory (required if status='Complete')
            status: The setup status ('Pending' or 'Complete')
        """
        state = request.state
        state['setup']['status'] = status
        if directory_name is not None:
            state['setup']['directory_name'] = directory_name
        state['setup']['timestamp'] = utc_now_offset_aware().isoformat()
        request.state = state
        request.save()

        if directory_name:
            logger.info(
                f'Request {request.pk}: setup state updated to {status} '
                f'with directory_name={directory_name}'
            )
        else:
            logger.info(
                f'Request {request.pk}: setup state updated to {status}'
            )

    @staticmethod
    def update_other_state(request, justification):
        """Update the 'other' denial reason state.

        This is used when denying a request for a reason not covered by
        the standard review steps.

        Args:
            request: The FacultyStorageAllocationRequest to update
            justification: The justification text for the denial
        """
        state = request.state
        state['other']['justification'] = justification
        state['other']['timestamp'] = utc_now_offset_aware().isoformat()
        request.state = state
        request.save()

        logger.info(
            f'Request {request.pk}: other denial reason set'
        )

    @staticmethod
    def complete_request(request, directory_name, email_strategy=None):
        # Check if already completed to avoid double-processing
        if request.status.name == 'Approved - Complete':
            logger.warning(
                f'Request {request.pk} is already completed, skipping')
            return

        # Update setup state (idempotent - safe to call multiple times)
        FacultyStorageAllocationRequestService.update_setup_state(
            request, directory_name)

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
            FacultyStorageAllocationRequestService.update_eligibility_state(
                request, 'Pending', eligibility.get('justification', ''))

        # Reset intake_consistency to Pending if it was denied
        intake_consistency = state['intake_consistency']
        if intake_consistency['status'] == 'Denied':
            FacultyStorageAllocationRequestService.update_intake_consistency_state(
                request, 'Pending', intake_consistency.get('justification', ''))

        # Clear any 'other' denial reason if it exists
        other = state['other']
        if other.get('timestamp'):
            FacultyStorageAllocationRequestService.update_other_state(
                request, '')

        # Update overall status to Under Review
        status = FacultyStorageAllocationRequestStatusChoice.objects.get(
            name='Under Review')
        request.status = status
        request.save()

        return request
