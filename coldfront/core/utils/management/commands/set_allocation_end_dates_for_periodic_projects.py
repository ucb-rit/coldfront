from coldfront.core.allocation.utils import get_project_compute_allocation
from coldfront.core.project.models import Project
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
import logging


class Command(BaseCommand):

    help = (
        "Sets Allocation end dates for periodically-renewed Projects to the "
        "given date.")

    logger = logging.getLogger(__name__)
    time_format = "%Y-%m-%dT%H:%M:%S"
    time_zone = timezone.utc

    def add_arguments(self, parser):
        parser.add_argument(
            "dt",
            help=f"The end date to set, in the form: {self.time_format}.")

    def handle(self, *args, **kwargs):
        date_time = kwargs["dt"]
        try:
            parsed_date_time = datetime.strptime(
                date_time, self.time_format).replace(tzinfo=self.time_zone)
        except ValueError:
            print(f"Date time {date_time} is invalid. Exiting.")
            return

        prefixes = []
        computing_allowance_interface = ComputingAllowanceInterface()
        for allowance in computing_allowance_interface.allowances():
            wrapper = ComputingAllowance(allowance)
            if wrapper.is_periodic():
                prefixes.append(
                    computing_allowance_interface.code_from_name(
                        allowance.name))
        prefixes = tuple(prefixes)

        for project in Project.objects.all():
            if project.name.startswith(prefixes):
                self.set_allocation_end_date(project, parsed_date_time)

    def set_allocation_end_date(self, project, date_time):
        """Set the end date of the given Project's compute Allocation to
        the given value."""
        try:
            allocation = get_project_compute_allocation(project)
            allocation.end_date = date_time
            allocation.save()
            self.logger.info(
                f"Set Allocation {allocation.pk} end_date to {date_time}.")
        except Exception as e:
            self.logger.exception(e)
            print(e)
