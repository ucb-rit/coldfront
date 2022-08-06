import logging
import sys

from tqdm import tqdm

from django.contrib.auth.models import User
from django.core.management import BaseCommand, CommandError
from django.conf import settings

from coldfront.core.allocation.models import ClusterAccountDeactivationRequest, \
    ClusterAccountDeactivationRequestStatusChoice
from coldfront.core.utils.common import utc_now_offset_aware


class Command(BaseCommand):
    help = 'Command to dequeue NO_VALID_USER_ACCOUNT_FEE_BILLING_ID ' \
           'ClusterAccountDeactivationRequests after ' \
           'their waiting period is complete.'
    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument('--reason',
                            help='ClusterAccountDeactivationRequestReasonChoice name to dequeue.',
                            type=str,
                            required=False)

    def handle(self, *args, **options):
        """ Dequeues ClusterAccountDeactivationRequests after their waiting
        period is complete. """

        queued_requests = ClusterAccountDeactivationRequest.objects.filter(
            status__name='Queued',
            expiration__lte=utc_now_offset_aware()
        )

        if options.get('reason', None):
            queued_requests.filter(reason__name=options.get('reason'))

        ready_status = \
            ClusterAccountDeactivationRequestStatusChoice.objects.get(name='Ready')
        for request in queued_requests:
            request.status = ready_status
            request.save()

        message = f'{queued_requests.count()} ' \
                  f'ClusterAccountDeactivationRequests dequeued.'
        sys.stdout.write(self.stdout.SUCCESS(message))
