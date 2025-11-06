from allauth.account.models import EmailAddress

from coldfront.plugins.faculty_storage_allocations.conf import settings
from coldfront.plugins.faculty_storage_allocations.models import FacultyStorageAllocationRequest


class FSARequestEligibilityService:
    """Handle eligibility checks for FSA requests."""

    @staticmethod
    def is_eligible_for_request(pi_user):
        """
        Determine if a PI is eligible to submit a new FSA request.

        Args:
            pi_user: The PI user to check

        Returns:
            tuple: (is_eligible: bool, reason_if_not: str)
        """
        # If the whitelist is enabled, check that the PI is on it.
        if settings.ELIGIBLE_PI_EMAIL_WHITELIST_ENABLED:
            user_emails = EmailAddress.objects.filter(
                user=pi_user
            ).values_list('email', flat=True)
            email_whitelist = set(
                [e.lower() for e in settings.ELIGIBLE_PI_EMAIL_WHITELIST])

            if not any(email in email_whitelist for email in user_emails):
                return False, 'PI is not on the whitelist of eligible PIs.'

        # Check if the PI has any existing non-denied requests.
        has_non_denied_request = FacultyStorageAllocationRequest.objects.filter(
            pi=pi_user
        ).exclude(status__name='Denied').exists()

        if has_non_denied_request:
            return False, 'PI already has an existing non-denied FSA request.'

        return True, ''
