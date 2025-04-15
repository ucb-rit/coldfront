import csv
import json
import os

from django.contrib.auth.models import User
from django.core.management import CommandError
from django.core.management.base import BaseCommand
from django.db.models import Q

from allauth.account.models import EmailAddress

from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserStatusChoice


# TODO: Replace the export_data users subcommand with this, or have it call this.
# TODO: Incorporate departments.


class Command(BaseCommand):

    help = ''

    def add_arguments(self, parser):
        """Define subcommands with different functions."""
        subparsers = parser.add_subparsers(
            dest='subcommand',
            help='The subcommand to run.',
            title='subcommands')
        subparsers.required = True
        self._add_get_subparser(subparsers)
        self._add_list_subparser(subparsers)

    def handle(self, *args, **options):
        """Call the handler for the provided subcommand."""
        subcommand = options['subcommand']
        handler = getattr(self, f'_handle_{subcommand}')
        handler(*args, **options)

    @staticmethod
    def _add_get_subparser(parsers):
        """Add a subparser for the 'get' subcommand."""
        parser = parsers.add_parser(
            'get',
            help=('TODO'))

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--username',
            help='Get the user by username.',
            type=str)
        group.add_argument(
            '--cluster_uid',
            help='Get the user by cluster UID.',
            type=str)
        group.add_argument(
            '--email',
            help='Get the user by email.',
            type=str)

        parser.add_argument(
            '--format',
            choices=['csv', 'json'],
            default='json',
            help='Output the result in the given format.',
            type=str)

    @staticmethod
    def _add_list_subparser(parsers):
        """Add a subparser for the 'list' subcommand."""
        parser = parsers.add_parser(
            'list',
            help=('TODO'))

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--usernames_file',
            help='List users having usernames in the given file.',
            type=str)

        parser.add_argument(
            '--format',
            choices=['csv', 'json'],
            default='json',
            help='Output results in the given format.',
            type=str)

    def _handle_get(self, *args, **options):
        """Handle the 'get' subcommand."""
        try:
            if options['username']:
                username = options['username'].lower()
                user = User.objects.get(username=username)
            elif options['cluster_uid']:
                cluster_uid = options['cluster_uid']
                assert cluster_uid.isdigit()
                user = User.objects.get(userprofile__cluster_uid=cluster_uid)
            elif options['email']:
                email = options['email'].lower()
                email_address = EmailAddress.objects.get(email=email)
                user = email_address.user
            else:
                raise CommandError('Unexpected option.')
        except Exception as e:
            # TODO: This makes sense when format is CSV, but not JSON.
            identifier = (
                options['username'] or
                options['cluster_uid'] or
                options['email'] or
                '')
            self.stdout.write(identifier)
            return

        user_data = self._get_user_data(user)

        if options['format'] == 'csv':
            writer = csv.writer(self.stdout)
            row = self._to_csv(user_data)
            writer.writerow(row)
        else:
            output = json.dumps(user_data, indent=4)
            self.stdout.write(output)

    def _handle_list(self, *args, **options):
        """Handle the 'list' subcommand."""
        if options['usernames_file']:
            usernames_file = options['usernames_file']
            assert os.path.isfile(usernames_file)
        else:
            raise CommandError('Unexpected option.')

        writer = csv.writer(self.stdout)

        header = ('username', 'first_name', 'last_name', 'email', 'pis')
        writer.writerow(header)

        # TODO: Handle JSON (jsonl?).

        active_pi_data_by_project_pk = {}

        with open(usernames_file, 'r') as f:
            for username in f:
                username = username.strip()
                try:
                    user = User.objects.get(username=username)
                except User.DoesNotExist:
                    user = None

                user_data = self._get_user_data(
                    user,
                    active_pi_data_by_project_pk=active_pi_data_by_project_pk)

                row = self._to_csv(user_data)

                writer.writerow(row)

    @staticmethod
    def _get_user_data(user, active_pi_data_by_project_pk=None):
        """TODO"""
        user_data = {
            'username': '',
            'first_name': '',
            'last_name': '',
            'emails': [],
            'pis': [],
        }

        if user is None:
            return user_data

        active_pi_data_by_project_pk = active_pi_data_by_project_pk or {}

        user_data['username'] = user.username
        user_data['first_name'] = user.first_name
        user_data['last_name'] = user.last_name

        email_addresses = EmailAddress.objects.filter(user=user)
        user_emails = []
        for email_address in email_addresses.order_by('-primary'):
            email_entry = {
                'email': email_address.email,
                'primary': email_address.primary,
            }
            user_emails.append(email_entry)
        user_data['emails'] = user_emails

        ignored_project_user_status_choices = \
            ProjectUserStatusChoice.objects.filter(
                name__in=['Denied', 'Pending'])
        ignored_project_status_choices = ProjectStatusChoice.objects.filter(
            name__in=['Denied', 'New'])
        user_pis = []
        q = (
            Q(user=user) &
            ~Q(status__in=ignored_project_user_status_choices) &
            ~Q(project__status__in=ignored_project_status_choices))
        user_project_users = ProjectUser.objects.select_related(
            'project').filter(q).order_by('project__name')
        for project_user in user_project_users:
            project = project_user.project
            if project not in active_pi_data_by_project_pk:
                project_pis = []
                for pi in project.pis(active_only=True):
                    pi_entry = {
                        'project_name': project.name,
                        'pi_first_name': pi.first_name,
                        'pi_last_name': pi.last_name,
                        'pi_email': pi.email,
                    }
                    project_pis.append(pi_entry)
                active_pi_data_by_project_pk[project] = project_pis
            for pi_entry in active_pi_data_by_project_pk[project]:
                user_pis.append(pi_entry)
        user_data['pis'] = user_pis

        return user_data

    def _to_csv(output, user_data):
        """TODO"""
        username_value = user_data['username']
        first_name_value = user_data['first_name']
        last_name_value = user_data['last_name']
        email_value = user_data['emails'][0]['email']
        pi_value_entries = []
        for pi_entry in user_data['pis']:
            pi_value_entry = (
                f'({pi_entry["project_name"]}|'
                f'{pi_entry["pi_first_name"]} {pi_entry["pi_last_name"]}|'
                f'{pi_entry["pi_email"]})')
            pi_value_entries.append(pi_value_entry)
        pis_value = ';'.join(pi_value_entries)

        return (
            username_value, first_name_value, last_name_value, email_value,
            pis_value)
