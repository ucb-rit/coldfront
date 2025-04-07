from decimal import Decimal

from bs4 import BeautifulSoup

from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse

from coldfront.api.statistics.utils import create_project_allocation

from coldfront.core.allocation.models import AllocationUserAttribute

from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRemovalRequest
from coldfront.core.project.models import ProjectUserRemovalRequestStatusChoice
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils_.new_project_user_utils import NewProjectUserRunnerFactory
from coldfront.core.project.utils_.new_project_user_utils import NewProjectUserSource

from coldfront.core.utils.tests.test_base import TestBase


class TestHomeBase(TestBase):
    """A base class for testing functionality on the home view."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.client.login(username=self.user.username, password=self.password)


class TestProjectsList(TestHomeBase):
    """A class for testing the component for displaying the user's
    projects."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        self._pi = User.objects.create(username='pi', email='pi@email.com')

    def _get_project_cluster_access_badge_and_popup_text(self, project_name):
        """Given a Project name, return two values from the field for
        displaying the user's access to the project on the cluster: the
        status text in the badge, and the popup text (if any). Return
        None, None if an entry for the project cannot be found.
        
        TODO: Note: The first return value currently includes
        accessibility text normally hidden to the user. Use .startswith
        for assertions. Improve this long term.
        """
        url = reverse('home')
        response = self.client.get(url)
        html = response.content.decode('utf-8')

        soup = BeautifulSoup(html, 'html.parser')

        h3 = soup.find('h3', string='My BRC Cluster Projects »')
        if not h3:
            self.fail('Could not locate HTML tag for parsing.')

        table = h3.find_next('table')
        if not table:
            self.fail('Could not locate HTML tag for parsing.')

        tbody = table.find('tbody')
        if not tbody:
            self.fail('Could not locate HTML tag for parsing.')

        rows = tbody.find_all('tr')
        for row in rows:
            row_data = []
            for i, column in enumerate(row.find_all('td')):
                cell_text = column.get_text(strip=True)
                if i == 0 and cell_text != project_name:
                    continue
                if i == 2:
                    popup = column.find('a', {'data-toggle': 'popover'})
                    if popup:
                        popup_text = popup.get('data-content')
                    else:
                        popup_text = ''
                    cell_data = (cell_text, popup_text)
                else:
                    cell_data = cell_text
                row_data.append(cell_data)
            return row_data[2]

        return None, None

    def test_project_cluster_access_badges(self):
        """Test that the expected badge for indicating access to the
        project on the cluster is displayed."""
        # Create a project named fc_test.
        project_name = 'fc_test'
        fc_test = self.create_active_project_with_pi(project_name, self._pi)

        # Create a compute allocation for the project.
        num_service_units = Decimal(settings.ALLOCATION_MAX)
        create_project_allocation(fc_test, num_service_units)

        # Add the user to fc_test.
        user_role = ProjectUserRoleChoice.objects.get(name='User')
        active_status = ProjectUserStatusChoice.objects.get(name='Active')
        project_user_obj = ProjectUser.objects.create(
            project=fc_test,
            user=self.user,
            role=user_role,
            status=active_status)

        # Request cluster access for the user under fc_test.
        runner_factory = NewProjectUserRunnerFactory()
        new_project_user_runner = runner_factory.get_runner(
            project_user_obj, NewProjectUserSource.ADDED)
        new_project_user_runner.run()

        # "Pending - Add" --> "Pending"
        badge_text, _ = self._get_project_cluster_access_badge_and_popup_text(
            project_name)
        self.assertTrue(badge_text.startswith('Pending'))

        # Manually update the status and assert that the badge text is expected.
        cluster_account_status = AllocationUserAttribute.objects.get(
            allocation_user__user=self.user,
            allocation_attribute_type__name='Cluster Account Status')

        # "Denied" --> "Denied"
        cluster_account_status.value = 'Denied'
        cluster_account_status.save()

        badge_text, _ = self._get_project_cluster_access_badge_and_popup_text(
            project_name)
        self.assertTrue(badge_text.startswith('Denied'))

        # "Active" --> "Active"
        cluster_account_status.value = 'Active'
        cluster_account_status.save()

        badge_text, _ = self._get_project_cluster_access_badge_and_popup_text(
            project_name)
        self.assertTrue(badge_text.startswith('Active'))

        # None --> "No Access"
        cluster_account_status.delete()

        badge_text, _ = self._get_project_cluster_access_badge_and_popup_text(
            project_name)
        self.assertTrue(badge_text.startswith('No Access'))

        # Has a pending removal request --> "Pending Removal"
        project_user = ProjectUser.objects.get(project=fc_test, user=self.user)
        pending_status = ProjectUserRemovalRequestStatusChoice.objects.get(
            name='Pending')
        ProjectUserRemovalRequest.objects.create(
            project_user=project_user,
            requester=self.user,
            status=pending_status)

        badge_text, _ = self._get_project_cluster_access_badge_and_popup_text(
            project_name)
        self.assertTrue(badge_text.startswith('Pending Removal'))
