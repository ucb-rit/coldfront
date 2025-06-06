from django.db.models import Q

from coldfront.core.project.models import ProjectUser
from coldfront.core.statistics.models import Job


class JobAccessibilityManager(object):
    """A class that defines how read access to job data is delegated to
    users."""

    def __init__(self, *args, **kwargs):
        self._valid_project_user_role_names = (
            'Manager', 'Principal Investigator')
        self._valid_project_user_status_names = ('Active', 'Pending - Remove')

    def can_user_access_job(self, user, job):
        """Return whether the given User can access the given Job."""
        if self._user_has_global_access(user):
            return True

        is_user_project_pi_or_manager = ProjectUser.objects.filter(
            project=job.accountid,
            user=user,
            role__name__in=self._valid_project_user_role_names,
            status__name__in=self._valid_project_user_status_names).exists()
        if is_user_project_pi_or_manager:
            return True

        if user == job.userid:
            return True

        return False

    def get_jobs_accessible_to_user(self, user, include_global=False):
        """Return a queryset of Jobs accessible to the given User.
        Optionally include all Jobs across all users, which will only be
        returned if the User has global access."""
        if self._user_has_global_access(user) and include_global:
            return Job.objects.all()

        submitted_by_user_q = Q(userid=user)

        managed_project_pks = list(
            ProjectUser.objects.filter(
                user=user,
                role__name__in=self._valid_project_user_role_names,
                status__name__in=self._valid_project_user_status_names,
            ).values_list('project', flat=True))
        submitted_under_managed_project_q = Q(accountid__in=managed_project_pks)

        return Job.objects.filter(
            submitted_by_user_q | submitted_under_managed_project_q)

    @staticmethod
    def _user_has_global_access(user):
        """Return whether the given User has global access to all Jobs."""
        if user.is_superuser:
            return True
        if user.has_perm('statistics.view_job'):
            return True
        return False
