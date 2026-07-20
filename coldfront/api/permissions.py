from rest_framework.permissions import SAFE_METHODS, IsAuthenticated


class IsAdminUserOrReadOnly(IsAuthenticated):
    """
    Allows access only to admin users, or is a read-only request.

    Disallows unauthenticated users.
    """

    def has_permission(self, request, view):
        is_authenticated = super().has_permission(request, view)
        if not is_authenticated:
            return False
        return bool(
            request.method in SAFE_METHODS
            or (request.user
            and request.user.is_staff)
            or request.user.is_superuser
        )


def IsSuperuserOrHasPerm(perm_codename):
    """
    Return a permission class that allows superusers or users with the
    given Django permission codename. Unauthenticated users and staff
    without the explicit permission are denied.

    Usage::

        permission_classes=[IsSuperuserOrHasPerm('app.codename')]
    """

    class Permission(IsAuthenticated):
        def has_permission(self, request, view):
            if not super().has_permission(request, view):
                return False
            return request.user.is_superuser or request.user.has_perm(perm_codename)

    Permission.__name__ = f"IsSuperuserOrHasPerm<{perm_codename}>"
    return Permission


class IsSuperuserOrStaff(IsAuthenticated):
    """
    Allows write access to superusers, read access to staff, and no
    access to other users.

    Disallows unauthenticated users.
    """

    def has_permission(self, request, view):
        is_authenticated = super().has_permission(request, view)
        if not is_authenticated:
            return False
        user = request.user
        if not user:
            return False
        if user.is_superuser:
            return True
        elif user.is_staff:
            return request.method in SAFE_METHODS
        return False
