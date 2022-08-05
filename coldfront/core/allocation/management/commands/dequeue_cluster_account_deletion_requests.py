from coldfront.core.allocation.models import ClusterAcctDeletionRequest, \
    ClusterAcctDeletionRequestStatusChoice

from django.core.management.base import BaseCommand

import logging

from coldfront.core.utils.common import utc_now_offset_aware

"""An admin command that dequeues ClusterAcctDeletionRequests whose expiration
 dates have passed."""


class Command(BaseCommand):
    help = 'Dequeues ClusterAcctDeletionRequests whose expiration dates have ' \
           'passed. Sets the requests status to Ready.'
    logger = logging.getLogger(__name__)

    def handle(self, *args, **options):
        """
        Dequeues ClusterAcctDeletionRequests whose expiration dates have
        passed. Sets the requests status to Ready
        """

        requests = \
            ClusterAcctDeletionRequest.objects.filter(
                status__name='Queued',
                expiration__lte=utc_now_offset_aware())

        num_requests = 0
        for request in requests:
            ready_status = \
                ClusterAcctDeletionRequestStatusChoice.objects.get(name='Ready')
            request.status = ready_status
            request.save()
            num_requests += 1

        message = f'Dequeued {num_requests} ClusterAcctDeletionRequests.'
        self.stdout.write(self.style.SUCCESS(message))
