from django.contrib.auth.models import User

from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.models import SecureDirAddUserRequest
from coldfront.core.allocation.models import SecureDirRemoveUserRequest

from coldfront.core.allocation.models import ProjectUser
from coldfront.core.allocation.utils import has_cluster_access


__all__ = [
    'SecureDirectory',
]


class SecureDirectory(object):
    """A wrapper around an Allocation that represents a secure
    directory."""

    def __init__(self, allocation_obj):
        self._allocation_obj = allocation_obj

    # TODO: Double check logic.
    # TODO: Order by?
    def get_addable_users(self):
        """Return a list of users that are eligible to be added to the
        directory.

        A user must meet the following criteria to be eligible:
            - Is an active member of any project belonging to any active
              PI of the project that owns the directory
            - Has cluster access under any project
            - Is not already part of the directory
            - Does not have any pending requests to be added to the
              directory
            - Does not have any pending requests to be removed from the
              directory
        """
        pis = self._allocation_obj.project.pis(active_only=True)

        pi_project_pks = (
            ProjectUser.objects.filter(
                user__in=pis,
                role__name='Principal Investigator',
                status__name='Active'
            ).values_list('project__pk', flat=True).distinct())

        eligible_user_pks = {
            ProjectUser.objects.filter(
                project__in=pi_project_pks,
                status__name='Active'
            ).values_list('user__pk', flat=True).distinct()}

        eligible_user_pks = {
            user_pk
            for user_pk in eligible_user_pks
            if has_cluster_access(user_pk)}

        for allocation_user in self._allocation_obj.allocationuser_set.filter(
                status__name='Active'):
            eligible_user_pks.discard(allocation_user.user.pk)

        pending_management_request_kwargs = {
            'allocation': self._allocation_obj,
            'status__name__in': ['Pending', 'Processing']
        }
        for request_obj in SecureDirAddUserRequest.objects.filter(
                **pending_management_request_kwargs):
            eligible_user_pks.discard(request_obj.user.pk)
        for request_obj in SecureDirRemoveUserRequest.objects.filter(
                **pending_management_request_kwargs):
            eligible_user_pks.discard(request_obj.user.pk)

        return User.objects.filter(pk__in=eligible_user_pks)

    # TODO: Double check logic.
    # TODO: Order by?
    def get_removable_users(self):
        """Return a list of users that are eligible to be removed from the
        directory.

        A user must meet the following criteria to be eligible:
            - Does not have any pending requests to be removed from the
              directory
            - Is not a PI of the project that owns the directory
        """
        eligible_user_pks = (
            self._allocation_obj.allocationuser_set.filter(
                status__name='Active'
            ).values_list('user__pk', flat=True).distinct())

        pending_management_request_kwargs = {
            'allocation': self._allocation_obj,
            'status__name__in': ['Pending', 'Processing']
        }
        for request_obj in SecureDirRemoveUserRequest.objects.filter(
                **pending_management_request_kwargs):
            eligible_user_pks.discard(request_obj.user.pk)

        pis = self._allocation_obj.project.pis(active_only=True)
        for pi in pis:
            eligible_user_pks.discard(pi.pk)

        return User.objects.filter(pk__in=eligible_user_pks)

    def user_can_manage(self, user):
        """Return whether the given User has permissions to manage this
        directory. The following users do:
            - Superusers
            - Active PIs of the project, regardless of whether they have
              been added to the directory
            - Active managers of the project who have been added to the
          directory
        """
        if user.is_superuser:
            return True

        project = self._allocation_obj.project
        if user in project.pis(active_only=True):
            return True

        if user in project.managers(active_only=True):
            user_on_allocation = AllocationUser.objects.filter(
                allocation=self._allocation_obj,
                user=user,
                status__name='Active')
            if user_on_allocation:
                return True

        return False

    # TODO: What other methods?
