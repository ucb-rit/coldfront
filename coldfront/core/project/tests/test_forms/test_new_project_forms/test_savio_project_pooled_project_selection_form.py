from django.core.exceptions import ImproperlyConfigured

from flags.state import flag_enabled

from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectPooledProjectSelectionForm
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.constants import LRCAllowances
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.tests.test_base import TestBase


class TestSavioProjectPooledProjectSelectionForm(TestBase):
    """A class for testing SavioProjectPooledProjectSelectionForm."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

    def test_inactive_projects_not_included_in_project_field(self):
        """Test that Projects with the 'Inactive' status are not
        included in the choices for the 'project' field."""
        computing_allowance_interface = ComputingAllowanceInterface()
        if flag_enabled('BRC_ONLY'):
            computing_allowance_name = BRCAllowances.FCA
        elif flag_enabled('LRC_ONLY'):
            computing_allowance_name = LRCAllowances.PCA
        else:
            raise ImproperlyConfigured
        prefix = computing_allowance_interface.code_from_name(
            computing_allowance_name)

        active_name = f'{prefix}_active_project'
        active_status = ProjectStatusChoice.objects.get(name='Active')
        active_project = Project.objects.create(
            name=active_name, title=active_name, status=active_status)
        inactive_name = f'{prefix}_inactive_project'
        inactive_status = ProjectStatusChoice.objects.get(name='Inactive')
        Project.objects.create(
            name=inactive_name, title=inactive_name, status=inactive_status)

        form = SavioProjectPooledProjectSelectionForm(
            computing_allowance=Resource.objects.get(
                name=computing_allowance_name))
        project_field_choices = form.fields['project'].queryset
        self.assertEqual(len(project_field_choices), 1)
        self.assertEqual(project_field_choices[0], active_project)

    # TODO
