from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.project.tests.test_views.test_renewal_views.utils import TestRenewalViewsMixin
from coldfront.core.project.tests.utils import create_project_and_request
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase
from django.urls import reverse
from http import HTTPStatus
import iso8601


class TestAllocationRenewalRequestReviewEligibilityView(TestBase,
                                                        TestRenewalViewsMixin):
    """A class for testing
    AllocationRenewalRequestReviewEligibilityView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

        self.user.is_superuser = True
        self.user.save()

        computing_allowance_interface = ComputingAllowanceInterface()
        computing_allowance = self.get_predominant_computing_allowance()
        project_name_prefix = computing_allowance_interface.code_from_name(
            computing_allowance.name)

        # Create a Project and an associated renewal request.
        project_name = f'{project_name_prefix}_project'
        project, self.allocation_renewal_request = \
            self.create_project_and_request(
                project_name, computing_allowance, self.user)

    @staticmethod
    def pi_allocation_renewal_request_review_eligibility_url(pk):
        """Return the URL for the view for reviewing the eligibility of
        the PI of the AllocationRenewalRequest with the given primary
        key."""
        return reverse(
            'pi-allocation-renewal-request-review-eligibility',
            kwargs={'pk': pk})

    def test_permissions_get(self):
        """Test that the correct users have permissions to perform GET
        requests."""

        def assert_has_access(user, has_access=True, expected_messages=[]):
            """Assert that the given user has or does not have access to
            the URL. Optionally assert that any messages were sent to
            the user."""
            self.client.login(username=user.username, password=self.password)
            url = self.pi_allocation_renewal_request_review_eligibility_url(
                self.allocation_renewal_request.pk)
            status_code = HTTPStatus.OK if has_access else HTTPStatus.FORBIDDEN
            response = self.client.get(url)
            if expected_messages:
                actual_messages = self.get_message_strings(response)
                for message in expected_messages:
                    self.assertIn(message, actual_messages)
            self.assertEqual(response.status_code, status_code)
            self.client.logout()

        # Superusers should have access.
        self.assertTrue(self.user.is_superuser)
        assert_has_access(self.user)

        # Non-superusers should not have access.
        self.user.is_superuser = False
        self.user.save()
        expected_messages = [
            'You do not have permission to view the previous page.',
        ]
        assert_has_access(
            self.user, has_access=False, expected_messages=expected_messages)

    def test_permissions_post(self):
        """Test that the correct users have permissions to perform POST
        requests."""
        url = self.pi_allocation_renewal_request_review_eligibility_url(
            self.allocation_renewal_request.pk)
        data = {}

        # Non-superusers should not have access.
        self.user.is_superuser = False
        self.user.save()
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        message = 'You do not have permission to view the previous page.'
        self.assertEqual(message, self.get_message_strings(response)[0])

        # Superusers should have access.
        self.user.is_superuser = True
        self.user.save()
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_view_blocked_for_inapplicable_statuses(self):
        """Test that requests that are already 'Approved', 'Complete',
        or 'Denied' cannot be modified via the view."""
        url = self.pi_allocation_renewal_request_review_eligibility_url(
            self.allocation_renewal_request.pk)
        data = {}

        redirect_url = reverse(
            'pi-allocation-renewal-request-detail',
            kwargs={'pk': self.allocation_renewal_request.pk})
        for status_name in ('Approved', 'Complete', 'Denied'):
            self.allocation_renewal_request.status = \
                AllocationRenewalRequestStatusChoice.objects.get(
                    name=status_name)
            # In the 'Denied' case, the view being redirected to expects
            # certain fields in the 'state' field to be set.
            if status_name == 'Denied':
                self.allocation_renewal_request.state['other'] = {
                    'justification': (
                        'This is a test of denying an '
                        'AllocationRenewalRequest.'),
                    'timestamp': utc_now_offset_aware().isoformat(),
                }
            self.allocation_renewal_request.save()
            response = self.client.post(url, data)
            self.assertRedirects(response, redirect_url)
            message = f'You cannot review a request with status {status_name}.'
            self.assertEqual(message, self.get_message_strings(response)[0])

    def test_view_blocked_if_new_project_request(self):
        """Test that, if the request has an associated
        SavioProjectAllocationRequest for a new Project, the view is
        blocked."""
        url = self.pi_allocation_renewal_request_review_eligibility_url(
            self.allocation_renewal_request.pk)
        data = {}

        # Create a new Project and associated request.
        computing_allowance = self.get_predominant_computing_allowance()
        new_project_name = 'fc_new_project'
        new_project, new_project_request = create_project_and_request(
            new_project_name, 'New', computing_allowance,
            get_current_allowance_year_period(), self.user, self.user,
            'Under Review')

        self.allocation_renewal_request.new_project_request = \
            new_project_request
        self.allocation_renewal_request.save()

        redirect_url = reverse(
            'pi-allocation-renewal-request-detail',
            kwargs={'pk': self.allocation_renewal_request.pk})
        response = self.client.post(url, data)
        self.assertRedirects(response, redirect_url)
        message = (
            'This request involves creating a new project. Eligibility '
            'review must be handled in the associated project request.')
        self.assertEqual(message, self.get_message_strings(response)[0])

        # Remove the reference.
        self.allocation_renewal_request.new_project_request = None
        self.allocation_renewal_request.save()
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_updates_request_state_and_status(self):
        """Test that a POST request updates the request's 'state' and
        'status' fields."""
        url = self.pi_allocation_renewal_request_review_eligibility_url(
            self.allocation_renewal_request.pk)
        data = {
            'status': 'Approved',
            'justification': (
                'This is a test that a POST request updates the request.'),
        }

        # Test setting the status to 'Approved'.
        pre_time = utc_now_offset_aware()

        redirect_url = reverse(
            'pi-allocation-renewal-request-detail',
            kwargs={'pk': self.allocation_renewal_request.pk})
        response = self.client.post(url, data)
        self.assertRedirects(response, redirect_url)
        message = (
            f'Eligibility status for request '
            f'{self.allocation_renewal_request.pk} has been set to '
            f'Approved.')
        self.assertEqual(message, self.get_message_strings(response)[0])

        post_time = utc_now_offset_aware()

        self.allocation_renewal_request.refresh_from_db()
        eligibility = self.allocation_renewal_request.state['eligibility']
        self.assertEqual(eligibility['status'], data['status'])
        self.assertEqual(eligibility['justification'], data['justification'])
        time = iso8601.parse_date(eligibility['timestamp'])
        self.assertTrue(pre_time <= time <= post_time)
        self.assertEqual(
            self.allocation_renewal_request.status.name, 'Under Review')

        # Test setting the status to 'Denied'.
        data['status'] = 'Denied'

        pre_time = utc_now_offset_aware()

        response = self.client.post(url, data)
        self.assertRedirects(response, redirect_url)
        message = (
            f'Eligibility status for request '
            f'{self.allocation_renewal_request.pk} has been set to Denied.')
        self.assertEqual(message, self.get_message_strings(response)[0])

        post_time = utc_now_offset_aware()

        self.allocation_renewal_request.refresh_from_db()
        eligibility = self.allocation_renewal_request.state['eligibility']
        self.assertEqual(eligibility['status'], data['status'])
        self.assertEqual(eligibility['justification'], data['justification'])
        time = iso8601.parse_date(eligibility['timestamp'])
        self.assertTrue(pre_time <= time <= post_time)
        self.assertEqual(self.allocation_renewal_request.status.name, 'Denied')
