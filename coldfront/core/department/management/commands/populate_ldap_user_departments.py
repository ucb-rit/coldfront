from django.core.management import BaseCommand
from django.contrib.auth.models import User
from coldfront.core.department.utils.ldap import fetch_and_set_user_departments
'''
A command that populates every PI's authoritative departments if found via LDAP
'''

class Command(BaseCommand):
    help = 'Populates every users authoritative departments if found via LDAP'

    def handle(self, *args, **options):
        for user in User.objects.select_related('userprofile').all():
            user_profile = user.userprofile
            fetch_and_set_user_departments(user, user_profile)