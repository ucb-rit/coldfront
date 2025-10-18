from coldfront.core.allocation.models import Allocation
from coldfront.core.resource.models import Resource
from coldfront.plugins.cluster_storage.models import FacultyStorageAllocationRequest
from coldfront.plugins.cluster_storage.models import FacultyStorageAllocationRequestStatusChoice


class StorageRequestEligibilityService:
    """Handle eligibility checks for storage requests."""

    @staticmethod
    def is_eligible_for_request(pi_user):
        """
        Determine if a PI is eligible to submit a new storage request.

        Args:
            pi_user: The PI user to check

        Returns:
            tuple: (is_eligible: bool, reason_if_not: str)
        """
        # Check if the PI has any existing non-denied requests
        has_non_denied_request = FacultyStorageAllocationRequest.objects.filter(
            pi=pi_user
        ).exclude(status__name='Denied').exists()

        if has_non_denied_request:
            return False, 'PI already has an existing non-denied storage request.'

        return True, ''
