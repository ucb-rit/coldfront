import logging

from django.db import transaction

from coldfront.plugins.departments.models import Department
from coldfront.plugins.departments.models import UserDepartment
from coldfront.plugins.departments.utils import UserInfoDict
from coldfront.plugins.departments.utils.data_sources import fetch_departments_for_user


logger = logging.getLogger(__name__)


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
            .filter(user=user)
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


class UserDepartmentUpdater(object):
    """A class that updates a User's authoritative and/or
    non-authoritative Department associations."""

    def __init__(self, user, non_authoritative_departments):
        self._user = user
        self._non_authoritative_departments = set(non_authoritative_departments)
        self._authoritative_departments = set()

    def run(self, authoritative=True, non_authoritative=True):
        """Update associations. Fetch and update authoritative ones,
        unless indicated. Update non-authoritative ones to those
        provided during instantiation, unless indicated. If any error
        occurs during fetching, skip updating authoritative ones."""
        if authoritative:
            try:
                authoritative_user_department_data = \
                    self._fetch_authoritative_user_departments()
            except Exception as e:
                authoritative = False

        with transaction.atomic():
            if authoritative:
                self._process_authoritative_user_departments(
                    authoritative_user_department_data)
            if authoritative and non_authoritative:
                # The order of updates should not matter since the two sets of
                # Departments should be mutually exclusive.
                self._update_non_authoritative_user_departments()
                self._update_authoritative_user_departments()
            elif authoritative:
                self._update_authoritative_user_departments()
            elif non_authoritative:
                self._update_non_authoritative_user_departments()

    def _fetch_authoritative_user_departments(self):
        """Fetch department data for the User from the data source."""
        try:
            user_data = UserInfoDict.from_user(self._user)
            return fetch_departments_for_user(user_data)
        except Exception as e:
            logger.error(
                f'Failed to fetch department data for User {self._user.pk}. '
                f'Details:')
            logger.exception(e)
            raise e

    def _process_authoritative_user_departments(self,
                                                authoritative_user_department_data):
        """Given department data for the User, fetched from the data
        source:
            1. Create Department objects as needed.
            2. Mark the Department as being authoritative, and NOT
               non-authoritative.
        """
        for code, name in authoritative_user_department_data:
            department, department_created = create_or_update_department(
                code, name)
            if department_created:
                logger.info(f'Created Department {department}.')
            self._authoritative_departments.add(department)
            self._non_authoritative_departments.discard(department)

    def _update_authoritative_user_departments(self):
        """Update authoritative associations to those set in this
        instance. Delete any other existing authoritative associations.
        This may involve updating non-authoritative associations to be
        authoritative."""
        for department in self._authoritative_departments:
            UserDepartment.objects.update_or_create(
                user=self._user,
                department=department,
                defaults={
                    'is_authoritative': True,
                })

        to_delete = (
            UserDepartment.objects
                .filter(
                    user=self._user,
                    is_authoritative=True)
                .exclude(department__in=self._authoritative_departments)
        )
        to_delete.delete()

    def _update_non_authoritative_user_departments(self):
        """Update non-authoritative associations to those set in this
        instance. Delete any other existing non-authoritative
        associations. Do not override any associations that are set
        authoritatively."""
        for department in self._non_authoritative_departments:
            existing_authoritative = UserDepartment.objects.filter(
                user=self._user,
                department=department,
                is_authoritative=True).exists()
            if existing_authoritative:
                continue
            UserDepartment.objects.update_or_create(
                user=self._user,
                department=department,
                defaults={
                    'is_authoritative': False,
                })

        to_delete = (
            UserDepartment.objects
                .filter(
                    user=self._user,
                    is_authoritative=False)
                .exclude(department__in=self._non_authoritative_departments)
        )
        to_delete.delete()
