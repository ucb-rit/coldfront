from django.core.management import BaseCommand
from coldfront.core.department.models import Department
from coldfront.core.utils.ldap import LDAP_URL
from coldfront.core.utils.ldap import DEPARTMENT_OU

from ldap3 import Connection

class Command(BaseCommand):
    def handle(self, *args, **options):
        # auto_range=True is needed for large searches
        conn = Connection(LDAP_URL, auto_bind=True, auto_range=True)
        conn.search(DEPARTMENT_OU,
                '(berkeleyEduOrgUnitHierarchyString=*-*-*-*)',
                attributes=['berkeleyEduOrgUnitHierarchyString', 'description'])
        
        for entry in conn.entries[1:]:
            hierarchy = entry.berkeleyEduOrgUnitHierarchyString.value
            # filter L4 hierarchies
            if hierarchy.count('-') == 3:
                Department.objects.get_or_create(code=hierarchy.split('-')[3],
                        name=entry.description.value)