from django.core.management import BaseCommand
from coldfront.core.department.models import Department
from coldfront.core.department.utils.ldap import LDAP_URL
from coldfront.core.department.utils.ldap import DEPARTMENT_OU
from ldap3 import Connection
import logging


class Command(BaseCommand):

    help = 'Fetches departments from LDAP and sets them in the database'
    logger = logging.getLogger(__name__)

    def handle(self, *args, **options):
        department, created = Department.objects.get_or_create(
                    code='OTH', name='Other')
        if created:
            self.logger.info(f'Created department {department.pk}, Other (OTH)')
        # auto_range=True is needed for large searches
        conn = Connection(LDAP_URL, auto_bind=True, auto_range=True)
        conn.search(DEPARTMENT_OU,
                '(berkeleyEduOrgUnitHierarchyString=*-*-*-*)',
                attributes=['berkeleyEduOrgUnitHierarchyString', 'description'])
        
        for entry in conn.entries[1:]:
            hierarchy = entry.berkeleyEduOrgUnitHierarchyString.value
            # filter L4 hierarchies
            if hierarchy.count('-') == 3:
                department, created = Department.objects.get_or_create(
                    code=hierarchy.split('-')[3], name=entry.description.value)
                if created:
                    self.logger.info(f'Created department {department.pk}, '
                                f'{department.name} ({department.code})')