import logging
import sys

from django.core.management import BaseCommand

from coldfront.core.allocation.models import \
    ClusterAccountDeactivationRequest, \
    ClusterAccountDeactivationRequestStatusChoice
from coldfront.core.utils.common import utc_now_offset_aware


class Command(BaseCommand):
    help = 'Command to dequeue ClusterAccountDeactivationRequests after ' \
           'their waiting period is complete.'
    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument('--reason',
                            choices=['ALL',
                                     'NO_VALID_USER_ACCOUNT_FEE_BILLING_ID',
                                     'NO_VALID_RECHARGE_USAGE_FEE_BILLING_ID'],
                            help='ClusterAccountDeactivationRequestReasonChoice'
                                 ' name to dequeue. \"All\" will dequeue '
                                 'all requests.',
                            type=str,
                            required=True)

    def handle(self, *args, **options):
        """ Dequeues ClusterAccountDeactivationRequests after their waiting
        period is complete. """

        queued_requests = ClusterAccountDeactivationRequest.objects.filter(
            status__name='Queued',
            expiration__lte=utc_now_offset_aware()
        ).order_by('pk')

        reason = options.get('reason')
        if reason != 'ALL':
            queued_requests.filter(reason__name=reason)

        dequeued_requests = []
        ready_status = \
            ClusterAccountDeactivationRequestStatusChoice.objects.get(
                name='Ready')
        for request in queued_requests:
            request.status = ready_status
            request.save()
            dequeued_requests.append(request.pk)

        message = f'Marked {queued_requests.count()} ' \
                  f'ClusterAccountDeactivationRequests as ' \
                  f'\"Ready\": {", ".join(dequeued_requests)}.'
        sys.stdout.write(self.stdout.SUCCESS(message))
