from datetime import timedelta

from django.core.management.base import BaseCommand

from coldfront.core.project.utils_.renewal_utils import get_next_allowance_year_period
from coldfront.core.project.utils_.renewal_utils import send_mass_renewal_emails
from django_q.models import Schedule
from django_q.tasks import schedule

# How many days before the next period's start date should this command run
DAYS_BEFORE_ALLOCATION_START = 25

class Command(BaseCommand):
    """ This command starts the `django-q` schedule which calls 
    `send_mass_renewal_emails` at the start of every allocation period 
    (for FCAs/PCAs). """
    def handle(self, *args, **options):
        next_period = get_next_allowance_year_period()

        if next_period:
            send_mass_renewal_emails()

            func = 'django.core.management.call_command'
            schedule_args = ('add_scheduled_renewal_email')
            schedule_kwargs = {
                'next_run': next_period.start_date - timedelta(
                    days=DAYS_BEFORE_ALLOCATION_START),
                'schedule_type': Schedule.ONCE,
            }
            schedule(func, *schedule_args, **schedule_kwargs)
