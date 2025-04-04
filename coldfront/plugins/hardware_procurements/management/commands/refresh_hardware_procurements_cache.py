import logging

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.utils.module_loading import import_string

from django_q.models import Schedule
from django_q.tasks import schedule

from ...conf import settings
from ...utils.data_sources.backends.cached import CachedDataSourceBackend


"""An admin command that refreshes the cache of hardware procurements,
if enabled."""


class Command(BaseCommand):

    help = (
        'Refresh the cache of hardware procurements, or schedule a'
        'refresh to occur at a set interval. This command will fail if '
        'the cached data source backend is not installed.')

    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument(
            '--schedule',
            action='store_true',
            default=False,
            help='Schedule this command periodically.')
        parser.add_argument(
            '--interval',
            default=60,
            help='The number of minutes between scheduled runs.',
            type=int)

    def handle(self, *args, **options):
        data_source_config = settings.DATA_SOURCE_CONFIG
        data_source_class = import_string(data_source_config['DATA_SOURCE'])
        if data_source_class != CachedDataSourceBackend:
            raise CommandError('The cache is not enabled.')

        if options['schedule']:
            self._handle_schedule(options['interval'])
        else:
            self._handle_synchronous(data_source_config)

    def _handle_schedule(self, interval):
        """Schedule a synchronous run of this command at the given
        interval, in minutes. Do nothing if there is already a schedule
        in place."""
        # Identify existing tasks by a static name, as opposed to the command
        # name, which may change.
        task_name = 'refresh_hardware_procurements_cache'
        command_name = __name__.rsplit('.', maxsplit=1)[-1]

        task_exists = Schedule.objects.filter(name=task_name).exists()
        if task_exists:
            message = (
                f'A task to refresh the cache is already scheduled, under the '
                f'name "{task_name}".')
            self.stdout.write(self.style.WARNING(message))
            return

        func = 'django.core.management.call_command'
        args = (command_name,)
        kwargs = {
            'schedule_type': 'I',
            'minutes': interval,
            'name': task_name,
        }
        schedule(func, *args, **kwargs)

        message = (
            f'Scheduled a task to refresh the cache every {interval} '
            f'minutes, under the name "{task_name}".')
        self.stdout.write(self.style.SUCCESS(message))

    def _handle_synchronous(self, data_source_config):
        """Refresh the cache."""
        data_source = CachedDataSourceBackend(**data_source_config['OPTIONS'])
        data_source.clear_cache()
        data_source.populate_cache_if_needed()

        self.stdout.write(self.style.SUCCESS('Cache refreshed.'))
