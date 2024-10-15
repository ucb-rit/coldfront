from coldfront.plugins.ucb_departments.models import Department
from coldfront.plugins.ucb_departments.models import UserDepartment
from coldfront.plugins.ucb_departments.utils.ldap import (ldap_get_user_departments,
                                                          get_L4_code_from_department_code,
                                                          get_department_name_from_code)
import logging

logger = logging.getLogger(__name__)


def fetch_and_set_user_departments(user, userprofile, dry_run=False, l4_department_code_cache={}):
    """Fetch a user's departments from LDAP and set them in the
    database.

    Parameters:
        user (User): Django User object
        userprofile (UserProfile): Coldfront UserProfile object
        dry_run (bool): If True, don't actually make changes
                        (default: False)
    Returns:
        None
    """
    if dry_run:
        logger.info = print
    user_entry = ldap_get_user_departments(user.email, user.first_name, user.last_name)
    ldap_departments = user_entry if user_entry else []
    for department_code in ldap_departments:
        if department_code not in l4_department_code_cache:
            l4_department_code_cache[department_code] = \
                get_L4_code_from_department_code(department_code)
        department_code = l4_department_code_cache[department_code]

        if department_code is None:
            logger.warning(f'Could not find L4 code for department {department_code}')
            continue
        # If a Department doesn't exist, create it.
        name = None if Department.objects.filter(code=department_code).exists()\
            else get_department_name_from_code(department_code)
        if dry_run:
            department = Department(code=department_code, name=name)
            userdepartment = UserDepartment(userprofile=userprofile,
                                department=department, is_authoritative=True)
            created = name is not None
        else:
            department, created = Department.objects.get_or_create(
                                                    code=department_code,
                                                    defaults={'name': name})
        if created:
            logger.info(f'Created Department {department}')

        # Create a UserDepartment association, updating is_authoritative if
        # needed.
        if not UserDepartment.objects.filter(userprofile=userprofile,
                                             department__code=department_code,
                                             is_authoritative=True).exists():
            if dry_run:
                userdepartment = UserDepartment(userprofile=userprofile,
                                department=department, is_authoritative=True)
                print(f'Created UserDepartment {userdepartment}')
            else:
                UserDepartment.objects.update_or_create(userprofile=userprofile,
                                        department=department,
                                        defaults={'is_authoritative': True})
    return l4_department_code_cache
