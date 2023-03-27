from django.core.management import BaseCommand
from django.contrib.auth.models import User
from coldfront.core.department.utils.ldap import fetch_and_set_user_departments
from coldfront.core.utils.common import add_argparse_dry_run_argument
import logging

class Command(BaseCommand):

    help = 'Populates every users authoritative departments if found via LDAP'

    def add_arguments(self, parser):
        parser.add_argument(
            '--only_pis',
            action='store_true',
            help='Only populate the departments of users who are PIs.')
        add_argparse_dry_run_argument(parser)

    def handle(self, *args, **options):
        only_pis = options['only_pis']
        dry_run = options['dry_run']
        users = User.objects.select_related('userprofile')
        if only_pis:
            users = users.filter(userprofile__is_pi=True)
        else:
            users = users.all()
        for user in users:
            userprofile = user.userprofile
            fetch_and_set_user_departments(user, userprofile, dry_run)