from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import CommandError
from django.core.management.base import BaseCommand
from django.db import transaction

from flags.state import flag_enabled

from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils import is_primary_cluster_project
from coldfront.core.project.utils_.new_project_user_utils import NewProjectUserRunnerFactory
from coldfront.core.project.utils_.new_project_user_utils import NewProjectUserSource
from coldfront.core.project.utils_.renewal_utils import AllocationRenewalApprovalRunner
from coldfront.core.project.utils_.renewal_utils import AllocationRenewalProcessingRunner
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils import get_primary_compute_resource_name
from coldfront.core.statistics.models import ProjectTransaction
from coldfront.core.utils.common import add_argparse_dry_run_argument
from coldfront.core.utils.common import display_time_zone_current_date
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.email.email_strategy import DropEmailStrategy

import logging


"""An admin command for managing projects."""


class Command(BaseCommand):

    help = 'Manage projects.'
    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        """Define subcommands with different functions."""
        subparsers = parser.add_subparsers(
            dest='subcommand',
            help='The subcommand to run.',
            title='subcommands')
        subparsers.required = True
        self._add_create_subparser(subparsers)

        self._add_renew_subparser(subparsers)

    def handle(self, *args, **options):
        """Call the handler for the provided subcommand."""
        subcommand = options['subcommand']
        if subcommand == 'create':
            self._handle_create(*args, **options)
        elif subcommand == 'renew':
            self._handle_renew(*args, **options)

    @staticmethod
    def _add_create_subparser(parsers):
        """Add a subparser for the 'create' subcommand."""
        parser = parsers.add_parser(
            'create',
            help=(
                'Create a project with an allocation to a particular compute '
                'resource. Note: The current use case for this is to create a '
                'project for a newly-created standalone cluster. It cannot be '
                'used to create projects under the primary cluster (e.g., '
                'Savio on BRC, Lawrencium on LRC), under a standalone '
                'cluster that (a) can have at most one project and (b) '
                'already has a project, or, for BRC, under the Vector '
                'project.'))
        parser.add_argument(
            'name', help='The name of the project to create.', type=str)
        parser.add_argument(
            'cluster_name',
            help=(
                'The name of a cluster, for which a compute resource (e.g., '
                '"{cluster_name} Compute") should exist.'))
        parser.add_argument(
            'pi_usernames',
            help=(
                'A space-separated list of usernames of users to make the '
                'project\'s PIs.'),
            nargs='+',
            type=str)
        add_argparse_dry_run_argument(parser)

    @staticmethod
    def _add_renew_subparser(parsers):
        """Add a subparser for the 'renew' subcommand."""
        parser = parsers.add_parser(
            'renew',
            help=(
                'Renew ICA projects that have the Inactive status.'
                'This command will approve and process the request.'
                ))
        
        parser.add_argument(
            'name', help='The name of the project to renew.', type=str)
        
        parser.add_argument(
            'username',
            help=(
                'The username of the user making the request.'
                'The requester should be a user for the project.'),
            type=str)
        
        parser.add_argument(
            'allocation_period',
            help=(
                'Name of the allocation period the allowance is valid for.'
            ), 
            type=str)
        
        add_argparse_dry_run_argument(parser)
        

    @staticmethod
    def _create_project_with_compute_allocation_and_pis(project_name,
                                                        compute_resource,
                                                        pi_users):
        """Create a Project with the given name, with an Allocation to
        the given compute Resource, and with the given Users as
        Principal Investigators. Return the Project.

        Some fields are set by default:
            - The Project's status is 'Active'.
            - The ProjectUsers' statuses are 'Active'.
            - The Allocation's status is 'Active'.
            - The Allocation's start_date is today.
            - The Allocation's end_date is None.
            - The Allocation has the maximum number of service units.

        TODO: When the command is generalized, allow these to be
         specified.
        """
        with transaction.atomic():
            project = Project.objects.create(
                name=project_name,
                title=project_name,
                status=ProjectStatusChoice.objects.get(name='Active'))

            project_users = []
            for pi_user in pi_users:
                project_user = ProjectUser.objects.create(
                    project=project,
                    user=pi_user,
                    role=ProjectUserRoleChoice.objects.get(
                        name='Principal Investigator'),
                    status=ProjectUserStatusChoice.objects.get(name='Active'))
                project_users.append(project_user)

            allocation = Allocation.objects.create(
                project=project,
                status=AllocationStatusChoice.objects.get(name='Active'),
                start_date=display_time_zone_current_date(),
                end_date=None)
            allocation.resources.add(compute_resource)

            num_service_units = settings.ALLOCATION_MAX
            AllocationAttribute.objects.create(
                allocation_attribute_type=AllocationAttributeType.objects.get(
                    name='Service Units'),
                allocation=allocation,
                value=str(num_service_units))

            ProjectTransaction.objects.create(
                project=project,
                date_time=utc_now_offset_aware(),
                allocation=num_service_units)

            runner_factory = NewProjectUserRunnerFactory()
            for project_user in project_users:
                runner = runner_factory.get_runner(
                    project_user, NewProjectUserSource.AUTO_ADDED,
                    email_strategy=DropEmailStrategy())
                runner.run()

            for pi_user in pi_users:
                pi_user.userprofile.is_pi = True
                pi_user.userprofile.save()

        return project

    def _handle_create(self, *args, **options):
        """Handle the 'create' subcommand."""
        cleaned_options = self._validate_create_options(options)
        project_name = cleaned_options['project_name']
        compute_resource = cleaned_options['compute_resource']
        pi_users = cleaned_options['pi_users']

        pi_users_str = (
            '[' +
            ', '.join(f'"{pi_user.username}"' for pi_user in pi_users) +
            ']')
        message_template = (
            f'{{0}} Project "{project_name}" with Allocation to '
            f'"{compute_resource.name}" Resource under PIs {pi_users_str}.')
        if options['dry_run']:
            message = message_template.format('Would create')
            self.stdout.write(self.style.WARNING(message))
            return

        try:
            self._create_project_with_compute_allocation_and_pis(
                project_name, compute_resource, pi_users)
        except Exception as e:
            message = message_template.format('Failed to create')
            self.stderr.write(self.style.ERROR(message))
            self.logger.exception(f'{message}\n{e}')
        else:
            message = message_template.format('Created')
            self.stdout.write(self.style.SUCCESS(message))
            self.logger.info(message)

    @staticmethod
    def _renew_project(project, allocation_period, requester, pi):
        pre_project = project
        post_project = project
        request_time = utc_now_offset_aware()
        status = AllocationRenewalRequestStatusChoice.objects.get(name='Under Review')
        computing_allowance = Resource.objects.get(
            name='Instructional Computing Allowance')

        request = AllocationRenewalRequest.objects.create(
            requester=requester,
            pi=pi,
            computing_allowance=computing_allowance,
            allocation_period=allocation_period,
            status=status,
            pre_project=pre_project,
            post_project=post_project,
            request_time=request_time)
        
        request.state['eligibility']['status'] = 'Approved'
        request.state['eligibility']['timestamp'] = \
            utc_now_offset_aware().isoformat()
        request.save()

        num_service_units = Decimal('200000.00')
        approval_runner = AllocationRenewalApprovalRunner(
            request, num_service_units, email_strategy=DropEmailStrategy())
        approval_runner.run()

        request.refresh_from_db()
        processing_runner = AllocationRenewalProcessingRunner(
            request, num_service_units)
        processing_runner.run()


    def _handle_renew(self, *args, **options):
        """Handle the 'renew' subcommand."""
        cleaned_options = self._validate_renew_options(options)

        project_name = options['name']
        alloc_period_name = options['allocation_period']
        username_str = options['username']

        message_template = (
            f'{{0}} Project "{project_name}" renewed for  '
            f'"{alloc_period_name}" Requested by {username_str}.')
        if options['dry_run']:
            message = message_template.format('Would create')
            self.stdout.write(self.style.WARNING(message))
            return
        
        try:
            self._renew_project(cleaned_options['project'], 
                cleaned_options['allocation_period'], cleaned_options['requester'], cleaned_options['pi'])
        except Exception as e:
            message = message_template.format('Failed to renew')
            self.stderr.write(self.style.ERROR(message))
            self.logger.exception(f'{message}\n{e}')
        else:
            message = message_template.format('Renewed')
            self.stdout.write(self.style.SUCCESS(message))
            self.logger.info(message)

    @staticmethod
    def _validate_create_options(options):
        """Validate the options provided to the 'create' subcommand.
        Raise a subcommand if any are invalid or if they violate
        business logic, else return a dict of the form:
            {
                'project_name': 'project_name',
                'compute_resource': Resource,
                'pi_users': list of Users,
            }
        """
        project_name = options['name'].lower()
        if Project.objects.filter(name=project_name).exists():
            raise CommandError(
                f'A Project with name "{project_name}" already exists.')

        cluster_name = options['cluster_name']
        lowercase_cluster_name = cluster_name.lower()
        uppercase_cluster_name = cluster_name.upper()

        # TODO: When the command is generalized, enforce business logic re:
        #  the number of certain projects a PI may have.
        pi_usernames = list(set(options['pi_usernames']))
        pi_users = []
        for pi_username in pi_usernames:
            try:
                pi_user = User.objects.get(username=pi_username)
            except User.DoesNotExist:
                raise CommandError(
                    f'User with username "{pi_username}" does not exist.')
            else:
                pi_users.append(pi_user)

        lowercase_primary_cluster_name = get_primary_compute_resource_name(
            ).replace(' Compute', '').lower()
        is_cluster_primary = (
            lowercase_cluster_name == lowercase_primary_cluster_name)
        if (is_primary_cluster_project(Project(name=project_name)) or
                is_cluster_primary):
            raise CommandError(
                'This command may not be used to create a Project under the '
                'primary cluster.')

        # On BRC, also prevent a project from being created for the Vector
        # cluster.
        if flag_enabled('BRC_ONLY'):
            # TODO: As noted in the add_accounting_defaults management command,
            #  'Vector' should be fully-uppercase in its Resource name. Update
            #  this when that is the case.
            capitalized_cluster_name = cluster_name.capitalize()
            if capitalized_cluster_name == 'Vector':
                raise CommandError(
                    f'This command may not be used to create a Project under '
                    f'the {uppercase_cluster_name} cluster.')

        try:
            compute_resource = Resource.objects.get(
                name=f'{uppercase_cluster_name} Compute')
        except Resource.DoesNotExist:
            raise CommandError(
                f'Cluster {uppercase_cluster_name} does not exist.')

        # TODO: When the command is generalized, allow the project name to
        #  differ from the cluster name (within expected bounds).
        if project_name != lowercase_cluster_name:
            raise CommandError(
                f'This command may not be used to create a Project whose name '
                f'differs from the cluster name.')

        return {
            'project_name': project_name,
            'compute_resource': compute_resource,
            'pi_users': pi_users,
        }

    @staticmethod
    def _validate_renew_options(options):
        """Validate the options provided to the 'renew' subcommand.
        Raise a subcommand if any are invalid or if they violate
        business logic, else return a dict of the form:
            {
                'project': Project,
                'requester': User,
                'pi': User,
                'allocation_period': AllocationPeriod,
            }
        """

        input_username = options['username']
        requester = None
        try:
            requester = User.objects.get(username=input_username)
        except User.DoesNotExist:
            raise CommandError(
                f'User with username "{input_username}" does not exist.')

        project_name = options['name'].lower()
        if not project_name.startswith("ic_"):
            raise CommandError(
                f'The project with name "{project_name}" is not an ICA.'
            )
        
        project = None
        pi = None
        try:
            project = Project.objects.get(name=project_name)
        except Project.DoesNotExist:
            raise CommandError(
                f'A Project with name "{project_name}" does not exist.')
        
        if not ProjectUser.objects.filter(project=project, user=requester).exists():
            raise CommandError(
                f'Requester is not a user for the project "{project_name}".')

        try:
            # For ICA projects, there should be only one Principal Investigator
            pi = ProjectUser.objects.get(
                project=project, 
                role=ProjectUserRoleChoice.objects.get(
                    name='Principal Investigator')
                ).user
        except ProjectUser.DoesNotExist:
            raise CommandError(
                f'Unable to find the PI for "{project_name}".')
        
        input_allocation_period = options['allocation_period']
        allocation_period = None
        try:
            allocation_period = AllocationPeriod.objects.get(name=input_allocation_period)
        except AllocationPeriod.DoesNotExist:
            raise CommandError(
                f'"{input_allocation_period}" is not a valid allocation period.')
        else:
            if utc_now_offset_aware().date() > allocation_period.end_date:
                raise CommandError(
                    f'"{input_allocation_period}" already ended.')
            elif utc_now_offset_aware().date() < allocation_period.start_date:
                # TODO: Should I raise an error
                raise CommandError(
                    f'"{input_allocation_period}" has not begun yet.')
        
        return {
                'project': project,
                'requester': requester,
                'pi': pi,
                'allocation_period': allocation_period,
            }
