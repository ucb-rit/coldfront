"""Component tests for request views."""

import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

from coldfront.core.project.models import ProjectUser
from coldfront.plugins.cluster_storage.models import (
    FacultyStorageAllocationRequest,
)
from coldfront.plugins.cluster_storage.tests.pytest.utils import (
    create_storage_request,
)

User = get_user_model()


@pytest.mark.component
class TestStorageRequestView:
    """Integration tests for storage request creation view.

    Note: This tests the StorageRequestView which is accessed via
    project-specific URLs, not the generic storage-request URLs.
    """

    def test_get_request_form_displays_correctly(
        self, client, test_project, test_pi,
        project_user_role_pi, project_user_status_active,
        sign_user_access_agreement
    ):
        """Test GET request shows form to create storage request."""
        # Create ProjectUser for the PI
        ProjectUser.objects.create(
            project=test_project,
            user=test_pi,
            role=project_user_role_pi,
            status=project_user_status_active
        )

        # Ensure PI has signed access agreement
        sign_user_access_agreement(test_pi)

        # Log in as PI
        client.force_login(test_pi)

        # Access the form using reverse
        url = reverse('storage-request', kwargs={'pk': test_project.pk})
        response = client.get(url)

        # Should show the form
        assert response.status_code == 200
        assert 'form' in response.context
        assert 'storage_amount' in response.context['form'].fields
        assert 'pi' in response.context['form'].fields

    def test_post_creates_request_in_database(
        self, client, test_project, test_pi, test_user,
        project_user_role_pi, project_user_status_active,
        sign_user_access_agreement
    ):
        """Test POST creates FacultyStorageAllocationRequest in DB."""
        # Create ProjectUser for the PI
        pi_project_user = ProjectUser.objects.create(
            project=test_project,
            user=test_pi,
            role=project_user_role_pi,
            status=project_user_status_active
        )

        # Ensure PI has signed access agreement
        sign_user_access_agreement(test_pi)

        # Log in as PI
        client.force_login(test_pi)

        # Submit the form
        data = {
            'pi': pi_project_user.pk,
            'storage_amount': 3,
            'confirm_external_intake': True
        }

        initial_count = FacultyStorageAllocationRequest.objects.count()

        url = reverse('storage-request', kwargs={'pk': test_project.pk})
        response = client.post(url, data=data)

        # Verify request was created
        assert FacultyStorageAllocationRequest.objects.count() == \
            initial_count + 1

        # Verify request has correct data
        request = FacultyStorageAllocationRequest.objects.latest('id')
        assert request.project == test_project
        assert request.pi == test_pi
        assert request.requester == test_pi
        assert request.requested_amount_gb == 3000  # 3 TB = 3000 GB
        assert request.status.name == 'Under Review'

    def test_post_redirects_on_success(
        self, client, test_project, test_pi,
        project_user_role_pi, project_user_status_active,
        sign_user_access_agreement
    ):
        """Test successful creation redirects to project detail page."""
        # Create ProjectUser for the PI
        pi_project_user = ProjectUser.objects.create(
            project=test_project,
            user=test_pi,
            role=project_user_role_pi,
            status=project_user_status_active
        )

        # Ensure PI has signed access agreement
        sign_user_access_agreement(test_pi)

        # Log in as PI
        client.force_login(test_pi)

        # Submit the form
        data = {
            'pi': pi_project_user.pk,
            'storage_amount': 2,
            'confirm_external_intake': True
        }

        url = reverse('storage-request', kwargs={'pk': test_project.pk})
        response = client.post(url, data=data)

        # Should redirect to project detail
        assert response.status_code == 302
        assert f'/project/{test_project.pk}/' in response.url

    def test_post_shows_errors_on_invalid_data(
        self, client, test_project, test_pi,
        project_user_role_pi, project_user_status_active,
        sign_user_access_agreement
    ):
        """Test form displays validation errors."""
        # Create ProjectUser for the PI
        ProjectUser.objects.create(
            project=test_project,
            user=test_pi,
            role=project_user_role_pi,
            status=project_user_status_active
        )

        # Ensure PI has signed access agreement
        sign_user_access_agreement(test_pi)

        # Log in as PI
        client.force_login(test_pi)

        # Submit with missing required field
        data = {
            'storage_amount': 2,
            'confirm_external_intake': True
            # Missing 'pi' field
        }

        url = reverse('storage-request', kwargs={'pk': test_project.pk})
        response = client.post(url, data=data)

        # Should show form with errors
        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['form'].errors
        assert 'pi' in response.context['form'].errors

    def test_view_requires_authentication(self, client, test_project):
        """Test view requires user to be logged in."""
        # Try to access without logging in
        url = reverse('storage-request', kwargs={'pk': test_project.pk})
        response = client.get(url)

        # Should redirect to login
        assert response.status_code == 302
        assert '/login' in response.url.lower()

    def test_view_requires_project_membership(
        self, client, test_project, test_user
    ):
        """Test view requires user to be PI or manager of project."""
        # Log in as user who is NOT a member of the project
        client.force_login(test_user)

        url = reverse('storage-request', kwargs={'pk': test_project.pk})
        response = client.get(url)

        # Should deny access (403) or redirect
        assert response.status_code in [302, 403]

    def test_post_prevents_duplicate_requests(
        self, client, test_project, test_pi,
        project_user_role_pi, project_user_status_active,
        sign_user_access_agreement
    ):
        """Test cannot create request if PI already has active request."""
        # Create ProjectUser for the PI
        pi_project_user = ProjectUser.objects.create(
            project=test_project,
            user=test_pi,
            role=project_user_role_pi,
            status=project_user_status_active
        )

        # Ensure PI has signed access agreement
        sign_user_access_agreement(test_pi)

        # Create existing request for this PI
        create_storage_request(
            status='Under Review',
            project=test_project,
            requester=test_pi,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Log in as PI
        client.force_login(test_pi)

        # Try to submit another request
        data = {
            'pi': pi_project_user.pk,
            'storage_amount': 2,
            'confirm_external_intake': True
        }

        initial_count = FacultyStorageAllocationRequest.objects.count()

        url = reverse('storage-request', kwargs={'pk': test_project.pk})
        response = client.post(url, data=data)

        # Should not create a new request
        assert FacultyStorageAllocationRequest.objects.count() == initial_count

        # Should show error message
        messages = list(response.context['messages'])
        assert len(messages) > 0
        assert 'cannot be submitted' in str(messages[0]).lower()


@pytest.mark.component
class TestStorageRequestDetailView:
    """Integration tests for request detail view."""

    def test_displays_request_details(
        self, client, test_project, test_user, test_pi
    ):
        """Test view shows all request information."""
        # Create a request
        request = create_storage_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=2000
        )

        # Log in as superuser to ensure access
        superuser = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='adminpass'
        )
        client.force_login(superuser)

        # Access detail view
        url = reverse('storage-request-detail', kwargs={'pk': request.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert 'request' in response.context or \
               'object' in response.context or \
               'facultystorageallocationrequest' in response.context

        # Check that request data is in response
        content = response.content.decode()
        assert test_project.name in content
        assert str(request.requested_amount_gb) in content or \
               '2000' in content or '2 TB' in content

    def test_shows_current_state(
        self, client, test_project, test_user, test_pi
    ):
        """Test view displays current workflow state."""
        # Create a request and approve eligibility
        request = create_storage_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1500
        )

        # Update state
        request.state['eligibility']['status'] = 'Approved'
        request.save()

        # Log in as superuser
        superuser = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='adminpass'
        )
        client.force_login(superuser)

        # Access detail view
        url = reverse('storage-request-detail', kwargs={'pk': request.pk})
        response = client.get(url)

        assert response.status_code == 200

        # Check that state information is displayed
        content = response.content.decode()
        # State display varies, but should show some indication
        assert 'eligibility' in content.lower() or \
               'status' in content.lower()

    def test_requires_permission_to_view(
        self, client, test_project, test_user, test_pi
    ):
        """Test user must have permission to view request."""
        # Create a request
        request = create_storage_request(
            status='Under Review',
            project=test_project,
            requester=test_pi,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Log in as unrelated user (not PI, not admin)
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@test.com',
            password='pass'
        )
        client.force_login(other_user)

        # Try to access detail view
        url = reverse('storage-request-detail', kwargs={'pk': request.pk})
        response = client.get(url)

        # Should deny access
        assert response.status_code in [302, 403, 404]

    def test_pi_can_view_own_request(
        self, client, test_project, test_pi,
        project_user_role_pi, project_user_status_active,
        sign_user_access_agreement
    ):
        """Test PI can view their own storage request with access agreement.
        """
        # Make PI a project member
        ProjectUser.objects.create(
            project=test_project,
            user=test_pi,
            role=project_user_role_pi,
            status=project_user_status_active
        )

        # Ensure PI has signed access agreement
        sign_user_access_agreement(test_pi)

        # Create a request for this PI
        request = create_storage_request(
            status='Under Review',
            project=test_project,
            requester=test_pi,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Log in as PI
        client.force_login(test_pi)

        # Access detail view
        url = reverse('storage-request-detail', kwargs={'pk': request.pk})
        response = client.get(url)

        # Should allow access
        assert response.status_code == 200
