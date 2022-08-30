from coldfront.core.allocation.models import AccountDeletionRequest, \
    AccountDeletionRequestStatusChoice

from django.core.management.base import BaseCommand

import logging

from coldfront.core.utils.common import utc_now_offset_aware

"""An admin command that dequeues AccountDeletionRequests whose expiration
 dates have passed."""


class Command(BaseCommand):
    help = 'Dequeues AccountDeletionRequests whose expiration dates have ' \
           'passed. Sets the requests status to Ready.'
    logger = logging.getLogger(__name__)

    def handle(self, *args, **options):
        """
        Dequeues AccountDeletionRequests whose expiration dates have
        passed. Sets the requests status to Ready
        """

        requests = \
            AccountDeletionRequest.objects.filter(
                status__name='Queued',
                expiration__lte=utc_now_offset_aware())

        num_requests = 0
        for request in requests:
            ready_status = \
                AccountDeletionRequestStatusChoice.objects.get(name='Ready')
            request.status = ready_status
            request.save()
            num_requests += 1

        message = f'Dequeued {num_requests} AccountDeletionRequests.'
        self.stdout.write(self.style.SUCCESS(message))
