import logging

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.utils.module_loading import import_string

from ...conf import settings
from ...utils.data_sources.backends.cached import CachedDataSourceBackend


"""An admin command that refreshes the cache of hardware procurements,
if enabled."""


class Command(BaseCommand):

    help = (
        'Refresh the cache of hardware procurements. This command will fail if '
        'the cached data source backend is not installed.')

    logger = logging.getLogger(__name__)

    def handle(self, *args, **options):
        data_source_config = settings.DATA_SOURCE_CONFIG

        data_source_class = import_string(data_source_config['DATA_SOURCE'])
        if data_source_class != CachedDataSourceBackend:
            raise CommandError('The cache is not enabled.')

        data_source = CachedDataSourceBackend(**data_source_config['OPTIONS'])
        data_source.clear_cache()
        data_source.populate_cache_if_needed()

        self.stdout.write(self.style.SUCCESS('Cache refreshed.'))
