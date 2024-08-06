from decimal import Decimal
from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.core.management import CommandError
from django.db.models import Q
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

        request = AllocationRenewalRequest.objects.get(
            requester=self.user,
            pi=self.user,
            pre_project=project
        )
        self.assertEqual(
            AllocationRenewalRequestStatusChoice.objects.get(name="Complete"),
            request.status)
        # TODO: Also test:
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
        self.assertProjectInactive(self.project_name)
        self.service_units_attribute.refresh_from_db()
        self.assertEqual(
            Decimal(self.service_units_attribute.value),
            settings.ALLOCATION_MIN)
    
    def test_validate_computing_allowance(self):
        """Test that computing allowance that cannot be renewed fail 
        correctly (e.g., Recharge, Condo)."""
        
        non_renewable_resources = ['Condo Allocation', 'Recharge Allocation']
        computing_allowance_interface = ComputingAllowanceInterface()
        for resource_name in non_renewable_resources:
            computing_allowance = Resource.objects.get(
                name=resource_name)
            project_name_prefix = computing_allowance_interface.code_from_name(
                computing_allowance.name)
            project_name = project_name_prefix + "testproject"
            Project.objects.create(
                name=project_name,
                title=project_name,
                status=ProjectStatusChoice.objects.get(name='Inactive'))
            
            with self.assertRaises(CommandError) as cm:
                self.command.renew(
                    project_name, self.allocation_period,
                    self.user.username, self.user.username)
            self.assertIn('is not renewable', str(cm.exception))
            self.assertProjectInactive(project_name)
            
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
            role=ProjectUserRoleChoice.objects.get(name="User"),
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
            role=ProjectUserRoleChoice.objects.get(name="Manager"),
            status=ProjectUserStatusChoice.objects.get(name='Removed'),
            user=removed_requester)
        
        invalid_usernames = [invalid_requester.username,
                             removed_requester.username]
        for invalid_username in invalid_usernames:
            with self.assertRaises(CommandError) as cm:
                self.command.renew(
                    project.name, self.allocation_period,
                    self.user.username, invalid_username)
            self.assertIn(
                f'Requester {invalid_username} is not an active member',
                str(cm.exception))
            self.assertProjectInactive(project.name)
            self.service_units_attribute.refresh_from_db()
            self.assertEqual(
                Decimal(self.service_units_attribute.value),
                settings.ALLOCATION_MIN)
    
    def test_validate_pi(self):
        """Test that PI's who do not exist or are not active fail correctly."""

        project = Project.objects.get(name=self.project_name)
        self.assertEqual(
            project.status, ProjectStatusChoice.objects.get(name='Inactive'))
        
        nonexistant_pi_username = 'nonexistant_pi_username'
        with self.assertRaises(CommandError) as cm:
                self.command.renew(
                    project.name, self.allocation_period,
                    nonexistant_pi_username, self.user.username)
        self.assertIn(
            f'User with username "{nonexistant_pi_username}" does not exist',
            str(cm.exception))
        self.assertProjectInactive(project.name)

        # Active User (manager) who is on project but not PI
        invalid_pi = User.objects.create(
            email='manager@gmail.com',
            first_name='manager',
            last_name='manager',
            username='invalid_pi'
        )
        ProjectUser.objects.create(
            project=project,
            role=ProjectUserRoleChoice.objects.get(name="Manager"),
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
                name="Principal Investigator"),
            status=ProjectUserStatusChoice.objects.get(name='Removed'),
            user=removed_pi)
        invalid_pis = [invalid_pi.username, removed_pi.username]
        for invalid_pi in invalid_pis:
            with self.assertRaises(CommandError) as cm:
                self.command.renew(
                    project.name, self.allocation_period,
                    invalid_pi, self.user.username)
            self.assertIn(
                f'{invalid_pi} is not an active PI',
                str(cm.exception))
            self.assertProjectInactive(project.name)
            self.service_units_attribute.refresh_from_db()
            self.assertEqual(
                Decimal(self.service_units_attribute.value),
                settings.ALLOCATION_MIN)

    def test_validate_allocation_period(self):
        """Test that AllocationPeriods which do not exist, are not valid for the
        given computing allowance, or are not current fail correctly."""

        project = Project.objects.get(name=self.project_name)
        self.assertEqual(
            project.status, ProjectStatusChoice.objects.get(name='Inactive'))
        
        nonexistant_alloc_period = "I don't exist!"
        with self.assertRaises(CommandError) as cm:
                self.command.renew(
                    project.name, nonexistant_alloc_period,
                    self.user.username, self.user.username)
        self.assertIn(
            f'AllocationPeriod "{nonexistant_alloc_period}" does not exist.',
            str(cm.exception))
        self.assertProjectInactive(project.name)

        # Allowance Year allocation periods are not for ICA projects
        cur_allowance_year = get_current_allowance_year_period()

        with self.assertRaises(CommandError) as cm:
            self.command.renew(
                project.name, cur_allowance_year.name,
                self.user.username, self.user.username)
        self.assertIn(
            f'"{cur_allowance_year.name}" is not a valid AllocationPeriod',
            str(cm.exception))
        self.assertProjectInactive(project.name)

        # Non-current allocation period
        past_alloc_period = AllocationPeriod.objects.filter(
            Q(name__startswith='Fall') |
            Q(name__startswith='Summer') |
            Q(name__startswith='Spring'),
            end_date__lt=utc_now_offset_aware())[0]
        
        with self.assertRaises(CommandError) as cm:
            self.command.renew(
                project.name, past_alloc_period,
                self.user.username, self.user.username)
        self.assertIn(
            f'AllocationPeriod already ended',
            str(cm.exception))
        self.assertProjectInactive(project.name)

        self.service_units_attribute.refresh_from_db()
        self.assertEqual(
            Decimal(self.service_units_attribute.value),
            settings.ALLOCATION_MIN)

    def assertProjectInactive(self, project_name):
        """ Test that a project has Inactive status. """
        still_inactive_proj = Project.objects.get(name=project_name)
        self.assertEqual(
            still_inactive_proj.status,
            ProjectStatusChoice.objects.get(name='Inactive'))

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
