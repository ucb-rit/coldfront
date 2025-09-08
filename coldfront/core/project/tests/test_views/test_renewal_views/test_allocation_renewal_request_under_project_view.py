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
from coldfront.core.project.utils_.new_project_user_utils import NewProjectUserRunnerFactory
from coldfront.core.project.utils_.new_project_user_utils import NewProjectUserSource
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import enable_deployment
from coldfront.core.utils.tests.test_base import TestBase


class TestAllocationRenewalRequestUnderProjectViewMixin(object):
    """A mixin for testing AllocationRenewalRequestUnderProjectView
    functionality common to both deployments."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

    def _create_project_to_renew(self):
        """Create a Project for the user to renew. Return the created
        Project along with a ProjectUser representing its PI."""
        computing_allowance_interface = ComputingAllowanceInterface()
        computing_allowance = self.get_predominant_computing_allowance()
        project_name_prefix = computing_allowance_interface.code_from_name(
            computing_allowance.name)

        project_name = f'{project_name_prefix}_project'
        project = self.create_active_project_with_pi(
            project_name, self.user, create_compute_allocation=True)
        project_user = ProjectUser.objects.get(project=project, user=self.user)
        return project, project_user

    @staticmethod
    def _project_detail_url(pk):
        """Return the URL for the detail view for the Project with the
        given primary key."""
        return reverse('project-detail', kwargs={'pk': pk})

    @staticmethod
    def _project_renew_url(pk):
        """Return the URL for the requesting to renew a PI's
        allocation under the Project with the given primary key."""
        return reverse('project-renew', kwargs={'pk': pk})

    @staticmethod
    def _request_view_name():
        """Return the name of the request view."""
        return 'allocation_renewal_request_under_project_view'

    def _send_post_requests(self, allocation_period, project, pi_project_user,
                            billing_id=None):
        """Send the necessary POST requests to the view for the given
        AllocationPeriod, Project, and PI ProjectUser. Optionally
        provide a billing ID."""
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

        if billing_id is not None:
            billing_id_form_data = {
                '2-billing_id': billing_id,
                current_step_key: '2',
            }
            form_data.append(billing_id_form_data)

        renewal_survey_form_data = {
            '3-was_survey_completed': True,
            current_step_key: '3',
        }
        form_data.append(renewal_survey_form_data)

        review_and_submit_form_data = {
            '4-confirmation': True,
            current_step_key: '4',
        }
        form_data.append(review_and_submit_form_data)

        url = self._project_renew_url(project.pk)
        for i, data in enumerate(form_data):
            response = self.client.post(url, data)
            if i == len(form_data) - 1:
                self.assertRedirects(
                    response, self._project_detail_url(project.pk))
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
            project, pi_project_user = self._create_project_to_renew()

            pre_time = utc_now_offset_aware()

            allocation_period = get_current_allowance_year_period()

            kwargs = {}
            if self._deployment_name == 'LRC':
                kwargs['billing_id'] = '000000-000'

            self._send_post_requests(
                allocation_period, project, pi_project_user, **kwargs)

            post_time = utc_now_offset_aware()

            requests = AllocationRenewalRequest.objects.all()
            self.assertEqual(requests.count(), 1)
            request = requests.first()
            self.assertTrue(pre_time <= request.request_time <= post_time)


class TestBRCAllocationRenewalRequestUnderProjectView(TestAllocationRenewalRequestUnderProjectViewMixin,
                                                      TestBase):
    """A class for testing AllocationRenewalRequestUnderProjectView on
    the BRC deployment."""

    @enable_deployment('BRC')
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self._deployment_name = 'BRC'


class TestLRCAllocationRenewalRequestUnderProjectView(TestAllocationRenewalRequestUnderProjectViewMixin,
                                                      TestBase):
    """A class for testing AllocationRenewalRequestUnderProjectView on
    the LRC deployment."""

    @enable_deployment('LRC')
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self._deployment_name = 'LRC'
        self.user.email = 'test_user@lbl.gov'
        self.user.save()

    @enable_deployment('LRC')
    def test_billing_id_must_be_valid(self):
        """Test that a billing ID provided when renewing a Project
        must be valid."""
        project, pi_project_user = self._create_project_to_renew()

        allocation_period = get_current_allowance_year_period()

        billing_id = '000000-001'
        assert not is_billing_id_valid(billing_id)

        with self.assertRaises(AssertionError) as cm:
            self._send_post_requests(
                allocation_period, project, pi_project_user,
                billing_id=billing_id)

        requests = AllocationRenewalRequest.objects.all()
        self.assertEqual(requests.count(), 0)

    @enable_deployment('LRC')
    @override_settings(
        BILLING_VALIDATOR_BACKEND=(
            'coldfront.core.billing.utils.validation.backends.dummy.'
            'DummyValidatorBackend'))
    def test_billing_id_not_required_if_project_has_valid_billing_id(self):
        """Test that a billing ID is not required if the Project to be
        renewed already has a valid billing ID."""
        project, pi_project_user = self._create_project_to_renew()

        allocation_period = get_current_allowance_year_period()

        billing_id = '000000-000'
        assert is_billing_id_valid(billing_id)
        billing_activity = get_or_create_billing_activity_from_full_id(
            billing_id)
        manager = ProjectBillingActivityManager(project)
        manager.billing_activity = billing_activity

        # The request succeeds without providing a billing ID, indicating that
        # the form is not required.
        self._send_post_requests(
            allocation_period, project, pi_project_user, billing_id=None)

        requests = AllocationRenewalRequest.objects.all()
        self.assertEqual(requests.count(), 1)

    @enable_deployment('LRC')
    @override_settings(
        BILLING_VALIDATOR_BACKEND=(
            'coldfront.core.billing.utils.validation.backends.dummy.'
            'DummyValidatorBackend'))
    def test_billing_id_required_if_project_has_invalid_billing_id(self):
        """Test that a billing ID is required if the Project to be
        renewed has an invalid billing ID."""
        project, pi_project_user = self._create_project_to_renew()

        allocation_period = get_current_allowance_year_period()

        billing_id = '000000-001'
        assert not is_billing_id_valid(billing_id)
        billing_activity = get_or_create_billing_activity_from_full_id(
            billing_id)
        manager = ProjectBillingActivityManager(project)
        manager.billing_activity = billing_activity

        # The request fails without providing a billing ID, indicating that
        # the form is required.
        with self.assertRaises(AssertionError):
            self._send_post_requests(
                allocation_period, project, pi_project_user, billing_id=None)

        requests = AllocationRenewalRequest.objects.all()
        self.assertEqual(requests.count(), 0)

    @enable_deployment('LRC')
    @override_settings(
        BILLING_VALIDATOR_BACKEND=(
            'coldfront.core.billing.utils.validation.backends.dummy.'
            'DummyValidatorBackend'))
    def test_post_updates_matching_billing_activities(self):
        """Test that a POST request that includes a billing ID update
        correctly updates the correct BillingActivity instances
        associated with the project."""
        project, pi_project_user = self._create_project_to_renew()

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

        # Add another user to the project.
        user_role = ProjectUserRoleChoice.objects.get(name='User')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        other_user = User.objects.create(
            email='test_user0@lbl.gov',
            first_name='Test',
            last_name='User0',
            username='test_user0')
        other_project_user = ProjectUser.objects.create(
            project=project,
            user=other_user,
            role=user_role,
            status=active_project_user_status)

        # Propagate the project's billing ID to the other user's ProjectUser and
        # User objects.
        new_project_user_runner = runner_factory.get_runner(
            other_project_user, NewProjectUserSource.ADDED)
        new_project_user_runner.run()

        other_project_user_manager = ProjectUserBillingActivityManager(
            other_project_user)
        assert other_project_user_manager.billing_activity == billing_activity

        other_user_manager = UserBillingActivityManager(other_project_user.user)
        assert other_user_manager.billing_activity == billing_activity

        # Override some billing IDs to not match the original.
        other_billing_id = '000000-003'
        other_billing_activity = (
            get_or_create_billing_activity_from_full_id(other_billing_id))
        pi_user_manager.billing_activity = other_billing_activity
        other_project_user_manager.billing_activity = other_billing_activity

        # Send the renewal request with a new billing ID.
        new_billing_id = '000000-002'
        assert is_billing_id_valid(new_billing_id)
        new_billing_activity = get_or_create_billing_activity_from_full_id(
            new_billing_id)

        allocation_period = get_current_allowance_year_period()
        self._send_post_requests(
            allocation_period, project, pi_project_user,
            billing_id=new_billing_id)

        # Check that only the entities that referenced the old billing ID were
        # updated.
        assert manager.billing_activity == new_billing_activity
        assert pi_project_user_manager.billing_activity == new_billing_activity
        assert pi_user_manager.billing_activity == other_billing_activity
        assert (
            other_project_user_manager.billing_activity ==
            other_billing_activity)
        assert other_user_manager.billing_activity == new_billing_activity
