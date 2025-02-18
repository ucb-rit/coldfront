from django.contrib.auth.models import User

from coldfront.plugins.departments.utils.queries import UserDepartmentUpdater


"""Functions designed to be run as Django-Q tasks."""


def fetch_and_set_user_authoritative_departments(user_pk):
    """Attempt to fetch departments for the User with the given primary
    key from the configured data source, and create authoritative
    UserDepartments."""
    user = User.objects.get(pk=user_pk)

    user_department_updater = UserDepartmentUpdater(user, [])
    user_department_updater.run(authoritative=True, non_authoritative=False)
