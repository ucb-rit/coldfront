from coldfront.core.department.models import Department
from coldfront.core.department.models import UserDepartment

from ldap3 import Connection

LDAP_URL = 'ldap.berkeley.edu'
PEOPLE_OU = 'ou=people,dc=berkeley,dc=edu'
DEPARTMENT_OU = 'ou=org units,dc=berkeley,dc=edu'

def ldap_search_user(email, first_name, last_name):
    conn = Connection(LDAP_URL, auto_bind=True)
    conn.search(PEOPLE_OU,
                f'(&(objectClass=person)(mail={email}))',
                attributes=['departmentNumber']) or \
    conn.search(PEOPLE_OU,
                '(&(objectClass=person)'
                f'(givenName={first_name})(sn={last_name}))',
                attributes=['departmentNumber'])
    return conn

def get_L4_code_from_department_code(code):
    conn = Connection(LDAP_URL, auto_bind=True)
    conn.search(DEPARTMENT_OU,
                f'(&(objectClass=organizationalUnit)(ou={code}))',
                attributes=['berkeleyEduOrgUnitHierarchyString'])
    hierarchy = conn.entries[0].berkeleyEduOrgUnitHierarchyString.value
    return hierarchy.split('-')[3]

def get_department_name_from_code(code):
    conn = Connection(LDAP_URL, auto_bind=True)
    conn.search(DEPARTMENT_OU,
                f'(&(objectClass=organizationalUnit)(ou={code}))',
                attributes=['description'])
    return conn.entries[0].description.value

def fetch_and_set_user_departments(user, userprofile):
        conn = ldap_search_user(user.email, user.first_name, user.last_name)
        ldap_departments = conn.entries[0].departmentNumber.values if \
                            len(conn.entries) == 1 else []
        for department_code in ldap_departments:
            department_code = get_L4_code_from_department_code(department_code)
            # if department doesn't exist, make it
            if not Department.objects.filter(code=department_code).exists():
                name = get_department_name_from_code(department_code)
                department, _ = Department.objects.get_or_create(name=name,
                                                        code=department_code)
            else:
                department = Department.objects.get(code=department_code)
            # replace non-authoritative associations with authoritative ones
            UserDepartment.objects.filter(userprofile=userprofile,
                                          department=department,
                                          is_authoritative=False).delete()
            UserDepartment.objects.get_or_create(userprofile=userprofile,
                department=department,
                is_authoritative=True)