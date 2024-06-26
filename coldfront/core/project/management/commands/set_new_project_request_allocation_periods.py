from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.common import add_argparse_dry_run_argument
from django.core.management import CommandError
from django.core.management.base import BaseCommand

import logging


"""An admin command that sets the AllocationPeriods for
SavioProjectAllocationRequests."""


class Command(BaseCommand):

    help = (
        'Set AllocationPeriods for SavioProjectAllocationRequests, either '
        'automatically or manually.')

    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(
            dest='subcommand',
            help='The subcommand to run.',
            title='subcommands')
        subparsers.required = True

        auto_parser = subparsers.add_parser(
            'auto',
            help=(
                'For requests missing an AllocationPeriod, automatically '
                'detect the correct one and set it. Warning: this command '
                'produces incorrect results for (a) requests for projects to '
                'be created for the next AllocationPeriod, although these '
                'should generally not be processed because they should '
                'already have periods set; and (b) requests for ICA projects '
                'for Summer Sessions.'))
        add_argparse_dry_run_argument(auto_parser)

        manual_parser = subparsers.add_parser(
            'manual',
            help='Set the AllocationPeriod for a particular request.')
        manual_parser.add_argument(
            'request_id',
            help='The ID of the SavioProjectAllocationRequest.',
            type=int)
        manual_parser.add_argument(
            'allocation_period_name',
            help='The name of the AllocationPeriod to set.',
            type=str)
        add_argparse_dry_run_argument(manual_parser)

    def handle(self, *args, **options):
        """Call the handler for the provided subcommand."""
        subcommand = options['subcommand']
        handler = getattr(self, f'handle_{subcommand}')
        handler(*args, **options)

    def handle_auto(self, *args, **options):
        """Handle the 'auto' subcommand."""
        computing_allowance_interface = ComputingAllowanceInterface()
        yearly_allowances, instructional_allowances = [], []
        for allowance in computing_allowance_interface.allowances():
            wrapper = ComputingAllowance(allowance)
            if not wrapper.is_periodic():
                continue
            if wrapper.is_yearly():
                yearly_allowances.append(allowance)
            elif wrapper.is_instructional():
                instructional_allowances.append(allowance)
        requests_and_allocation_periods = []
        requests_without_periods = \
            SavioProjectAllocationRequest.objects.filter(
                allocation_period=None).order_by('id')
        for request in requests_without_periods:
            if request.computing_allowance in yearly_allowances:
                allocation_periods = AllocationPeriod.objects.filter(
                    name__startswith='Allowance Year',
                    start_date__lte=request.created,
                    end_date__gte=request.created)
                num_allocation_periods = allocation_periods.count()
                if num_allocation_periods == 0:
                    raise CommandError(
                        f'Unexpectedly found no AllocationPeriod enclosing '
                        f'request {request.id} for allowance '
                        f'"{request.computing_allowance.name}", created at '
                        f'{request.created}.')
                elif num_allocation_periods == 1:
                    requests_and_allocation_periods.append(
                        (request, allocation_periods.first()))
                else:
                    allocation_period_names = allocation_periods.values_list(
                        'name', flat=True)
                    raise CommandError(
                        f'Unexpectedly found multiple AllocationPeriods '
                        f'({", ".join(allocation_period_names)}) enclosing '
                        f'request {request.id} for allowance '
                        f'"{request.computing_allowance.name}", created at '
                        f'{request.created}.')
            elif request.computing_allowance in instructional_allowances:
                year = request.extra_fields['year']
                semester = request.extra_fields['semester']
                # TODO: This filter handles the Fall and Spring semesters, but
                # TODO: not Summer Sessions, whose periods follow a different
                # TODO: naming scheme.
                allocation_periods = AllocationPeriod.objects.filter(
                    name__startswith=semester, name__endswith=year)
                num_allocation_periods = allocation_periods.count()
                if num_allocation_periods == 0:
                    raise CommandError(
                        f'Unexpectedly found no AllocationPeriod for request '
                        f'{request.id} for allowance '
                        f'"{request.computing_allowance.name}", for '
                        f'{semester} {year}.')
                elif num_allocation_periods == 1:
                    requests_and_allocation_periods.append(
                        (request, allocation_periods.first()))
                else:
                    allocation_period_names = allocation_periods.values_list(
                        'name', flat=True)
                    raise CommandError(
                        f'Unexpectedly found multiple AllocationPeriods '
                        f'({", ".join(allocation_period_names)}) for '
                        f'request {request.id} for allowance '
                        f'"{request.computing_allowance.name}", for '
                        f'{semester} {year}.')

        for request, allocation_period in requests_and_allocation_periods:
            self.set_allocation_period_for_request(
                request, allocation_period, dry_run=options['dry_run'])

    def handle_manual(self, *args, **options):
        """Handle the 'manual' subcommand."""
        request_id = options['request_id']
        try:
            request = SavioProjectAllocationRequest.objects.get(id=request_id)
        except SavioProjectAllocationRequest.DoesNotExist:
            raise CommandError(f'Invalid request {request_id}.')

        allocation_period_name = options['allocation_period_name']
        try:
            allocation_period = AllocationPeriod.objects.get(
                name=allocation_period_name)
        except AllocationPeriod.DoesNotExist:
            raise CommandError(
                f'Invalid AllocationPeriod {allocation_period_name}.')

        self.set_allocation_period_for_request(
            request, allocation_period, dry_run=options['dry_run'])

    def set_allocation_period_for_request(self, request, allocation_period,
                                          dry_run=False):
        """Set the AllocationPeriod for the given
        SavioProjectAllocationRequest, or merely display the update."""
        existing_allocation_period_name = getattr(
            request.allocation_period, 'name', None)
        message_template = (
            f'{{0}} AllocationPeriod for SavioProjectAllocationRequest '
            f'{request.id} ({request.project.name}) from '
            f'"{existing_allocation_period_name}" to '
            f'"{allocation_period.name}".')
        if dry_run:
            message = message_template.format('Would update')
            self.stdout.write(self.style.WARNING(message))
        else:
            request.allocation_period = allocation_period
            request.save()
            message = message_template.format('Updated')
            self.stdout.write(self.style.SUCCESS(message))
            self.logger.info(message)
