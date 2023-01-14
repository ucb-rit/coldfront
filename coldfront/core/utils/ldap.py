from ldap3 import Connection

LDAP_URL = 'ldap.berkeley.edu'
PEOPLE_OU = 'ou=people,dc=berkeley,dc=edu'
DEPARTMENT_OU = 'ou=org unit,dc=berkeley,dc=edu'
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
                f'(&(objectClass=organizationalUnit)(ou={code}))')
    hierarchy = conn.entries[0].berkeleyEduOrgUnitHierarchyString.value
    return hierarchy.split('-')[3]

def get_name_from_code(code):
    conn = Connection(LDAP_URL, auto_bind=True)
    conn.search(DEPARTMENT_OU,
                f'(&(objectClass=organizationalUnit)(ou={code}))')
    return conn.entries[0].description.value