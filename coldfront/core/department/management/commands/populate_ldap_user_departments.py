from django.core.management import BaseCommand
from django.contrib.auth.models import User
from coldfront.core.department.utils.ldap import fetch_and_set_user_departments
from coldfront.core.utils.common import add_argparse_dry_run_argument
import logging

class Command(BaseCommand):

    help = 'Populates every users authoritative departments if found via LDAP'

    def add_arguments(self, parser):
        add_argparse_dry_run_argument(parser)

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        for user in User.objects.select_related('userprofile').all():
            userprofile = user.userprofile
            fetch_and_set_user_departments(user, userprofile, dry_run)