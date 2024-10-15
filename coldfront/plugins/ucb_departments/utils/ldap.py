from ldap3 import Connection
import logging

logger = logging.getLogger(__name__)

LDAP_URL = 'ldap.berkeley.edu'
PEOPLE_OU = 'ou=people,dc=berkeley,dc=edu'
DEPARTMENT_OU = 'ou=org units,dc=berkeley,dc=edu'

def ldap_search_all_departments():
    """Return all departments in LDAP.

    Returns:
        (list) List of LDAP entries for departments
    """
    # auto_range=True is needed for large searches
    conn = Connection(LDAP_URL, auto_bind=True, auto_range=True)
    conn.search(
        DEPARTMENT_OU,
        '(berkeleyEduOrgUnitHierarchyString=*-*-*-*)',
        attributes=['berkeleyEduOrgUnitHierarchyString', 'description'])
    return conn.entries

def ldap_get_user_departments(email, first_name, last_name):
    """Search for a user in LDAP and return their departments.

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
        return conn.entries[0].departmentNumber.values
    elif conn.search(PEOPLE_OU, '(&(objectClass=person)'
            f'(givenName={first_name})(sn={last_name}))',
            attributes=['departmentNumber']) and len(conn.entries) == 1:
        return conn.entries[0].departmentNumber.values
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
    if not conn.entries:
        return None
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
