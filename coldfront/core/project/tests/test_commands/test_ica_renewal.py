from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.core.management import CommandError

from django.db.models import Q

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
from coldfront.core.utils.common import utc_now_offset_aware


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
        
        valid_alloc_periods = AllocationPeriod.objects.filter(Q(name__startswith="Fall") | 
                                        Q(name__startswith="Summer") | 
                                        Q(name__startswith="Spring"), 
                                        start_date__lt=utc_now_offset_aware(), 
                                        end_date__gt=utc_now_offset_aware())
        self.allocation_period = valid_alloc_periods[0]
        
        self.num_service_units = Decimal(
            computing_allowance_interface.service_units_from_name(
                computing_allowance.name, is_timed=True, 
                allocation_period=self.allocation_period))
        
        # Create an inactive project and make self.user the PI
        self.project_name = f'{project_name_prefix}project'
        inactive_project_status = ProjectStatusChoice.objects.get(name='Inactive')
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
        
        self.existing_service_units = Decimal('0.00')
        accounting_allocation_objects = create_project_allocation(
            inactive_project, self.existing_service_units)
        self.compute_allocation = accounting_allocation_objects.allocation
        self.service_units_attribute = \
            accounting_allocation_objects.allocation_attribute
        
        self.command = RenewalCommand()

    def test_renew_dry_run(self):
        """Test that the request would be successful but the dry run
        ensures that the the project is not updated."""
        project = Project.objects.get(name=self.project_name)
        self.assertEqual(project.status, 
                         ProjectStatusChoice.objects.get(name='Inactive'))
        output, error = self.command.renew(self.project_name, self.user.username,
                            self.allocation_period, self.user.username, dry_run=True)
        
        self.assertFalse(error)
        
        self.assertIn('Would renew', output)
        self.service_units_attribute.refresh_from_db()
        self.assertEqual(Decimal(self.service_units_attribute.value), Decimal('0.0'))

    def test_renew_inactive_to_active(self):
        """Test that a successful request updates a project's status
        to 'Active' and the service units to the correct amount."""
        project = Project.objects.get(name=self.project_name)
        self.assertEqual(project.status, 
                         ProjectStatusChoice.objects.get(name='Inactive'))

        output, error = self.command.renew(self.project_name, self.user.username,
                            self.allocation_period, self.user.username)
        
        self.assertFalse(error)
        now_active_proj = Project.objects.get(name=self.project_name)
        self.assertEqual(now_active_proj.status, 
                         ProjectStatusChoice.objects.get(name='Active'))
        self.service_units_attribute.refresh_from_db()
        self.assertEqual(Decimal(self.service_units_attribute.value), self.num_service_units)

    def test_renew_fail_not_active(self):
        """Test that an invalid request does not update the status
        or service units of a project."""
        project = Project.objects.get(name=self.project_name)
        self.assertEqual(project.status, 
                         ProjectStatusChoice.objects.get(name='Inactive'))

        with self.assertRaises(CommandError) as cm:
            self.command.renew("invalid project name", self.user.username,
                            self.allocation_period, self.user.username)
        self.assertIn("The project with name", str(cm.exception))
        still_inactive_proj = Project.objects.get(name=self.project_name)
        self.assertEqual(still_inactive_proj.status, 
                         ProjectStatusChoice.objects.get(name='Inactive'))
        self.service_units_attribute.refresh_from_db()
        self.assertEqual(Decimal(self.service_units_attribute.value), Decimal('0.0'))
        

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