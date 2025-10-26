"""Permission classes for cluster_storage API views."""

from rest_framework.permissions import IsAuthenticated


class IsSuperuserOrHasManagePermission(IsAuthenticated):
    """
    Allows access to superusers or users with the 'can_manage_storage_requests'
    permission.

    This permission is used for storage request management API endpoints that
    perform write operations (claim, complete, etc.). Since these operations
    don't have a meaningful "read-only" mode, both superusers and users with
    the manage permission get full access.

    Disallows unauthenticated users and users without the required permission.
    """

    def has_permission(self, request, view):
        """Check if user has permission to access storage request management."""
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
        if user.has_perm('cluster_storage.can_manage_storage_requests'):
            return True

        return False


__all__ = ['IsSuperuserOrHasManagePermission']
