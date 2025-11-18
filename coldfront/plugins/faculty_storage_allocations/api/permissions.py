"""Permission classes for faculty_storage_allocations API views."""

from rest_framework.permissions import IsAuthenticated


class IsSuperuserOrHasManagePermission(IsAuthenticated):
    """
    Allows access to superusers or users with the 'can_manage_fsa_requests'
    permission.

    This permission is used for FSA request management API endpoints that
    perform write operations (claim, complete, etc.). Since these operations
    don't have a meaningful "read-only" mode, both superusers and users with
    the manage permission get full access.

    Disallows unauthenticated users and users without the required permission.
    """

    def has_permission(self, request, view):
        """Check if user has permission to access FSA request management."""
        is_authenticated = super().has_permission(request, view)
        if not is_authenticated:
            return False

        user = request.user
        if not user:
            return False

        # Superusers have full access
        if user.is_superuser:
            return True

        # Users with the manage permission have full access
        if user.has_perm('faculty_storage_allocations.can_manage_fsa_requests'):
            return True

        return False


__all__ = ['IsSuperuserOrHasManagePermission']
