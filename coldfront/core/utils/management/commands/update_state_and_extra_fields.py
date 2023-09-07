'''
update old requests with new default values for state and extra_fields
STATE:
AllocationAdditionRequest, SecureDirRequest, SavioProjectAllocationRequest (Recharge, ICA):
        'notified': {
            'status': 'Pending',
            'timestamp': '', }

EXTRA_FIELDS:
SavioProjectAllocationRequest (ICA):
        'course_name': '',
        'course_department': '',
        'point_of_contact': '',
'''

from django.core.management.base import BaseCommand
from django.db.models import Q

from coldfront.core.allocation.models import (AllocationAdditionRequest,
                                              SecureDirRequest)
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.user.models import UserProfile
from coldfront.core.allocation.models import AllocationAttribute

from coldfront.core.project.utils_.renewal_utils import \
    get_current_allowance_year_period
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import \
    ComputingAllowance
from coldfront.core.utils.common import display_time_zone_current_date

class Command(BaseCommand):
    help = 'Audit data to ensure that certain invariants hold.'

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true',
            help='Update both state and extra fields')
        parser.add_argument('--state', action='store_true',
            help='Update state')
        parser.add_argument('--extra-fields', action='store_true',
            help='Update extra fields')
        parser.add_argument('--dry-run', action='store_true',
            help='Update extra fields')

    @staticmethod
    def add_notified_to_state(request, dry_run=False):
        if 'notified' not in request.state:
            request.state['notified'] = {
            'status': 'Pending',
            'timestamp': '',
            }
            if dry_run:
                print(f'Added "notified" to state for {request}')
            else:
                request.save()

    @staticmethod
    def add_ica_extra_fields(request, dry_run=False):
        save = False
        for field in ('course_name', 'course_department', 'point_of_contact'):
            if field not in request.extra_fields:
                save = True
                request.extra_fields[field] = ''
                if dry_run:
                    print(f'Added empty "{field}" to extra_fields for {request}')
        if save and not dry_run:
            request.save()

    def handle(self, *args, **options):
        if options['all'] or not any((options['state'], options['extra_fields'])):
            options['state'] = True
            options['extra_fields'] = True
        dry_run = options['dry_run']

        if options['state']:
            for request in SavioProjectAllocationRequest.objects.all():
                if ComputingAllowance(request.computing_allowance) \
                                        .requires_memorandum_of_understanding():
                    self.add_notified_to_state(request, dry_run)
            for request in AllocationAdditionRequest.objects.all():
                self.add_notified_to_state(request, dry_run)
            for request in SecureDirRequest.objects.all():
                self.add_notified_to_state(request, dry_run)
        if options['extra_fields']:
            for request in SavioProjectAllocationRequest.objects.all():
                if ComputingAllowance(request.computing_allowance) \
                                                            .is_instructional():
                    self.add_ica_extra_fields(request, dry_run)
