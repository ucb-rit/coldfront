from .base import BaseDataSourceBackend


class DummyDataSourceBackend(BaseDataSourceBackend):
    """A backend for testing purposes."""

    def fetch_departments(self):
        """Return a generator of 26 tuples, each representing a
        department associated with an uppercase alphabetic letter:
            ("DEPTA", "Department A"),
            ("DEPTB", "Department B"),
            ...
            ("DEPTZ", "Department Z").
        """
        for ascii_code in range(ord('A'), ord('Z') + 1):
            letter = chr(ascii_code)
            yield self._get_department_for_letter(letter)

    def fetch_departments_for_user(self, user_data):
        """Return a generator of up to two departments matching the
        first and last initials of the given user dict. If a particular
        initial is non-alphabetic, do not include a result for that
        initial. Yield the departments in alphabetic order.

        Examples:
            - "John Smith" -->
                ("DEPTJ", "Department J"),
                ("DEPTS", "Department S")
            - "Jane Doe" -->
                ("DEPTD", "Department D"),
                ("DEPTJ", "Department J")
            - "First 0" -->
                ("DEPTF, "Department F")
            - "Last" (no first name) -->
                ("DEPTL, "Department L")
            - (no first or last name) --> no results
        """

        def _get_department_for_name_part(_name_part):
            if not _name_part:
                return None
            initial = _name_part[0]
            if not initial.isalpha():
                return None
            initial = initial.upper()
            return self._get_department_for_letter(initial)

        departments = []
        for name_part in (user_data['first_name'], user_data['last_name']):
            department = _get_department_for_name_part(name_part)
            if not department:
                continue
            departments.append(department)
        departments.sort(key=lambda d: d[0])

        yield from departments

    @staticmethod
    def _get_department_for_letter(letter):
        """Return the identifier and description for the department
        corresponding to the given letter, which is assumed to be an
        uppercase alphabetic letter."""
        identifier = f'DEPT{letter}'
        description = f'Department {letter}'
        return identifier, description
