from coldfront.core.department.models import Department
from coldfront.core.department.models import UserDepartment
from ldap3 import Connection
import logging

logger = logging.getLogger(__name__)

LDAP_URL = 'ldap.berkeley.edu'
PEOPLE_OU = 'ou=people,dc=berkeley,dc=edu'
DEPARTMENT_OU = 'ou=org units,dc=berkeley,dc=edu'

def ldap_search_user(email, first_name, last_name):
    ''' Searches for a user in LDAP
    Parameters:
        email (str): Email address of user
        first_name (str): First name of user
        last_name (str): Last name of user
    Returns:
        (ldap3.Entry) LDAP entry for user or None if not found
    '''
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
    ''' Returns the L4 code for a department from a L4+ code
    Parameters:
        code (str): L4+ department code
    Returns:
        (str) Normalized L4 department code
    '''
    conn = Connection(LDAP_URL, auto_bind=True)
    conn.search(DEPARTMENT_OU,
                f'(&(objectClass=organizationalUnit)(ou={code}))',
                attributes=['berkeleyEduOrgUnitHierarchyString'])
    hierarchy = conn.entries[0].berkeleyEduOrgUnitHierarchyString.value
    return hierarchy.split('-')[3]

def get_department_name_from_code(code):
    ''' Returns the name of a department from a code
    Parameters:
       code (str): department code
    Returns:
        (str) Name of department
    '''
    conn = Connection(LDAP_URL, auto_bind=True)
    conn.search(DEPARTMENT_OU,
                f'(&(objectClass=organizationalUnit)(ou={code}))',
                attributes=['description'])
    return conn.entries[0].description.value

def fetch_and_set_user_departments(user, user_profile):
    ''' Fetches a user's departments from LDAP and sets them in the database
    Parameters:
        user (User): Django User object
        user_profile (UserProfile): Coldfront UserProfile object
    Returns:
        None
    '''
    user_entry = ldap_search_user(user.email, user.first_name, user.last_name)
    ldap_departments = user_entry.departmentNumber.values if user_entry else []
    for department_code in ldap_departments:
        department_code = get_L4_code_from_department_code(department_code)
        # if department doesn't exist, make it
        name = None if Department.objects.filter(code=department_code).exists() \
            else get_department_name_from_code(department_code)
        department, created = Department.objects.get_or_create(
                                                    code=department_code,
                                                    defaults={'name': name})
        if created:
            logger.info(f'Created department {department.pk}, '
                        f'{department.name} ({department.code})')

        # Create UserDepartment association, updating is_authorative if needed
        userdepartment, created = UserDepartment.objects.update_or_create(
                                        userprofile=user_profile,
                                        department=department,
                                        defaults={'is_authoritative': True})