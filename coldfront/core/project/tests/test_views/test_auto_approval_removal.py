from decimal import Decimal
from http import HTTPStatus

from django.contrib.messages import get_messages
from django.urls import reverse

from coldfront.api.statistics.utils import create_project_allocation
from coldfront.core.project.models import *
from coldfront.core.user.models import UserProfile
from django.contrib.auth.models import User
from django.core import mail
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import enable_deployment
from coldfront.core.utils.tests.test_base import TestBase as AllTestsBase
from django.conf import settings

from urllib.parse import urljoin


class TestBase(AllTestsBase):
    """
    Class for testing project join requests after removing
    all auto approval code
    """

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Create a requester user and multiple PI users.
        self.user1 = User.objects.create(
            email='user1@email.com',
            first_name='Normal',
            last_name='User1',
            username='user1')
        self.user1.set_password(self.password)
        self.user1.save()

        self.pi1 = User.objects.create(
            email='pi1@email.com',
            first_name='Pi1',
            last_name='User',
            username='pi1')
        self.pi1.set_password(self.password)
        self.pi1.save()
        user_profile = UserProfile.objects.get(user=self.pi1)
        user_profile.is_pi = True
        user_profile.save()

        self.pi2 = User.objects.create(
            email='pi2@email.com',
            first_name='Pi2',
            last_name='User',
            username='pi2')
        self.pi2.set_password(self.password)
        self.pi2.save()
        user_profile = UserProfile.objects.get(user=self.pi2)
        user_profile.is_pi = True
        user_profile.save()

        for user in [self.user1, self.pi1, self.pi2]:
            user_profile = UserProfile.objects.get(user=user)
            user_profile.access_agreement_signed_date = utc_now_offset_aware()
            user_profile.save()

        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')

        pi_project_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        user_project_role = ProjectUserRoleChoice.objects.get(
            name='User')

        # Create Projects.
        from coldfront.core.resource.utils_.allowance_utils.interface import \
            ComputingAllowanceInterface
        computing_allowance_interface = ComputingAllowanceInterface()
        computing_allowance = self.get_predominant_computing_allowance()
        project_name_prefix = computing_allowance_interface.code_from_name(
            computing_allowance.name)
        
        self.project1 = Project.objects.create(
            name=f'{project_name_prefix}_project1', status=active_project_status)
        create_project_allocation(self.project1, Decimal('0.00'))

        # add pis
        for pi_user in [self.pi1, self.pi2]:
            ProjectUser.objects.create(
                project=self.project1,
                user=pi_user,
                role=pi_project_role,
                status=active_project_user_status)

        # Clear the mail outbox.
        mail.outbox = []

    def get_message_strings(self, response):
        """Return messages included in the given response as a list of
        strings."""
        return [str(m) for m in get_messages(response.wsgi_request)]


class TestProjectJoinView(TestBase):
    """
    Testing class for ProjectJoinView
    """

    def setUp(self):
        """Set up test data."""
        super().setUp()

    def test_project_join_request(self):
        """
        Test that ProjectJoinView successfully creates a ProjectUser and a
        ProjectUserJoinRequest
        """
        url = reverse(
            'project-join', kwargs={'pk': self.project1.pk})
        data = {'reason': 'Testing ProjectJoinView. Testing ProjectJoinView.'}
        self.client.login(username=self.user1.username, password=self.password)
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        proj_user = ProjectUser.objects.filter(user=self.user1,
                                               project=self.project1,
                                               status__name='Pending - Add')
        self.assertTrue(proj_user.exists())
        self.assertTrue(ProjectUserJoinRequest.objects.filter(
            project_user=proj_user.first(),
            reason=data['reason']).exists())

        self.client.logout()

    def test_project_join_request_email(self):
        """
        Test that the correct email is sent to managers and
        PIs after a join request
        """
        url = reverse(
            'project-join', kwargs={'pk': self.project1.pk})
        data = {'reason': 'Testing ProjectJoinView. Testing ProjectJoinView.'}
        self.client.login(username=self.user1.username, password=self.password)
        response = self.client.post(url, data)
        self.client.logout()

        email_to_list = [proj_user.user.email for proj_user in
                         self.project1.projectuser_set.filter(
                             role__name__in=['Manager', 'Principal Investigator'],
                             status__name='Active')]

        domain = import_from_settings('CENTER_BASE_URL')
        view = reverse(
            'project-review-join-requests', kwargs={'pk': self.project1.pk})
        review_url = urljoin(domain, view)

        body_components = [
            (f'User {self.user1.first_name} {self.user1.last_name} '
             f'({self.user1.email}) has requested to join your project, '
             f'{self.project1.name} via the {settings.PORTAL_NAME} User '
             f'Portal.'),
            f'Please approve/deny this request here: {review_url}.',
        ]

        for email in mail.outbox:
            for component in body_components:
                self.assertIn(component, email.body)
            for recipient in email.to:
                self.assertIn(recipient, email_to_list)
            self.assertEqual(settings.EMAIL_SENDER, email.from_email)


class TestProjectReviewJoinRequestsView(TestBase):
    """
    Testing class for ProjectReviewJoinRequestsView
    """

    @enable_deployment('BRC')
    def setUp(self):
        """Set up test data."""
        super().setUp()
        url = reverse(
            'project-join', kwargs={'pk': self.project1.pk})
        self.data = {'reason': 'Testing ProjectJoinView. Testing ProjectJoinView.'}
        self.client.login(username=self.user1.username, password=self.password)
        response = self.client.post(url, self.data)
        self.client.logout()

    @enable_deployment('BRC')
    def test_project_join_request_view_content(self):
        """
        Test that project-review-join-requests displays correct requests
        """
        url = reverse(
            'project-review-join-requests', kwargs={'pk': self.project1.pk})
        self.client.login(username=self.pi1.username, password=self.password)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, self.user1.username)
        self.assertContains(response, self.data['reason'])

    @enable_deployment('BRC')
    def test_project_join_request_view_approve(self):
        """
        Test project-review-join-requests approval
        """
        proj_user = ProjectUser.objects.filter(user=self.user1,
                                               project=self.project1).first()

        self.assertEqual(proj_user.status.name, 'Pending - Add')

        form_data = {'userform-TOTAL_FORMS': ['1'],
                     'userform-INITIAL_FORMS': ['1'],
                     'userform-MIN_NUM_FORMS': ['0'],
                     'userform-MAX_NUM_FORMS': ['1'],
                     'userform-0-selected': ['on'],
                     'decision': ['approve']}

        url = reverse(
            'project-review-join-requests', kwargs={'pk': self.project1.pk})
        self.client.login(username=self.pi1.username, password=self.password)
        response = self.client.post(url, form_data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        proj_user.refresh_from_db()
        self.assertEqual(proj_user.status.name, 'Active')

    @enable_deployment('BRC')
    def test_project_join_request_view_deny(self):
        """
        Test project-review-join-requests approval
        """
        proj_user = ProjectUser.objects.filter(user=self.user1,
                                               project=self.project1).first()

        self.assertEqual(proj_user.status.name, 'Pending - Add')

        form_data = {'userform-TOTAL_FORMS': ['1'],
                     'userform-INITIAL_FORMS': ['1'],
                     'userform-MIN_NUM_FORMS': ['0'],
                     'userform-MAX_NUM_FORMS': ['1'],
                     'userform-0-selected': ['on'],
                     'decision': ['deny']}

        url = reverse(
            'project-review-join-requests', kwargs={'pk': self.project1.pk})
        self.client.login(username=self.pi1.username, password=self.password)
        response = self.client.post(url, form_data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        proj_user.refresh_from_db()
        self.assertEqual(proj_user.status.name, 'Denied')


class TestProjectUpdateView(TestBase):
    """
    Testing class for ProjectUpdateView
    """

    def setUp(self):
        """Set up test data."""
        super().setUp()

    def test_project_update(self):
        """
        Testing ProjectUpdateView functionality after removing auto approvals
        """
        form_data = {'title': 'New Updated Title',
                     'description': 'New Updated Description'}
        url = reverse(
            'project-update', kwargs={'pk': self.project1.pk})
        self.client.login(username=self.pi1.username, password=self.password)
        response = self.client.post(url, form_data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        self.assertRedirects(response, reverse('project-detail',
                                               kwargs={'pk': self.project1.pk}))
        self.project1.refresh_from_db()
        self.assertEqual(self.project1.title, form_data['title'])
        self.assertEqual(self.project1.description, form_data['description'])

