from coldfront.plugins.departments.models import Department
from coldfront.plugins.departments.models import UserDepartment


def create_or_update_department(code, name):
    department, created = Department.objects.update_or_create(
        code=code,
        defaults={
            'name': name,
        })
    return department, created


def get_departments_for_user(user, strs_only=False):
    """Return two lists: Departments the given User is (a)
    authoritatively and (b) non-authoritatively associated with. Each
    list is sorted by ascending name.

    Optionally return the str representation of each Department instead
    of the Department itself.
    """
    user_departments = (
        UserDepartment.objects
            .filter(userprofile=user.userprofile)
            .select_related('department')
            .order_by('department__name'))

    authoritative, non_authoritative = [], []
    for user_department in user_departments:
        department = user_department.department
        entry = str(department) if strs_only else department
        if user_department.is_authoritative:
            authoritative.append(entry)
        else:
            non_authoritative.append(entry)

    return authoritative, non_authoritative
