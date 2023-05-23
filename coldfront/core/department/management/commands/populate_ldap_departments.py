from django.core.management import BaseCommand
from coldfront.core.department.models import Department
from coldfront.core.department.utils.ldap import LDAP_URL
from coldfront.core.department.utils.ldap import DEPARTMENT_OU
from coldfront.core.utils.common import add_argparse_dry_run_argument
from ldap3 import Connection
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

        # auto_range=True is needed for large searches
        conn = Connection(LDAP_URL, auto_bind=True, auto_range=True)
        conn.search(
            DEPARTMENT_OU,
            '(berkeleyEduOrgUnitHierarchyString=*-*-*-*)',
            attributes=['berkeleyEduOrgUnitHierarchyString', 'description'])
        
        for entry in conn.entries[1:]:
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
