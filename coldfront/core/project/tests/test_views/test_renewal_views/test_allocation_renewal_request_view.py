from http import HTTPStatus

from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse

from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.billing.utils.billing_activity_managers import ProjectBillingActivityManager
from coldfront.core.billing.utils.billing_activity_managers import ProjectUserBillingActivityManager
from coldfront.core.billing.utils.billing_activity_managers import UserBillingActivityManager
from coldfront.core.billing.utils.queries import get_or_create_billing_activity_from_full_id
from coldfront.core.billing.utils.validation import is_billing_id_valid
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.utils_.new_project_user_utils import NewProjectUserRunnerFactory
from coldfront.core.project.utils_.new_project_user_utils import NewProjectUserSource
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import enable_deployment
from coldfront.core.utils.tests.test_base import TestBase


class TestAllocationRenewalRequestViewMixin(object):
    """A mixin for testing AllocationRenewalRequestView functionality
    common to both deployments."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

    def _create_project(self, project_name_suffix='project', pi=None):
        """Create a Project for the user to renew. Return the created
        Project along with a ProjectUser representing its PI.

        Optionally provide the suffix of the project name (e.g., the
        name will be {project_name_prefix}_{project_name_suffix}). The
        default suffix is "project".

        Optionally provide the User to set as the PI of the project. The
        default is self.user.
        """
        pi = pi or self.user

        computing_allowance_interface = ComputingAllowanceInterface()
        computing_allowance = self.get_predominant_computing_allowance()
        project_name_prefix = computing_allowance_interface.code_from_name(
            computing_allowance.name)

        project_name = f'{project_name_prefix}_{project_name_suffix}'
        project = self.create_active_project_with_pi(
            project_name, pi, create_compute_allocation=True)
        project_user = ProjectUser.objects.get(project=project, user=pi)
        return project, project_user

    @staticmethod
    def _renew_pi_allocation_url():
        """Return the URL for requesting to renew a PI's allocation."""
        return reverse('renew-pi-allocation')

    @staticmethod
    def _request_view_name():
        """Return the name of the request view."""
        return 'allocation_renewal_request_view'

    def _send_post_requests_for_pooling_preference(self, pooling_preference,
                                                   allocation_period,
                                                   pi_project_user,
                                                   project_to_pool_with_pk=None,
                                                   new_project_dict=None,
                                                   billing_id=None):
        """Send the necessary POST requests to the view to simulate the
        given pooling preference case.

        Optionally provide a billing ID.

        Parameters:
            - pooling_preference (str): The pooling preference to
                simulate. Options are defined in the
                AllowanceRenewalRequest model.
            - allocation_period (AllocationPeriod): The AllocationPeriod
                to renew under
            - pi_project_user (ProjectUser): The ProjectUser
                representing the PI whose allowance is being renewed
            - project_to_pool_with_pk (int): The primary key of the
                Project to pool with. This is only considered in some
                cases.
            - new_project_dict (dict): A dictionary of data for creating
                a new project. This is only considered when creating a
                new project.
            - billing_id (str): An optional billing ID to provide
        """
        view_name = self._request_view_name()
        current_step_key = f'{view_name}-current_step'

        form_data = []

        allocation_period_form_data = {
            '0-allocation_period': allocation_period.pk,
            current_step_key: '0',
        }
        form_data.append(allocation_period_form_data)

        pi_selection_form_data = {
            '1-PI': pi_project_user.pk,
            current_step_key: '1',
        }
        form_data.append(pi_selection_form_data)

        pooling_preference_form_data = {
            '2-preference': pooling_preference,
            current_step_key: '2',
        }
        form_data.append(pooling_preference_form_data)

        project_selection_preferences = (
            AllocationRenewalRequest.UNPOOLED_TO_POOLED,
            AllocationRenewalRequest.POOLED_TO_POOLED_DIFFERENT,
            AllocationRenewalRequest.POOLED_TO_UNPOOLED_OLD,
        )
        if pooling_preference in project_selection_preferences:
            project_selection_form_data = {
                '3-project': project_to_pool_with_pk,
                current_step_key: '3',
            }
            form_data.append(project_selection_form_data)

        if (pooling_preference ==
                AllocationRenewalRequest.POOLED_TO_UNPOOLED_NEW):
            assert new_project_dict is not None
            new_project_details_form_data = {
                '4-name': new_project_dict['name'],
                '4-title': new_project_dict['title'],
                '4-description': new_project_dict['description'],
                current_step_key: '4',
            }
            form_data.append(new_project_details_form_data)

        if billing_id is not None:
            billing_id_form_data = {
                '5-billing_id': billing_id,
                current_step_key: '5',
            }
            form_data.append(billing_id_form_data)

        if (pooling_preference ==
                AllocationRenewalRequest.POOLED_TO_UNPOOLED_NEW):
            new_project_survey_form_data = {
                '6-scope_and_intent': 'a' * 50,
                '6-computational_aspects': 'b' * 50,
                current_step_key: '6',
            }
            form_data.append(new_project_survey_form_data)

        renewal_survey_form_data = {
            '7-was_survey_completed': True,
            current_step_key: '7',
        }
        form_data.append(renewal_survey_form_data)

        review_and_submit_form_data = {
            '8-confirmation': True,
            current_step_key: '8',
        }
        form_data.append(review_and_submit_form_data)

        url = self._renew_pi_allocation_url()
        for i, data in enumerate(form_data):
            response = self.client.post(url, data)
            if i == len(form_data) - 1:
                self.assertRedirects(response, reverse('home'))
            else:
                self.assertEqual(response.status_code, HTTPStatus.OK)

    @override_settings(
        BILLING_VALIDATOR_BACKEND=(
            'coldfront.core.billing.utils.validation.backends.dummy.'
            'DummyValidatorBackend'))
    def test_post_sets_request_request_time(self):
        """Test that a POST request sets the request_time of the renewal
        request."""
        with enable_deployment(self._deployment_name):
            project, pi_project_user = self._create_project()

            pre_time = utc_now_offset_aware()

            allocation_period = get_current_allowance_year_period()

            kwargs = {}
            if self._deployment_name == 'LRC':
                kwargs['billing_id'] = '000000-000'

            self._send_post_requests_for_pooling_preference(
                AllocationRenewalRequest.UNPOOLED_TO_UNPOOLED,
                allocation_period, pi_project_user, **kwargs)

            post_time = utc_now_offset_aware()

            requests = AllocationRenewalRequest.objects.all()
            self.assertEqual(requests.count(), 1)
            request = requests.first()
            self.assertTrue(pre_time <= request.request_time <= post_time)


class TestBRCAllocationRenewalRequestView(TestAllocationRenewalRequestViewMixin,
                                          TestBase):
    """A class for testing AllocationRenewalRequestView on the BRC
    deployment."""

    @enable_deployment('BRC')
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self._deployment_name = 'BRC'


class TestLRCAllocationRenewalRequestView(TestAllocationRenewalRequestViewMixin,
                                          TestBase):
    """A class for testing AllocationRenewalRequestView on the LRC
    deployment."""

    @enable_deployment('LRC')
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self._deployment_name = 'LRC'
        self.user.email = 'test_user@lbl.gov'
        self.user.save()

    @enable_deployment('LRC')
    @override_settings(
        BILLING_VALIDATOR_BACKEND=(
            'coldfront.core.billing.utils.validation.backends.dummy.'
            'DummyValidatorBackend'))
    def test_billing_id_not_required_if_pi_not_pi_of_requested_project(self):
        """Test that a billing ID is not required if the selected PI is
        not already a PI of the requested project (and, therefore, they
        are unauthorized to make this change)."""
        # Create a project the PI's allowance is currently under.
        _, src_pi_project_user = self._create_project(
            project_name_suffix='src', pi=self.user)

        # Create a second project under a different PI to be pooled with.
        dst_pi = User.objects.create(
            email='test_pi0@lbl.gov',
            first_name='Test',
            last_name='PI0',
            username='test_pi0')
        dst_project, dst_pi_project_user = self._create_project(
            project_name_suffix='dst', pi=dst_pi)

        # Set the destination Project's billing ID to be an invalid one. (I.e.,
        # the billing ID update form would be included, but is skipped because
        # the PI is unauthorized.)
        billing_id = '000000-001'
        assert not is_billing_id_valid(billing_id)
        billing_activity = get_or_create_billing_activity_from_full_id(
            billing_id)
        manager = ProjectBillingActivityManager(dst_project)
        manager.billing_activity = billing_activity

        runner_factory = NewProjectUserRunnerFactory()

        # Propagate the destination project's billing ID to its PI's ProjectUser
        # and User objects.
        new_project_user_runner = runner_factory.get_runner(
            dst_pi_project_user, NewProjectUserSource.NEW_PROJECT_REQUESTER)
        new_project_user_runner.run()

        pi_project_user_manager = ProjectUserBillingActivityManager(
            dst_pi_project_user)
        assert pi_project_user_manager.billing_activity == billing_activity

        pi_user_manager = UserBillingActivityManager(dst_pi_project_user.user)
        assert pi_user_manager.billing_activity == billing_activity

        # Send the renewal request. No billing ID is required because the form
        # is not included, despite the fact that the billing ID is invalid,
        # because the PI is not already a PI of the project.
        allocation_period = get_current_allowance_year_period()
        self._send_post_requests_for_pooling_preference(
            AllocationRenewalRequest.UNPOOLED_TO_POOLED, allocation_period,
            src_pi_project_user, dst_project.pk)

        # Check that the request was created.
        requests = AllocationRenewalRequest.objects.all()
        self.assertEqual(requests.count(), 1)

        # Check that no entities referencing billing IDs on the destination
        # project were updated.
        assert manager.billing_activity == billing_activity
        assert pi_project_user_manager.billing_activity == billing_activity
        assert pi_user_manager.billing_activity == billing_activity

    @enable_deployment('LRC')
    @override_settings(
        BILLING_VALIDATOR_BACKEND=(
            'coldfront.core.billing.utils.validation.backends.dummy.'
            'DummyValidatorBackend'))
    def test_billing_id_required_if_creating_new_project(self):
        """Test that a billing ID is required if a new project is being
        created under the PI."""
        project, pi_project_user = self._create_project()

        # Add another PI to the project so that it is pooled.
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        other_pi = User.objects.create(
            email='test_pi0@lbl.gov',
            first_name='Test',
            last_name='PI0',
            username='test_pi0')
        ProjectUser.objects.create(
            project=project,
            user=other_pi,
            role=pi_role,
            status=active_project_user_status)

        # Send the renewal request with a new billing ID.
        new_billing_id = '000000-002'
        assert is_billing_id_valid(new_billing_id)
        new_billing_activity = get_or_create_billing_activity_from_full_id(
            new_billing_id)

        allocation_period = get_current_allowance_year_period()
        new_project_dict = {
            'name': 'dstproj',
            'title': 'Destination Project',
            'description': (
                'A new project to create to test that billing IDs are set.'),
        }

        self._send_post_requests_for_pooling_preference(
            AllocationRenewalRequest.POOLED_TO_UNPOOLED_NEW, allocation_period,
            pi_project_user, new_project_dict=new_project_dict,
            billing_id=new_billing_id)

        # Check that the request was created.
        requests = AllocationRenewalRequest.objects.all()
        self.assertEqual(requests.count(), 1)
        request = requests.first()
        new_project_request = request.new_project_request
        self.assertTrue(
            isinstance(new_project_request, SavioProjectAllocationRequest))

        # Check that a new Project was created with the name, title, and
        # description.
        new_project = new_project_request.project
        self.assertTrue(new_project.name.endswith(new_project_dict['name']))
        self.assertEqual(new_project.title, new_project_dict['title'])
        self.assertEqual(
            new_project.description, new_project_dict['description'])

        # Check that the new Project's billing ID was set.
        manager = ProjectBillingActivityManager(new_project)
        assert manager.billing_activity == new_billing_activity

    @enable_deployment('LRC')
    @override_settings(
        BILLING_VALIDATOR_BACKEND=(
            'coldfront.core.billing.utils.validation.backends.dummy.'
            'DummyValidatorBackend'))
    def test_post_updates_matching_billing_activities_pooling(self):
        """Test that a POST request that includes a billing ID update
        correctly updates the correct BillingActivity instances
        associated with the project. In this test, the requester opts to
        stay pooled under the same project (with another PI)."""
        project, pi_project_user = self._create_project()

        # Set the Project's billing ID.
        billing_id = '000000-001'
        assert not is_billing_id_valid(billing_id)
        billing_activity = get_or_create_billing_activity_from_full_id(
            billing_id)
        manager = ProjectBillingActivityManager(project)
        manager.billing_activity = billing_activity

        runner_factory = NewProjectUserRunnerFactory()

        # Propagate the project's billing ID to the PI's ProjectUser and User
        # objects.
        new_project_user_runner = runner_factory.get_runner(
            pi_project_user, NewProjectUserSource.NEW_PROJECT_REQUESTER)
        new_project_user_runner.run()

        pi_project_user_manager = ProjectUserBillingActivityManager(
            pi_project_user)
        assert pi_project_user_manager.billing_activity == billing_activity

        pi_user_manager = UserBillingActivityManager(pi_project_user.user)
        assert pi_user_manager.billing_activity == billing_activity

        # Add another PI to the project so that it is pooled.
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        other_pi = User.objects.create(
            email='test_pi0@lbl.gov',
            first_name='Test',
            last_name='PI0',
            username='test_pi0')
        other_pi_project_user = ProjectUser.objects.create(
            project=project,
            user=other_pi,
            role=pi_role,
            status=active_project_user_status)

        # Propagate the project's billing ID to the other PI's ProjectUser and
        # User objects.
        new_project_user_runner = runner_factory.get_runner(
            other_pi_project_user, NewProjectUserSource.ADDED)
        new_project_user_runner.run()

        other_pi_project_user_manager = ProjectUserBillingActivityManager(
            other_pi_project_user)
        assert (
            other_pi_project_user_manager.billing_activity == billing_activity)

        other_pi_user_manager = UserBillingActivityManager(
            other_pi_project_user.user)
        assert other_pi_user_manager.billing_activity == billing_activity

        # Override some billing IDs to not match the original.
        other_billing_id = '000000-003'
        other_billing_activity = (
            get_or_create_billing_activity_from_full_id(other_billing_id))
        pi_user_manager.billing_activity = other_billing_activity
        other_pi_project_user_manager.billing_activity = other_billing_activity

        # Send the renewal request with a new billing ID.
        new_billing_id = '000000-002'
        assert is_billing_id_valid(new_billing_id)
        new_billing_activity = get_or_create_billing_activity_from_full_id(
            new_billing_id)

        allocation_period = get_current_allowance_year_period()
        self._send_post_requests_for_pooling_preference(
            AllocationRenewalRequest.POOLED_TO_POOLED_SAME, allocation_period,
            pi_project_user, billing_id=new_billing_id)

        # Check that only the entities that referenced the old billing ID were
        # updated.
        assert manager.billing_activity == new_billing_activity
        assert pi_project_user_manager.billing_activity == new_billing_activity
        assert pi_user_manager.billing_activity == other_billing_activity
        assert (
            other_pi_project_user_manager.billing_activity ==
            other_billing_activity)
        assert other_pi_user_manager.billing_activity == new_billing_activity
