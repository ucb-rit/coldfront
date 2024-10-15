from django.core.management import BaseCommand
from coldfront.plugins.ucb_departments.models import Department
from coldfront.plugins.ucb_departments.utils.ldap import ldap_search_all_departments
from coldfront.core.utils.common import add_argparse_dry_run_argument
import logging


class Command(BaseCommand):

    help = 'Fetches departments from LDAP and sets them in the database'
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
            created = False
            if not Department.objects.filter(code='OTH').exists():
                created = True
        else:
            department, created = Department.objects.get_or_create(
                code='OTH', name='Other')
        if created:
            self.log(
                f'Created Department {department.pk}, Other (OTH)', dry_run)

        department_entries = ldap_search_all_departments()
        for entry in department_entries:
            hierarchy = entry.berkeleyEduOrgUnitHierarchyString.value
            # filter L4 hierarchies
            if hierarchy.count('-') == 3:
                code = hierarchy.split('-')[3]
                if dry_run and not Department.objects.filter(
                        code=code).exists():
                    created = True
                    department.name = entry.description.value
                    department.code = code
                else:
                    department, created = Department.objects.get_or_create(
                        code=code, name=entry.description.value)
                if created:
                    self.log(
                        f'Created Department {department.pk}, {department}',
                        dry_run)
