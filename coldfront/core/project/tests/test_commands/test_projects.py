from decimal import Decimal
from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.core.management import CommandError
from django.db.models import Q

from coldfront.api.statistics.utils import create_project_allocation

from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.project.tests.test_commands.test_service_units_base import TestSUBase
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.common import utc_now_offset_aware


class TestProjectsBase(TestSUBase):
    """A base class for tests of the projects management command."""
    pass


class TestProjectsCreate(TestProjectsBase):
    """A class for testing the 'create' subcommand of the 'projects'
    management command."""

    # TODO
    pass


class TestProjectsRenew(TestProjectsBase):
    """A class for testing the 'renew' subcommand of the 'projects'
    management command."""

    def setUp(self):
        super().setUp()

        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

        computing_allowance = Resource.objects.get(
            name='Instructional Computing Allowance')
        computing_allowance_interface = ComputingAllowanceInterface()
        project_name_prefix = computing_allowance_interface.code_from_name(
            computing_allowance.name)
        
        valid_alloc_periods = AllocationPeriod.objects.filter(
            Q(name__startswith='Fall') |
            Q(name__startswith='Summer') |
            Q(name__startswith='Spring'),
            start_date__lt=utc_now_offset_aware(),
            end_date__gt=utc_now_offset_aware())
        self.allocation_period = valid_alloc_periods[0]
        
        self.num_service_units = Decimal(
            computing_allowance_interface.service_units_from_name(
                computing_allowance.name, is_timed=True, 
                allocation_period=self.allocation_period))
        
        # Create an inactive project and make self.user the PI
        self.project_name = f'{project_name_prefix}project'
        inactive_project_status = ProjectStatusChoice.objects.get(
            name='Inactive')
        inactive_project = Project.objects.create(
            name=self.project_name,
            title=self.project_name,
            status=inactive_project_status
        )

        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        ProjectUser.objects.create(
            project=inactive_project,
            role=pi_role,
            status=active_project_user_status,
            user=self.user)
        
        self.existing_service_units = settings.ALLOCATION_MIN
        accounting_allocation_objects = create_project_allocation(
            inactive_project, self.existing_service_units)
        self.compute_allocation = accounting_allocation_objects.allocation
        self.service_units_attribute = \
            accounting_allocation_objects.allocation_attribute
        
        self.command = ProjectsCommand()

    def test_dry_run(self):
        """Test that the request would be successful but the dry run
        ensures that the project is not updated."""
        project = Project.objects.get(name=self.project_name)
        self.assertEqual(project.status, 
                         ProjectStatusChoice.objects.get(name='Inactive'))
        output, error = self.command.renew(
            self.project_name, self.allocation_period, self.user.username,
            self.user.username, dry_run=True)
        
        self.assertFalse(error)

        self.assertIn('Would renew', output)
        self.service_units_attribute.refresh_from_db()
        self.assertEqual(
            Decimal(self.service_units_attribute.value),
            settings.ALLOCATION_MIN)

    def test_success(self):
        """Test that a successful request updates a project's status
        to 'Active' and the service units to the correct amount."""
        project = Project.objects.get(name=self.project_name)
        self.assertEqual(project.status,
                         ProjectStatusChoice.objects.get(name='Inactive'))

        output, error = self.command.renew(
            self.project_name, self.allocation_period, self.user.username,
            self.user.username)

        self.assertFalse(error)
        now_active_proj = Project.objects.get(name=self.project_name)
        self.assertEqual(now_active_proj.status,
                         ProjectStatusChoice.objects.get(name='Active'))
        self.service_units_attribute.refresh_from_db()
        self.assertEqual(
            Decimal(self.service_units_attribute.value),
            self.num_service_units)

        # TODO: Also test:
        #  That a request gets created and it's in the "Complete" state
        #  That only a processing email is sent

    def test_validate_project(self):
        """Test that, if the project is invalid, the command raises an
        error, and does not proceed."""
        project = Project.objects.get(name=self.project_name)
        self.assertEqual(
            project.status, ProjectStatusChoice.objects.get(name='Inactive'))

        with self.assertRaises(CommandError) as cm:
            self.command.renew(
                'invalid project name', self.allocation_period,
                self.user.username, self.user.username)
        self.assertIn('A Project with name', str(cm.exception))
        # TODO: Refactor the "not successful" checks into a block for reuse.
        still_inactive_proj = Project.objects.get(name=self.project_name)
        self.assertEqual(
            still_inactive_proj.status,
            ProjectStatusChoice.objects.get(name='Inactive'))
        self.service_units_attribute.refresh_from_db()
        self.assertEqual(
            Decimal(self.service_units_attribute.value),
            settings.ALLOCATION_MIN)

    # TODO
    #   test_validate_computing_allowance
    #     ComputingAllowance isn't renewable (e.g., Recharge, Condo)
    #   test_validate_requester
    #     Requester validation: doesn't exist; isn't active manager/PI
    #   test_validate_pi
    #     PI validation: doesn't exist; isn't active PI
    #   test_validate_allocation_period
    #     AllocationPeriod doesn't exist
    #     AllocationPeriod isn't valid for project's computing allowance
    #     AllocationPeriod isn't current


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
