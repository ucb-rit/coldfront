from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationAttributeUsage
from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.models import AllocationUserAttributeUsage
from coldfront.core.allocation.utils import get_or_create_active_allocation_user
from coldfront.core.allocation.utils import set_allocation_user_attribute_value
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser
from coldfront.core.resource.models import Resource
from coldfront.core.statistics.models import ProjectTransaction
from coldfront.core.statistics.models import ProjectUserTransaction
from coldfront.core.utils.common import utc_now_offset_aware
from datetime import date
from decimal import Decimal
from decimal import InvalidOperation
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
import iso8601
import logging
import os
import pytz


"""An admin command that loads allocation data for LRC."""


PROJECT_PREFIXES = {'ac_', 'lr_', 'pc_'}


class Command(BaseCommand):

    help = 'Loads allocation data from an LRC configuration file.'
    logger = logging.getLogger(__name__)

    def __init__(self, *args, **kwargs):
        self.pc_allocation_period = AllocationPeriod.objects.get(
            name='AY21-22')

    def add_arguments(self, parser):
        parser.add_argument(
            'file',
            help=(
                'The path to the file where each line is of the form:'
                'project_name|modified_time|allocation_cpu_minutes|comment. '
                'Lines that begin with "#" are comments, and may be ignored.'))

    def handle(self, *args, **options):
        # Retrieve data from the configuration file, filtering out and logging
        # invalid entries.
        valid_allocations = self.get_valid_allocations(options['file'])
        # Set up Allocations for Projects and their Users.
        for project_name, project_data in valid_allocations.items():
            num_service_units = project_data[1]
            project = Project.objects.get(name=project_name)
            kwargs = {
                'start_date': project_data[0].date(),
            }
            self.set_up_allocations(project, num_service_units, **kwargs)
        # Set up Allocations with zero SUs for Lawrencium projects that do not
        # have one. Only set start dates for PCA projects.
        condition = Q()
        for prefix in PROJECT_PREFIXES:
            condition = condition | Q(name__startswith=prefix)
        for project in Project.objects.filter(condition):
            kwargs = {}
            if project.name.startswith('pc_'):
                kwargs['start_date'] = self.pc_allocation_period.start_date
            self.set_up_allocations(project, Decimal('0.00'), **kwargs)

    @staticmethod
    def file_exists(file_path):
        """Return whether the object at the given path is an existing
        file.

        Parameters:
            - file_path (str): the path to the file to test

        Returns:
            - Boolean

        Raises:
            - None
        """
        return os.path.exists(file_path) and os.path.isfile(file_path)

    def get_valid_allocations(self, file_path):
        """Return a mapping from project name to (latest allocation
        start datetime (LA time), number of service units (Decimal)),
        retrieved from the configuration file at the given path. The
        amount for a given project is taken as follows:

            - Recharge (ac_): The last value found for the project.
            - Condo (lr_): The maximum allowed value.
            - PCA (pc_): The last value found for the project where the
              modification time is greater than or equal to the start of
              a hard-coded AllocationPeriod.

        Skip and log errors for invalid entries.

        Parameters:
            - file_path (str): The path to the configuration file

        Returns:
            - Dictionary mapping project name to a pair of values

        Raises:
            - Exception, if any errors occur
        """
        if not self.file_exists(file_path):
            raise FileNotFoundError(f'File {file_path} does not exist.')

        pc_start_date = self.pc_allocation_period.start_date
        parse_timezone = pytz.timezone('America/Los_Angeles')

        min_sus, max_sus = settings.ALLOCATION_MIN, settings.ALLOCATION_MAX

        valid_allocation_data = {}
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#'):
                    continue
                fields = [field.strip() for field in line.split('|')]
                if len(fields) != 4:
                    self.logger.error(
                        f'The entry {fields} does not have 4 fields.')
                    continue

                project_name = fields[0].strip()
                if not project_name:
                    self.logger.error(
                        f'The entry {fields} is missing a project name.')
                    continue
                if not project_name.startswith(tuple(PROJECT_PREFIXES)):
                    self.logger.error(
                        f'The entry {fields} has a project name with an '
                        f'invalid prefix.')
                    continue
                try:
                    Project.objects.get(name=project_name)
                except Project.DoesNotExist:
                    self.logger.error(
                        f'Project {project_name} does not exist.')
                    continue

                try:
                    modification_dt = iso8601.parse_date(
                        fields[1].strip(), default_timezone=parse_timezone)
                except iso8601.ParseError:
                    self.logger.error(
                        f'The entry {fields} has a modification time that '
                        f'does not conform to ISO 8601.')
                    continue

                # Use the entry with the latest modification time for a
                # particular project. On ties, prefer entries on later lines.
                if (project_name in valid_allocation_data and
                        modification_dt < valid_allocation_data[
                            project_name][0]):
                    continue

                try:
                    allocation_cpu_minutes = Decimal(fields[2].strip())
                except InvalidOperation:
                    self.logger.error(
                        f'The entry {fields} has an invalid allocation in CPU '
                        f'minutes.')
                    continue
                num_service_units = allocation_cpu_minutes // 60
                if not (min_sus <= num_service_units <= max_sus):
                    self.logger.error(
                        f'The entry {fields} has an out-of-bounds allocation.')
                    continue

                if project_name.startswith('ac_'):
                    pass
                elif project_name.startswith('lr_'):
                    num_service_units = max_sus
                elif project_name.startswith('pc_'):
                    if modification_dt.date() < pc_start_date:
                        continue
                else:
                    continue

                valid_allocation_data[project_name] = (
                    modification_dt, num_service_units)

        return valid_allocation_data

    def set_up_allocations(self, project, num_service_units, start_date=None):
        """Set service units and optionally start dates for the
        Lawrencium Compute resource for the given project and all its
        users. Create any intermediate objects as needed.

        Parameters:
            - project (Project): a Project instance
            - num_service_units (Decimal): the number of service units
              to allocate
            - start_date (Date, optional): a date object

        Returns:
            - None

        Raises:
            - ObjectDoesNotExist, if an expected database object does
            not exist
            - MultipleObjectsReturned, if a given Project has more than
            one allocation to the Lawrencium Compute resource
        """
        if not isinstance(project, Project):
            raise TypeError(f'{project} is not a Project.')
        if not isinstance(num_service_units, Decimal):
            raise TypeError(f'{num_service_units} is not a Decimal.')
        if start_date is not None and not isinstance(start_date, date):
            raise TypeError(f'{start_date} is not a Date.')

        kwargs = {
            'start_date': start_date,
            'num_service_units': num_service_units,
        }
        # PCA projects have end dates, but Recharge and Condo projects do not.
        if project.name.startswith('pc_'):
            kwargs['end_date'] = self.pc_allocation_period.end_date

        allocation = self.set_up_project_allocation(project, **kwargs)

        # Setup allocations for each of the project's users.
        project_users = ProjectUser.objects.prefetch_related(
            'status', 'user__userprofile'
        ).filter(project=project, status__name='Active')
        for project_user in project_users:
            self.set_up_project_user_allocation(
                project_user, allocation, num_service_units=num_service_units)

    @staticmethod
    def set_up_project_allocation(project, start_date=None, end_date=None,
                                  num_service_units=Decimal('0.00')):
        """Create an Allocation to the Lawrencium Compute resource for
        the given Project, set its start and end dates, set its service
        units to the given value, and create a transaction. Return the
        created Allocation.

        Parameters:
            - project (Project): a Project instance
            - start_date (date, optional): a date object
            - end_date (date, optional): a date object
            - num_service_units (Decimal, optional): the number of
              service units to allocate

        Returns:
            - Allocation

        Raises:
            - ObjectDoesNotExist, if an expected database object does
            not exist
            - MultipleObjectsReturned, if a given Project has more than
            allocation to the Lawrencium Compute resource
        """
        resource = Resource.objects.get(name='Lawrencium Compute')
        defaults = {
            'status': AllocationStatusChoice.objects.get(name='Active'),
            'start_date': start_date,
            'end_date': end_date,
        }
        allocation, _ = Allocation.objects.get_or_create(
            project=project, defaults=defaults)
        allocation.resources.add(resource)
        allocation.save()

        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Service Units')
        allocation_attribute, _ = AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type,
            allocation=allocation, defaults={'value': str(num_service_units)})

        ProjectTransaction.objects.create(
            project=project,
            date_time=utc_now_offset_aware(),
            allocation=num_service_units)

        # A usage should have been created for the attribute.
        try:
            AllocationAttributeUsage.objects.get(
                allocation_attribute=allocation_attribute)
        except AllocationAttributeUsage.DoesNotExist:
            raise AllocationAttributeUsage.DoesNotExist(
                f'Unexpected: No AllocationAttributeUsage object exists for'
                f'AllocationAttribute {allocation_attribute.pk}.')

        return allocation

    @staticmethod
    def set_up_project_user_allocation(project_user, allocation,
                                       num_service_units=Decimal('0.00')):
        """Create an AllocationUser under the given Allocation for the
        given ProjectUser, set its service units to the given value,
        create a transaction, and activate its cluster account
        status if appropriate. Return the created AllocationUser."""
        user = project_user.user
        allocation_user = get_or_create_active_allocation_user(
            allocation, user)
        allocation_user_attribute = set_allocation_user_attribute_value(
            allocation_user, 'Service Units', str(num_service_units))

        ProjectUserTransaction.objects.create(
            project_user=project_user,
            date_time=utc_now_offset_aware(),
            allocation=num_service_units)

        # A usage should have been created for the attribute.
        try:
            AllocationUserAttributeUsage.objects.get(
                allocation_user_attribute=allocation_user_attribute)
        except AllocationUserAttributeUsage.DoesNotExist:
            raise AllocationUserAttributeUsage.DoesNotExist(
                f'Unexpected: No AllocationUserAttributeUsage object '
                f'exists for AllocationUserAttribute '
                f'{allocation_user_attribute.pk}.')

        # If the user has a cluster UID, set the AllocationUser's 'Cluster
        # Account Status' attribute to 'Active'.
        if user.userprofile.cluster_uid:
            set_allocation_user_attribute_value(
                allocation_user, 'Cluster Account Status', 'Active')

        return allocation_user
