import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.project.utils_.renewal_utils import AllocationRenewalApprovalRunner
from coldfront.core.utils.common import add_argparse_dry_run_argument
from coldfront.core.utils.common import display_time_zone_current_date
from coldfront.core.utils.common import display_time_zone_date_to_utc_datetime
from coldfront.core.utils.common import utc_now_offset_aware


"""An admin command that approves AllocationRenewalRequests for a
particular Allocation Period."""


class Command(BaseCommand):

    help = (
        'Approve AllocationRenewalRequests for the AllocationPeriod with the '
        'given ID, for requests made before the start of the period and '
        'currently "Under Review". Warning: Currently, this command is only '
        'intended for use for FCA renewal requests on BRC.')

    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument(
            'allocation_period_id',
            help='The ID of the AllocationPeriod.',
            type=int)
        add_argparse_dry_run_argument(parser)

    def handle(self, *args, **options):
        """Approve eligible requests if the AllocationPeriod is valid
        and eligible."""
        dry_run = options['dry_run']

        allocation_period_id = options['allocation_period_id']
        try:
            allocation_period = AllocationPeriod.objects.get(
                pk=allocation_period_id)
        except AllocationPeriod.DoesNotExist:
            raise CommandError(
                f'AllocationPeriod {allocation_period_id} does not exist.')

        # TODO: If supporting other allocation types, remove this check.
        if not allocation_period.name.startswith('Allowance Year'):
            raise CommandError(
                f'AllocationPeriod {allocation_period_id} does not represent '
                f'an allowance year.')

        current_date = display_time_zone_current_date()
        allocation_period_start_date = allocation_period.start_date
        if allocation_period_start_date <= current_date:
            raise CommandError(
                f'AllocationPeriod {allocation_period_id} has already '
                f'started.')

        # TODO: If supporting other allocation types, remove the filter on the
        # TODO: project name.
        allocation_period_start_utc = display_time_zone_date_to_utc_datetime(
            allocation_period_start_date)
        requests = AllocationRenewalRequest.objects.filter(
            allocation_period=allocation_period, status__name='Under Review',
            post_project__name__startswith='fc_',
            request_time__lt=allocation_period_start_utc)

        # TODO: If supporting other allocation types, choose the appropriate
        # TODO: base value.
        num_service_units = settings.FCA_DEFAULT_ALLOCATION

        message_template = (
            f'{{0}} AllocationRenewalRequest {{1}} for PI {{2}}, scheduling '
            f'{{3}} to be granted to {{4}} on {allocation_period_start_date}, '
            f'and emailing the requester and/or PI.')
        for request in requests:
            message_args = [
                request.pk, request.pi, num_service_units,
                request.post_project.name]
            if dry_run:
                phrase = 'Would automatically approve'
                message = message_template.format(phrase, *message_args)
                self.stdout.write(self.style.WARNING(message))
            else:
                try:
                    self.update_request_state(request)
                    request.refresh_from_db()
                    self.approve_request(request, num_service_units)
                except Exception as e:
                    message = (
                        f'Failed to approve AllocationRenewalRequest '
                        f'{request.pk}. Details:\n'
                        f'{e}')
                    self.stderr.write(self.style.ERROR(message))

                phrase = 'Automatically approved'
                message = message_template.format(phrase, *message_args)
                self.stdout.write(self.style.SUCCESS(message))
                self.logger.info(message)

    @staticmethod
    def update_request_state(request):
        """Fill in the 'Eligibility' field in the given request's
        state."""
        state = request.state
        eligibility = state['eligibility']
        eligibility['status'] = 'Approved'
        eligibility['timestamp'] = utc_now_offset_aware().isoformat()
        request.save()

    @staticmethod
    def approve_request(request, num_service_units):
        """Instantiate and run tne approval runner for the given request
        and number of service units, sending emails."""
        approval_runner = AllocationRenewalApprovalRunner(
            request, num_service_units, send_email=True)
        approval_runner.run()
