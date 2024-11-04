from ldap3 import Connection

from .base import BaseDataSourceBackend


class CalNetLdapDataSourceBackend(BaseDataSourceBackend):
    """A backend that fetches department data from UC Berkeley's CalNet
    LDAP directory service.

    https://calnet.berkeley.edu/calnet-technologists/ldap-directory-service

    TODO: Discuss structure, which org units are considered departments
     in our case, etc. Give examples, etc.

    The departments of interest are "L4" org units.
    """

    DIRECTORY_URL = 'ldap.berkeley.edu'
    # The distinguished name (DN) of the "people" organizational unit.
    PEOPLE_DN = 'ou=people,dc=berkeley,dc=edu'
    # The distinguished name (DN) of the "org units" organizational unit.
    ORG_UNITS_OU = 'ou=org units,dc=berkeley,dc=edu'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._connection = Connection(
            self.DIRECTORY_URL, auto_bind=True, auto_range=True)
        # A mapping from the name of an "org units" OU to a tuple of the
        # identifier and description for the OU's department.
        self._cache_department_data_by_ou = {}

    def fetch_departments(self):
        """Return a generator of UC Berkeley departments, represented as
        tuples.

        Departments are org units at level 4 (L4) of the org tree.
        """
        identifier_attr = 'berkeleyEduOrgUnitHierarchyString'
        # This search filter returns L4 org units.
        # The first portion includes org units with at least three hyphens (L4
        # and above).
        # The second portion excludes org units with at least four hyphens (L5
        # and above).
        search_filter = (
            f'({identifier_attr}=*-*-*-*)(!({identifier_attr}=*-*-*-*-*)))')
        for identifier, description in self._lookup_org_units(search_filter):
            yield identifier.split('-')[3], description

    def fetch_departments_for_user(self, user_data):
        """Return a generator of UC Berkeley departments, represented as
        tuples, associated with the given person, represented as a dict.

        Search for the person in the "people" OU, as follows:
             1. Attempt to find entries for the person from associated
                email addresses.
             2. If and only if none are found, attempt to find an entry
                for the person from first and last name. Only use an
                entry if it is the only one (i.e., not if there are
                multiple people with the same name).

        The resulting entries list department numbers associated with
        the person. Look up and return the corresponding L4 org units
        from the "org units" OU.

        A mapping from department number to the corresponding L4 org
        units is cached within the instance to reduce redundant LDAP
        lookups.
        """
        # Due to short-circuiting, if the email lookup produces results, the
        # name lookup is skipped.
        results = (
            self._lookup_person_department_numbers_from_emails(
                user_data['emails'])
            or
            self._lookup_person_department_numbers_from_name(
                user_data['first_name'], user_data['last_name']))

        for department_number in results:
            if department_number not in self._cache_department_data_by_ou:
                identifier, description = \
                    self._lookup_department_info_for_org_unit(department_number)
                self._cache_department_data_by_ou[department_number] = (
                    identifier, description)
            identifier, description = self._cache_department_data_by_ou[
                department_number]
            if identifier is not None and description is not None:
                yield identifier, description

    def _lookup_department_info_for_org_unit(self, ou):
        """Given the identifier for an org unit at the department (L4)
        level or above (higher levels are deeper in the org tree),
        return the identifier and description for its department. Return
        None for both if no matching OU is found.

        Parameters:
            - ou (str): The identifier for an org unit (e.g., "JICCS")

        Returns:
            - Two strs denoting the identifier and description for the
              department that the org unit is (a) under or (b) identical
              to
            - None, None if no matching OU is found

        Raises:
            - ValueError, if the provided OU is not at least as deep as
              the department (L4) level.
        """
        search_filter = f'(&(objectClass=organizationalUnit)(ou={ou}))'
        for identifier, description in self._lookup_org_units(search_filter):
            if identifier.count('-') < 3:
                raise ValueError(
                    f'Org unit "{ou}" is broader than the department level.')
            # There should only be one result.
            return identifier.split('-')[3], description
        return None, None

    def _lookup_org_units(self, search_filter):
        """Given an LDAP search filter for the "org units" OU, return a
        generator of tuples containing the hierarchy string and
        description for each matching org unit. Return an empty list if
        no matching org units are found.

        Parameters:
            - search_filter (str): An LDAP search filter to be used to
              search the "org units" OU

        Returns:
            - Generator of tuples of the form (org unit hierarchy
              string (str), org unit description (str)) if matching
              results are found. E.g.,
                  ("UCBKL-AVCIS-VRIST-JICCS", "Sample Description 1"),
                  ("UCBKL-AVCIS-VRIST-JJCNS", "Sample Description 2"),
            - An empty list otherwise
        """
        search_base = self.ORG_UNITS_OU
        hierarchy_string_attr = 'berkeleyEduOrgUnitHierarchyString'
        description_attr = 'description'
        attributes = [hierarchy_string_attr, description_attr]

        results_found = self._connection.search(
            search_base, search_filter, attributes=[attributes])
        if not results_found:
            return []

        for entry in self._connection.entries:
            hierarchy_string = getattr(entry, hierarchy_string_attr).value
            description = getattr(entry, description_attr).value
            yield hierarchy_string, description

    def _lookup_person_department_numbers(self, search_filter,
                                          assert_one_person=False):
        """Given an LDAP search filter for the "people" OU, return a set
        of department numbers associated with all matching entries.

        Optionally require that there be at most one matching person.

        Parameters:
            - search_filter (str): An LDAP search filter to be used to
              search the "people" OU
            - assert_one_person (bool): An optional flag that requires
              that there must be at most one matching person in the
              search results

        Returns:
            - Set of strs representing department numbers that are
              identifiers for L4 org units (e.g., {"JICCS", "JJCNS"})
            - An empty set of no people entries are found

        Raises:
            - AssertionError, if assert_one_person is specified, but
              more than one person is found
        """
        search_base = self.PEOPLE_DN
        department_number_attr = 'departmentNumber'
        attributes = [department_number_attr]

        results_found = self._connection.search(
            search_base, search_filter, attributes=[attributes])
        if not results_found:
            return set()

        if assert_one_person:
            message = 'More than one matching person found.'
            assert len(self._connection.entries) == 1, message
            # The for loop below will run once.

        results = set()
        for entry in self._connection.entries:
            department_numbers = getattr(entry, department_number_attr).values
            for department_number in department_numbers:
                results.add(department_number)
        return results

    def _lookup_person_department_numbers_from_emails(self, emails):
        """Given a list of emails (strs) associated with a single
        person, return a set of department numbers associated with all
        entries in the "people" OU matching those* emails.

        *Only consider email addresses that end with "berkeley.edu"
        (e.g., "email@berkeley.edu", "email@cs.berkeley.edu").

        Parameters:
            - emails (list<str>): Emails associated with a single person

        Returns:
            - Set of strs representing department numbers that are
              identifiers for L4 org units (e.g., {"JICCS", "JJCNS"})
        """
        berkeley_email_suffix = 'berkeley.edu'
        results = set()
        for email in emails:
            if not email.endswith(berkeley_email_suffix):
                continue
            search_filter = f'(&(objectClass=person)(mail={email}))'
            for department_number in self._lookup_person_department_numbers(
                    search_filter, assert_one_person=False):
                results.add(department_number)
        return results

    def _lookup_person_department_numbers_from_name(self, first_name,
                                                    last_name):
        """Given a person's first and last name (strs), return a set of
        department numbers associated with at most a single entry in the
        "people" OU matching that name. If there are multiple, return an
        empty set.

        Parameters:
            - first_name (str): A person's first name
            - last_name (str): A person's last name

        Returns:
            - Set of strs representing department numbers that are
              identifiers for L4 org units (e.g., {"JICCS", "JJCNS"})
        """
        results = set()
        search_filter = f'(givenName={first_name})(sn={last_name}))'
        try:
            department_numbers = self._lookup_person_department_numbers(
                search_filter, assert_one_person=True)
        except AssertionError:
            pass
        else:
            for department_number in department_numbers:
                results.add(department_number)
        return results
