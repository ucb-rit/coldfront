import logging

from django.core.management import BaseCommand

from coldfront.core.utils.common import add_argparse_dry_run_argument

from coldfront.plugins.departments.models import Department
from coldfront.plugins.departments.utils.data_sources import fetch_departments


class Command(BaseCommand):

    help = (
        'Fetch department data from the configured data source, and '
        'create Departments in the database.')
    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        add_argparse_dry_run_argument(parser)
    
    def log(self, message, dry_run):
        if not dry_run:
            self.logger.info(message)
        self.stdout.write(self.style.SUCCESS(message))

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            department = Department()
            department.pk = '{placeholder_pk}'
            created = not Department.objects.filter(code='OTH').exists()
        else:
            department, created = Department.objects.get_or_create(
                code='OTH', name='Other')
        if created:
            message = f'Created Department {department.pk}, Other (OTH)'
            self.log(message, dry_run)

        department_entries = fetch_departments()
        for code, name in department_entries:
            if dry_run:
                created = not Department.objects.filter(code=code).exists()
                department.name = name
                department.code = code
            else:
                department, created = Department.objects.get_or_create(
                    name=name, code=code)
            if created:
                message = f'Created Department {department.pk}, {department}'
                self.log(message, dry_run)
