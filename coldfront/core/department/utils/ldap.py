from coldfront.core.department.models import Department
from coldfront.core.department.models import UserDepartment
from ldap3 import Connection
import logging

logger = logging.getLogger(__name__)

LDAP_URL = 'ldap.berkeley.edu'
PEOPLE_OU = 'ou=people,dc=berkeley,dc=edu'
DEPARTMENT_OU = 'ou=org units,dc=berkeley,dc=edu'


def ldap_search_user(email, first_name, last_name):
    """Search for a user in LDAP.

    Parameters:
        email (str): Email address of user
        first_name (str): First name of user
        last_name (str): Last name of user
    Returns:
        (ldap3.Entry) LDAP entry for user or None if not found
    """
    conn = Connection(LDAP_URL, auto_bind=True)
    if conn.search(PEOPLE_OU, f'(&(objectClass=person)(mail={email}))',
                                            attributes=['departmentNumber']):
        return conn.entries[0]
    elif conn.search(PEOPLE_OU, '(&(objectClass=person)'
            f'(givenName={first_name})(sn={last_name}))',
            attributes=['departmentNumber']) and len(conn.entries) == 1:
        return conn.entries[0]
    return None


def get_L4_code_from_department_code(code):
    """Return the L4 code for a department from a L4+ code.
    L4 are departments like "Integrative Biology (IBIBI)"
    L5 are subsets of L4 like "BSINB Dept Administration (IBADM)"
    L6 are subsets of L5 like "IB Student Services (IBSTD)"

    Parameters:
        code (str): L4+ department code
    Returns:
        (str) Normalized L4 department code
    """
    conn = Connection(LDAP_URL, auto_bind=True)
    conn.search(DEPARTMENT_OU,
                f'(&(objectClass=organizationalUnit)(ou={code}))',
                attributes=['berkeleyEduOrgUnitHierarchyString'])
    hierarchy = conn.entries[0].berkeleyEduOrgUnitHierarchyString.value
    return hierarchy.split('-')[3]


def get_department_name_from_code(code):
    """Return the name of a department from its code (any level but ideally only L4).
    Example: "IBIBI" -> "Integrative Biology"

    Parameters:
       code (str): department code
    Returns:
        (str) Name of department
    """
    conn = Connection(LDAP_URL, auto_bind=True)
    conn.search(DEPARTMENT_OU,
                f'(&(objectClass=organizationalUnit)(ou={code}))',
                attributes=['description'])
    return conn.entries[0].description.value


def fetch_and_set_user_departments(user, userprofile, dry_run=False):
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
        department = Department()
        department.pk = '{placeholder_pk}'
        userdepartment = UserDepartment()
        userdepartment.pk = '{placeholder_pk}'
    user_entry = ldap_search_user(user.email, user.first_name, user.last_name)
    ldap_departments = user_entry.departmentNumber.values if user_entry else []
    for department_code in ldap_departments:
        department_code = get_L4_code_from_department_code(department_code)
        # If a Department doesn't exist, create it.
        name = None if Department.objects.filter(code=department_code).exists() \
            else get_department_name_from_code(department_code)
        if dry_run:
            created = name is not None
            department.code = department_code
            department.name = department_code
        else:
            department, created = Department.objects.get_or_create(
                                                    code=department_code,
                                                    defaults={'name': name})
        if created:
            logger.info(f'Created Department {department.pk}, '
                        f'{department.name} ({department.code})')

        # Create a UserDepartment association, updating is_authoritative if
        # needed.
        if not dry_run:
            userdepartment, created = UserDepartment.objects.update_or_create(
                                            userprofile=userprofile,
                                            department=department,
                                            defaults={'is_authoritative': True})

        if dry_run and not UserDepartment.objects.filter(
                                            userprofile=userprofile,
                                            department__code=department_code,
                                            is_authoritative=True).exists():
            print(f'Created UserDepartment {userdepartment.pk}, '
                        f'{user.first_name} {user.last_name}-{department_code}')
