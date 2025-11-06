"""Unit tests for API permission classes."""

import pytest
from unittest.mock import Mock

from coldfront.plugins.faculty_storage_allocations.api.permissions import (
    IsSuperuserOrHasManagePermission,
)


@pytest.mark.unit
class TestIsSuperuserOrHasManagePermission:
    """Unit tests for IsSuperuserOrHasManagePermission."""

    def test_allows_superuser(self):
        """Test superusers are allowed access."""
        permission = IsSuperuserOrHasManagePermission()

        # Mock request with superuser
        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = True
        request.user.is_superuser = True

        # Mock view
        view = Mock()

        assert permission.has_permission(request, view) is True

    def test_allows_user_with_manage_permission(self):
        """Test users with can_manage_fsa_requests permission are allowed."""
        permission = IsSuperuserOrHasManagePermission()

        # Mock request with user who has the permission
        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = True
        request.user.is_superuser = False
        request.user.has_perm.return_value = True

        view = Mock()

        result = permission.has_permission(request, view)

        # Check that has_perm was called with correct permission
        request.user.has_perm.assert_called_once_with(
            'faculty_storage_allocations.can_manage_fsa_requests'
        )
        assert result is True

    def test_denies_user_without_manage_permission(self):
        """Test users without manage permission are denied."""
        permission = IsSuperuserOrHasManagePermission()

        # Mock request with user who lacks the permission
        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = True
        request.user.is_superuser = False
        request.user.has_perm.return_value = False

        view = Mock()

        assert permission.has_permission(request, view) is False

    def test_denies_unauthenticated_user(self):
        """Test unauthenticated users are denied."""
        permission = IsSuperuserOrHasManagePermission()

        # Mock request with unauthenticated user
        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = False

        view = Mock()

        assert permission.has_permission(request, view) is False

    def test_denies_staff_without_permission(self):
        """Test staff users without manage permission are denied.

        Being staff is not sufficient - users need the specific
        can_manage_fsa_requests permission.
        """
        permission = IsSuperuserOrHasManagePermission()

        # Mock request with staff user who lacks the permission
        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = True
        request.user.is_superuser = False
        request.user.is_staff = True
        request.user.has_perm.return_value = False

        view = Mock()

        assert permission.has_permission(request, view) is False

    def test_allows_staff_with_permission(self):
        """Test staff users with manage permission are allowed."""
        permission = IsSuperuserOrHasManagePermission()

        # Mock request with staff user who has the permission
        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = True
        request.user.is_superuser = False
        request.user.is_staff = True
        request.user.has_perm.return_value = True

        view = Mock()

        assert permission.has_permission(request, view) is True

    def test_allows_non_staff_with_permission(self):
        """Test non-staff users with manage permission are allowed.

        This verifies that is_staff is not required - only the
        can_manage_fsa_requests permission matters.
        """
        permission = IsSuperuserOrHasManagePermission()

        # Mock request with NON-STAFF user who has the permission
        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = True
        request.user.is_superuser = False
        request.user.is_staff = False  # Explicitly not staff
        request.user.has_perm.return_value = True

        view = Mock()

        result = permission.has_permission(request, view)

        # Should still be allowed (permission is what matters, not staff status)
        assert result is True
