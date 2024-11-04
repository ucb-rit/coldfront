from django.contrib.auth.models import User
from django.core.management import BaseCommand

from allauth.account.models import EmailAddress

from coldfront.core.utils.common import add_argparse_dry_run_argument

from coldfront.plugins.departments.models import UserDepartment
from coldfront.plugins.departments.utils.data_sources import fetch_departments_for_user
from coldfront.plugins.departments.utils.data_sources import get_data_source
from coldfront.plugins.departments.utils.queries import create_or_update_department


class Command(BaseCommand):

    help = (
        'Fetch data about departments associated with users from the '
        'configured data source, and create UserDepartments in the database.')

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

        # TODO: Account for dry_run.

        data_source = get_data_source()

        # A mapping from Department code to the primary key of the corresponding
        # object.
        department_pk_by_code = {}

        for user in users:
            # TODO: This is going to get duplicated. Make a function.
            user_data = {
                'emails': list(
                    EmailAddress.objects.filter(
                        user=user).values_list('email', flat=True)),
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
            user_department_data = fetch_departments_for_user(
                user_data, data_source=data_source)

            for code, name in user_department_data:

                if code not in department_pk_by_code:
                    department, department_created = \
                        create_or_update_department(code, name)
                    department_pk_by_code[code] = department.pk
                department_pk = department_pk_by_code[code]

                user_department, user_department_created = \
                    UserDepartment.objects.update_or_create(
                        userprofile=user.userprofile,
                        department=department_pk,
                        defaults={
                            'is_authoritative': True,
                        })
