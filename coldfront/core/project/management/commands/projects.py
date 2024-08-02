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
from coldfront.core.allocation.utils import calculate_service_units_to_allocate
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
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
from coldfront.core.project.utils_.renewal_utils import set_allocation_renewal_request_eligibility
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils import get_primary_compute_resource_name
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
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
            help='Renew a PI\'s allowance under a project.')
        parser.add_argument(
            'name', help='The name of the project to renew under.', type=str)
        parser.add_argument(
            'allocation_period',
            help='The name of the AllocationPeriod to renew under.',
            type=str)
        parser.add_argument(
            'pi_username',
            help=(
                'The username of the user whose allowance should be renewed. '
                'The PI must be an active PI of the project.'),
            type=str)
        parser.add_argument(
            'requester_username',
            help=(
                'The username of the user making the request. The requester '
                'must be an active manager or PI of the project.'),
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
    def _renew_project(project, allocation_period, requester, pi,
                       computing_allowance, num_service_units):
        """Renew the computing allowance of the given PI under the given
        project for the given AllocationPeriod, as requested by the
        given User and granting the given number of service units.

            1. Create an AllocationRenewalRequest.
            2. Update the state of the request to prepare it for
               approval.
            3. Approve the request.
            4. Process the request.

        Assumptions:
            - The ComputingAllowance is renewable.
            - The PI is an active PI of the project.
            - The requester is an active Manager or PI of the project.
            - The allowance is being renewed under the same project
              (i.e., there is no change in pooling preferences).
            - The AllocationPeriod is current: it has started, and it
              has not ended.
        """
        pre_project = project
        post_project = project
        request_time = utc_now_offset_aware()
        status = AllocationRenewalRequestStatusChoice.objects.get(
            name='Under Review')

        with transaction.atomic():
            request = AllocationRenewalRequest.objects.create(
                requester=requester,
                pi=pi,
                computing_allowance=computing_allowance.get_resource(),
                allocation_period=allocation_period,
                status=status,
                pre_project=pre_project,
                post_project=post_project,
                request_time=request_time)

            eligibility_status = 'Approved'
            eligibility_justification = ''
            set_allocation_renewal_request_eligibility(
                request, eligibility_status, eligibility_justification)

            # TODO: The command currently assumes that the period has already
            #  started. If allowing renewals for future periods:
            #   - Refactor and reuse existing logic for determining whether to
            #     run the processing runner.
            #   - Refactor ane reuse existing logic to filter out periods that
            #     are too far in the future.

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
        requester_str = options['requester_username']
        pi_str = options['pi_username']

        message_template = (
            f'{{0}} the allocation for PI "{pi_str}" under Project  '
            f'"{project_name}" for {alloc_period_name}, '
            f'requested by {requester_str}.')
        if options['dry_run']:
            message = message_template.format('Would renew')
            self.stdout.write(self.style.WARNING(message))
            return

        try:
            self._renew_project(
                cleaned_options['project'],
                cleaned_options['allocation_period'],
                cleaned_options['requester'],
                cleaned_options['pi'],
                cleaned_options['computing_allowance'],
                cleaned_options['num_service_units'])
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
                'computing_allowance': ComputingAllowance,
                'num_service_units': Decimal,
            }
        """
        project_name = options['name'].lower()
        try:
            project = Project.objects.get(name=project_name)
        except Project.DoesNotExist:
            raise CommandError(
                f'A Project with name "{project_name}" does not exist.')

        computing_allowance_interface = ComputingAllowanceInterface()
        computing_allowance = ComputingAllowance(
            computing_allowance_interface.allowance_from_project(project))
        if not computing_allowance.is_renewable():
            raise CommandError(
                f'Computing allowance "{computing_allowance.get_name()}" is '
                f'not renewable.')

        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        manager_project_user_role = ProjectUserRoleChoice.objects.get(
            name='Manager')
        pi_project_user_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')

        # The requester must be an "Active" "Manager" or "Principal
        # Investigator" of the project.
        requester_username = options['requester_username']
        try:
            requester = User.objects.get(username=requester_username)
        except User.DoesNotExist:
            raise CommandError(
                f'User with username "{requester_username}" does not exist.')
        is_requester_valid = ProjectUser.objects.filter(
            project=project, user=requester,
            role__in=[manager_project_user_role, pi_project_user_role],
            status=active_project_user_status).exists()
        if not is_requester_valid:
            raise CommandError(
                f'Requester {requester.username} is not an active member of '
                f'the project "{project_name}".')

        # The PI must be an "Active" "Principal Investigator" of the project.
        pi_username = options['pi_username']
        try:
            pi = User.objects.get(username=pi_username)
        except User.DoesNotExist:
            raise CommandError(
                f'User with username "{pi_username}" does not exist.')
        is_pi_valid = ProjectUser.objects.filter(
            project=project, user=pi, role=pi_project_user_role,
            status=active_project_user_status).exists()
        if not is_pi_valid:
            raise CommandError(
                f'{pi} is not an active PI of the project "{project_name}".')

        # The AllocationPeriod must be:
        #     (a) valid for the project's computing allowance, and
        #     (b) current.
        allocation_period_name = options['allocation_period']
        try:
            allocation_period = AllocationPeriod.objects.get(
                name=allocation_period_name)
        except AllocationPeriod.DoesNotExist:
            raise CommandError(
                f'AllocationPeriod "{allocation_period_name}" does not exist.')

        allowance_periods_q = computing_allowance.get_period_filters()
        if not allowance_periods_q:
            raise CommandError(
                f'Unexpectedly found no AllocationPeriod filters for '
                f'"{computing_allowance.get_name()}".')
        allocation_periods_for_allowance = AllocationPeriod.objects.filter(
            allowance_periods_q)
        try:
            error = (
                f'"{allocation_period_name}" is not a valid AllocationPeriod '
                f'for computing allowance "{computing_allowance.get_name()}".')
            assert allocation_period in allocation_periods_for_allowance, error
        except AssertionError as e:
            raise CommandError(e)

        try:
            allocation_period.assert_started()
            allocation_period.assert_not_ended()
        except AssertionError as e:
            raise CommandError(e)

        request_time = utc_now_offset_aware()
        num_service_units = calculate_service_units_to_allocate(
            computing_allowance, request_time,
            allocation_period=allocation_period)

        # TODO (in progress): Add business logic to ensure that the PI is
        #  allowed to have a renewal request made under them.

        return {
            'project': project,
            'requester': requester,
            'pi': pi,
            'allocation_period': allocation_period,
            'computing_allowance': computing_allowance,
            'num_service_units': num_service_units,
        }
