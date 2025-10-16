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

    @staticmethod
    def can_request_amount(amount_gb, min_gb=1000, max_gb=5000):
        """
        Check if the requested amount is within allowed limits.

        Args:
            amount_gb: The amount requested in GB
            min_gb: Minimum allowed amount (default: 1000 GB = 1 TB)
            max_gb: Maximum allowed amount (default: 5000 GB = 5 TB)

        Returns:
            tuple: (is_valid: bool, reason_if_not: str)
        """
        if amount_gb < min_gb:
            return False, f'Requested amount must be at least {min_gb} GB.'

        if amount_gb > max_gb:
            return False, f'Requested amount cannot exceed {max_gb} GB.'

        return True, ''
