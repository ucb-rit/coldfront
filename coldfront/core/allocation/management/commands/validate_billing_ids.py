from django.core.management.base import BaseCommand

import logging

"""An admin command validates billing ids."""


class Command(BaseCommand):
    help = 'Validates billing ids.'
    logger = logging.getLogger(__name__)

    def handle(self, *args, **options):
        pass
