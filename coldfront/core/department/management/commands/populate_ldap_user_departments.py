from django.core.management import BaseCommand
from django.contrib.auth.models import User
from coldfront.core.department.utils.ldap import fetch_and_set_user_departments
'''
A command that populates every PI's authoritative departments if found via LDAP
'''

class Command(BaseCommand):
    def handle(self, *args, **options):
        for pi in User.objects.select_related('userprofile').all():
            pi_profile = pi.userprofile
            fetch_and_set_user_departments(pi, pi_profile)