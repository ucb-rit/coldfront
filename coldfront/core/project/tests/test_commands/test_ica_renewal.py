from decimal import Decimal
from io import StringIO

from django.core.management import call_command

from coldfront.api.statistics.utils import create_project_allocation
from coldfront.core.project.tests.test_commands.test_service_units_base import \
    TestSUBase
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface


class TestICARenewal(TestSUBase):
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
        self.num_service_units = Decimal(
            computing_allowance_interface.service_units_from_name(
                computing_allowance.name))
        
        # Create an inactive project and make self.user the PI
        project_name = f'{project_name_prefix}project'
        inactive_project_status = ProjectStatusChoice.objects.get(name='Inactive')
        inactive_project = Project.objects.create(
            name=project_name,
            title=project_name,
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
        
        self.existing_service_units = Decimal('0.00')
        accounting_allocation_objects = create_project_allocation(
            inactive_project, self.existing_service_units)
        self.compute_allocation = accounting_allocation_objects.allocation
        self.service_units_attribute = \
            accounting_allocation_objects.allocation_attribute
        
        self.command = RenewalCommand()

    def test_renew_valid_allocation_period(self):
        """Test that 'renew' raises an error if the
        allocation period is invalid."""
        allocation_period = AllocationPeriod.objects.get(name="Fall Semester 2022")

        computing_allowance = Resource.objects.get(
            name='Instructional Computing Allowance')
        project_name_prefix = ComputingAllowanceInterface().code_from_name(
            computing_allowance.name)
        project_name = f'{project_name_prefix}project'

        output, error = self.command.renew(project_name, self.user.username, 
                            allocation_period, self.user.username)
        
        self.assertIn('AllocationPeriod already ended', output)
        
    def test_renew_updates_service_units(self):
        allocation_period = AllocationPeriod.objects.get(name="Summer Sessions 2024 - Session B")

        computing_allowance = Resource.objects.get(
            name='Instructional Computing Allowance')
        computing_allowance_interface = ComputingAllowanceInterface()
        project_name_prefix =  computing_allowance_interface.code_from_name(
            computing_allowance.name)
        project_name = f'{project_name_prefix}project'

        output, error = self.command.renew(project_name, self.user.username, 
                            allocation_period, self.user.username)

        self.assertEqual(self.num_service_units, self.existing_service_units)
        

class RenewalCommand(object):
    """A wrapper class over the 'projects' management command."""

    command_name = "projects"
    def call_subcommand(self, name, *args):
        """Call the subcommand with the given name and arguments. Return
        output written to stdout and stderr."""
        out, err = StringIO(), StringIO()
        args = [self.command_name, name, *args]
        kwargs = {'stdout': out, 'stderr': err}
        call_command(*args, **kwargs)
        return out.getvalue(), err.getvalue()
    
    def renew(self, name, username, allocation_period, pi_username, **flags):
        """Call the 'renew' subcommand with the given positional arguments."""
        args = ['renew', name, username, allocation_period, pi_username]
        self._add_flags_to_args(args, **flags)
        return self.call_subcommand(*args)

    @staticmethod
    def _add_flags_to_args(args, **flags):
        """Given a list of arguments to the command and a dict of flag
        values, add the latter to the former."""
        for key in ('dry_run', 'ignore_invalid'):
            if flags.get(key, False):
                args.append(f'--{key}')