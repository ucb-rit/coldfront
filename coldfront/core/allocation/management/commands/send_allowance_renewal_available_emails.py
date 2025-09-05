import logging

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand

from flags.state import flag_enabled

from coldfront.core.project.utils_.renewal_utils import AllowanceRenewalAvailableEmailSender
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.project.utils_.renewal_utils import get_next_allowance_year_period
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.constants import LRCAllowances
from coldfront.core.utils.common import add_argparse_dry_run_argument
from coldfront.core.utils.email.email_strategy import EnqueueEmailStrategy


class Command(BaseCommand):

    help = (
        'Send emails to active projects with FCAs (BRC) or PCAs (LRC), '
        'notifying them that they may renew their computing allowance for the '
        'upcoming allowance year.')

    logger = logging.getLogger(__name__)

    # TODO: Consider only sending the email to projects that have not yet
    #  renewed, so that this command can be safely re-run for subsequent emails.

    def add_arguments(self, parser):
        add_argparse_dry_run_argument(parser)

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        current_allowance_year = get_current_allowance_year_period()
        next_allowance_year = get_next_allowance_year_period()

        if flag_enabled('BRC_ONLY'):
            computing_allowance_name = BRCAllowances.FCA
        elif flag_enabled('LRC_ONLY'):
            computing_allowance_name = LRCAllowances.PCA
        else:
            raise ImproperlyConfigured(
                'Exactly one of BRC_ONLY, LRC_ONLY should be enabled.')
        computing_allowance = ComputingAllowance(
            Resource.objects.get(name=computing_allowance_name))

        email_strategy = EnqueueEmailStrategy()

        email_sender = AllowanceRenewalAvailableEmailSender(
            current_allowance_year, next_allowance_year, computing_allowance,
            email_strategy=email_strategy)
        email_sender.run()

        num_emails = len(email_strategy.get_queue())
        if dry_run:
            message = f'Would send emails to {num_emails} projects.'
            self.stdout.write(self.style.WARNING(message))
        else:
            user_confirmation = input(
                f'This will send emails to {num_emails} projects. Are you sure '
                f'you wish to proceed? [Y/y/N/n]: ')
            if user_confirmation.strip().lower() != 'y':
                self.stdout.write(self.style.WARNING('Operation cancelled.'))
                return

            email_strategy.send_queued_emails()

            sent_message = (
                f'Sent emails to {num_emails} projects. Check logs for errors.')
            self.stdout.write(self.style.SUCCESS(sent_message))
