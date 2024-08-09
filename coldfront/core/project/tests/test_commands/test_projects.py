from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.core.management import CommandError
from django.contrib.auth.models import User

from coldfront.api.statistics.utils import create_project_allocation

from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.project.tests.test_commands.test_service_units_base import TestSUBase
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.resource.models import Resource
from coldfront.core.resource.models import ResourceAttributeType
from coldfront.core.resource.models import TimedResourceAttribute
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.common import display_time_zone_current_date
from coldfront.core.utils.tests.test_base import enable_deployment


class TestProjectsBase(TestSUBase):
    """A base class for tests of the projects management command."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._command = ProjectsCommand()


class TestProjectsCreate(TestProjectsBase):
    """A class for testing the 'create' subcommand of the 'projects'
    management command."""

    # TODO
    pass


class TestProjectsRenew(TestProjectsBase):
    """A class for testing the 'renew' subcommand of the 'projects'
    management command."""

    @enable_deployment('BRC')
    def setUp(self):
        super().setUp()

        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

        self._ica_computing_allowance = ComputingAllowance(
            Resource.objects.get(name=BRCAllowances.ICA))
        computing_allowance_interface = ComputingAllowanceInterface()
        project_name_prefix = computing_allowance_interface.code_from_name(
            self._ica_computing_allowance.get_name())

        # An arbitrary number of service units to grant to ICAs in these tests.
        self._ica_num_service_units = Decimal('1000000.00')

        self._set_up_allocation_periods()

        # Create an inactive project and make self.user the PI
        self.project_name = f'{project_name_prefix}project'
        inactive_project_status = ProjectStatusChoice.objects.get(
            name='Inactive')
        inactive_project = Project.objects.create(
            name=self.project_name,
            title=self.project_name,
            status=inactive_project_status)

        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        ProjectUser.objects.create(
            project=inactive_project,
            role=pi_role,
            status=active_project_user_status,
            user=self.user)

        accounting_allocation_objects = create_project_allocation(
            inactive_project, settings.ALLOCATION_MIN)
        self.service_units_attribute = \
            accounting_allocation_objects.allocation_attribute

    def _assert_project_inactive(self, project_name):
        """Assert that a project has the Inactive status."""
        still_inactive_proj = Project.objects.get(name=project_name)
        self.assertEqual(
            still_inactive_proj.status,
            ProjectStatusChoice.objects.get(name='Inactive'))

    def _set_up_allocation_periods(self):
        """Create AllocationPeriods to potentially renew under."""
        # Delete existing ICA AllocationPeriods.
        AllocationPeriod.objects.filter(
            self._ica_computing_allowance.get_period_filters()).delete()

        today = display_time_zone_current_date()
        year = today.year

        self.past_ica_period = AllocationPeriod.objects.create(
            name=f'Spring Semester {year}',
            start_date=today - timedelta(days=100),
            end_date=today - timedelta(days=1))
        self.current_ica_period = AllocationPeriod.objects.create(
            name=f'Summer Sessions {year}',
            start_date=today - timedelta(days=50),
            end_date=today + timedelta(days=50))
        self.future_ica_period = AllocationPeriod.objects.create(
            name=f'Fall Semester {year + 1}',
            start_date=today + timedelta(days=1),
            end_date=today + timedelta(days=100))

        ica_periods = (
            self.past_ica_period,
            self.current_ica_period,
            self.future_ica_period,
        )
        for period in ica_periods:
            self._set_service_units_to_be_allocated_for_period(
                self._ica_computing_allowance, period,
                self._ica_num_service_units)

    def _set_service_units_to_be_allocated_for_period(self, computing_allowance,
                                                      allocation_period,
                                                      num_service_units):
        """Define the number of service units that should be granted to
        as part of the given ComputingAllowance under the given
        AllocationPeriod."""
        assert isinstance(computing_allowance, ComputingAllowance)
        assert isinstance(allocation_period, AllocationPeriod)
        assert isinstance(num_service_units, Decimal)
        resource_attribute_type = ResourceAttributeType.objects.get(
            name='Service Units')
        TimedResourceAttribute.objects.update_or_create(
            resource_attribute_type=resource_attribute_type,
            resource=computing_allowance.get_resource(),
            start_date=allocation_period.start_date,
            end_date=allocation_period.end_date,
            defaults={
                'value': str(num_service_units),
            })

    @enable_deployment('BRC')
    def test_dry_run(self):
        """Test that the request would be successful but the dry run
        ensures that the project is not updated."""
        project = Project.objects.get(name=self.project_name)
        self.assertEqual(project.status, 
                         ProjectStatusChoice.objects.get(name='Inactive'))
        output, error = self._command.renew(
            self.project_name, self.current_ica_period, self.user.username,
            self.user.username, dry_run=True)
        
        self.assertFalse(error)

        self.assertIn('Would renew', output)
        self.service_units_attribute.refresh_from_db()
        self.assertEqual(
            Decimal(self.service_units_attribute.value),
            settings.ALLOCATION_MIN)

    @enable_deployment('BRC')
    def test_success(self):
        """Test that a successful request updates a project's status
        to 'Active' and the service units to the correct amount."""
        project = Project.objects.get(name=self.project_name)
        self.assertEqual(
            project.status,
            ProjectStatusChoice.objects.get(name='Inactive'))

        output, error = self._command.renew(
            self.project_name, self.current_ica_period, self.user.username,
            self.user.username)

        self.assertFalse(error)
        now_active_proj = Project.objects.get(name=self.project_name)
        self.assertEqual(
            now_active_proj.status,
            ProjectStatusChoice.objects.get(name='Active'))
        self.service_units_attribute.refresh_from_db()
        self.assertEqual(
            Decimal(self.service_units_attribute.value),
            self._ica_num_service_units)

        request = AllocationRenewalRequest.objects.get(
            requester=self.user,
            pi=self.user,
            pre_project=project)
        self.assertEqual(
            AllocationRenewalRequestStatusChoice.objects.get(name='Complete'),
            request.status)
        # TODO: Also test:
        #  That only a processing email is sent

    @enable_deployment('BRC')
    def test_validate_project(self):
        """Test that, if the project is invalid, the command raises an
        error, and does not proceed."""
        project = Project.objects.get(name=self.project_name)
        self.assertEqual(
            project.status, ProjectStatusChoice.objects.get(name='Inactive'))

        with self.assertRaises(CommandError) as cm:
            self._command.renew(
                'invalid project name', self.current_ica_period,
                self.user.username, self.user.username)
        self.assertIn('A Project with name', str(cm.exception))
        self._assert_project_inactive(self.project_name)
        self.service_units_attribute.refresh_from_db()
        self.assertEqual(
            Decimal(self.service_units_attribute.value),
            settings.ALLOCATION_MIN)

    @enable_deployment('BRC')
    def test_validate_computing_allowance_non_renewable(self):
        """Test that computing allowances that cannot be renewed fail
        correctly (e.g., Recharge, Condo)."""
        computing_allowance_interface = ComputingAllowanceInterface()
        non_renewable_resources = [BRCAllowances.CO, BRCAllowances.RECHARGE]
        for resource_name in non_renewable_resources:
            computing_allowance = ComputingAllowance(
                Resource.objects.get(name=resource_name))
            assert not computing_allowance.is_renewable()
            project_name_prefix = computing_allowance_interface.code_from_name(
                computing_allowance.get_name())
            project_name = project_name_prefix + 'testproject'
            Project.objects.create(
                name=project_name,
                title=project_name,
                status=ProjectStatusChoice.objects.get(name='Inactive'))

            with self.assertRaises(CommandError) as cm:
                self._command.renew(
                    project_name, self.current_ica_period,
                    self.user.username, self.user.username)
            self.assertIn('is not renewable', str(cm.exception))
            self._assert_project_inactive(project_name)

    # TODO: Retire this test case once support for these allowances has been
    #  added.
    @enable_deployment('BRC')
    def test_validate_computing_allowance_one_per_pi(self):
        """Test that computing allowances which a PI may only have one
        of fail correctly."""
        computing_allowance_interface = ComputingAllowanceInterface()
        one_per_pi_resources = [BRCAllowances.FCA, BRCAllowances.PCA]
        for resource_name in one_per_pi_resources:
            computing_allowance = ComputingAllowance(
                Resource.objects.get(name=resource_name))
            assert computing_allowance.is_one_per_pi()
            project_name_prefix = computing_allowance_interface.code_from_name(
                computing_allowance.get_name())
            project_name = project_name_prefix + 'testproject'
            Project.objects.create(
                name=project_name,
                title=project_name,
                status=ProjectStatusChoice.objects.get(name='Inactive'))

            with self.assertRaises(CommandError) as cm:
                self._command.renew(
                    project_name, self.current_ica_period,
                    self.user.username, self.user.username)
            self.assertIn('not currently supported', str(cm.exception))
            self._assert_project_inactive(project_name)

    @enable_deployment('BRC')
    def test_validate_requester(self):
        """Test that requesters who do not exist, or are not an active
        manager/PI fail correctly."""
        project = Project.objects.get(name=self.project_name)
        self.assertEqual(
            project.status, ProjectStatusChoice.objects.get(name='Inactive'))

        # Requester who is not manager/PI is invalid.
        invalid_requester = User.objects.create(
            email='invalid@gmail.com',
            first_name='invalid',
            last_name='invalid',
            username='invalid_requester'
        )
        ProjectUser.objects.create(
            project=project,
            role=ProjectUserRoleChoice.objects.get(name='User'),
            status=ProjectUserStatusChoice.objects.get(name='Active'),
            user=invalid_requester)

        # Requester who is removed from project is invalid, even if Manager/PI
        removed_requester = User.objects.create(
            email='removed@gmail.com',
            first_name='removed',
            last_name='removed',
            username='removed_requester'
        )
        ProjectUser.objects.create(
            project=project,
            role=ProjectUserRoleChoice.objects.get(name='Manager'),
            status=ProjectUserStatusChoice.objects.get(name='Removed'),
            user=removed_requester)

        invalid_usernames = [invalid_requester.username,
                             removed_requester.username]
        for invalid_username in invalid_usernames:
            with self.assertRaises(CommandError) as cm:
                self._command.renew(
                    project.name, self.current_ica_period,
                    self.user.username, invalid_username)
            self.assertIn(
                f'Requester {invalid_username} is not an active member',
                str(cm.exception))
            self._assert_project_inactive(project.name)
            self.service_units_attribute.refresh_from_db()
            self.assertEqual(
                Decimal(self.service_units_attribute.value),
                settings.ALLOCATION_MIN)

    @enable_deployment('BRC')
    def test_validate_pi(self):
        """Test that PIs who do not exist or are not active fail
        correctly."""
        project = Project.objects.get(name=self.project_name)
        self.assertEqual(
            project.status, ProjectStatusChoice.objects.get(name='Inactive'))

        nonexistent_pi_username = 'nonexistent_pi_username'
        with self.assertRaises(CommandError) as cm:
            self._command.renew(
                project.name, self.current_ica_period,
                nonexistent_pi_username, self.user.username)
        self.assertIn(
            f'User with username "{nonexistent_pi_username}" does not exist',
            str(cm.exception))
        self._assert_project_inactive(project.name)

        # Active User (manager) who is on project but not PI
        invalid_pi = User.objects.create(
            email='manager@gmail.com',
            first_name='manager',
            last_name='manager',
            username='invalid_pi'
        )
        ProjectUser.objects.create(
            project=project,
            role=ProjectUserRoleChoice.objects.get(name='Manager'),
            status=ProjectUserStatusChoice.objects.get(name='Active'),
            user=invalid_pi)

        # Removed PI
        removed_pi = User.objects.create(
            email='removedPI@gmail.com',
            first_name='removed',
            last_name='removed',
            username='removed_pi'
        )
        ProjectUser.objects.create(
            project=project,
            role=ProjectUserRoleChoice.objects.get(
                name='Principal Investigator'),
            status=ProjectUserStatusChoice.objects.get(name='Removed'),
            user=removed_pi)
        invalid_pis = [invalid_pi.username, removed_pi.username]
        for invalid_pi in invalid_pis:
            with self.assertRaises(CommandError) as cm:
                self._command.renew(
                    project.name, self.current_ica_period,
                    invalid_pi, self.user.username)
            self.assertIn(
                f'{invalid_pi} is not an active PI',
                str(cm.exception))
            self._assert_project_inactive(project.name)
            self.service_units_attribute.refresh_from_db()
            self.assertEqual(
                Decimal(self.service_units_attribute.value),
                settings.ALLOCATION_MIN)

    @enable_deployment('BRC')
    def test_validate_allocation_period(self):
        """Test that AllocationPeriods which do not exist, are not valid
        for the given computing allowance, or are not current fail
        correctly."""
        project = Project.objects.get(name=self.project_name)
        self.assertEqual(
            project.status, ProjectStatusChoice.objects.get(name='Inactive'))

        nonexistent_alloc_period = 'I don\'t exist!'
        with self.assertRaises(CommandError) as cm:
            self._command.renew(
                project.name, nonexistent_alloc_period,
                self.user.username, self.user.username)
        self.assertIn(
            f'AllocationPeriod "{nonexistent_alloc_period}" does not exist.',
            str(cm.exception))
        self._assert_project_inactive(project.name)

        # "Allowance Year" allocation periods are not for ICA projects
        cur_allowance_year = get_current_allowance_year_period()

        with self.assertRaises(CommandError) as cm:
            self._command.renew(
                project.name, cur_allowance_year.name,
                self.user.username, self.user.username)
        self.assertIn(
            f'"{cur_allowance_year.name}" is not a valid AllocationPeriod',
            str(cm.exception))
        self._assert_project_inactive(project.name)

        # Ended allocation period
        with self.assertRaises(CommandError) as cm:
            self._command.renew(
                project.name, self.past_ica_period,
                self.user.username, self.user.username)
        self.assertIn(
            'AllocationPeriod already ended',
            str(cm.exception))
        self._assert_project_inactive(project.name)

        # Not started allocation period
        with self.assertRaises(CommandError) as cm:
            self._command.renew(
                project.name, self.future_ica_period,
                self.user.username, self.user.username)
        self.assertIn(
            'AllocationPeriod does not start until',
            str(cm.exception))
        self._assert_project_inactive(project.name)

        self.service_units_attribute.refresh_from_db()
        self.assertEqual(
            Decimal(self.service_units_attribute.value),
            settings.ALLOCATION_MIN)


class ProjectsCommand(object):
    """A wrapper class over the 'projects' management command."""

    command_name = 'projects'

    def call_subcommand(self, name, *args):
        """Call the subcommand with the given name and arguments. Return
        output written to stdout and stderr."""
        out, err = StringIO(), StringIO()
        args = [self.command_name, name, *args]
        kwargs = {'stdout': out, 'stderr': err}
        call_command(*args, **kwargs)
        return out.getvalue(), err.getvalue()

    def renew(self, name, allocation_period, pi_username, requester_username,
              **flags):
        """Call the 'renew' subcommand with the given positional arguments."""
        args = [
            'renew', name, allocation_period, pi_username, requester_username]
        self._add_flags_to_args(args, **flags)
        return self.call_subcommand(*args)

    @staticmethod
    def _add_flags_to_args(args, **flags):
        """Given a list of arguments to the command and a dict of flag
        values, add the latter to the former."""
        for key in ('dry_run', 'ignore_invalid'):
            if flags.get(key, False):
                args.append(f'--{key}')
