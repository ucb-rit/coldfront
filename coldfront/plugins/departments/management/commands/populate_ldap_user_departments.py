from django.core.management import BaseCommand
from django.contrib.auth.models import User
from coldfront.plugins.departments.utils.queries import fetch_and_set_user_departments
from coldfront.core.utils.common import add_argparse_dry_run_argument
from coldfront.plugins.departments.models import Department


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

        l4_department_code_cache = {department.code: department.code for department in Department.objects.all()}
        for user in users:
            userprofile = user.userprofile
            l4_department_code_cache = fetch_and_set_user_departments(user, userprofile, dry_run, l4_department_code_cache)