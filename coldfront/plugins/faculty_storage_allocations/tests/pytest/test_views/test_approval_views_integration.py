"""Component tests for approval views."""

import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

from coldfront.core.project.models import ProjectUser
from coldfront.plugins.faculty_storage_allocations.tests.pytest.utils import (
    create_fsa_request,
)

User = get_user_model()


@pytest.mark.component
class TestFSARequestDetailView:
    """Integration tests for request detail view."""

    def test_displays_request_details(
        self, client, test_project, test_user, test_pi
    ):
        """Test view shows all request information including directory path."""
        # Create a request
        request = create_fsa_request(
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
        url = reverse('faculty-storage-allocation-request-detail', kwargs={'pk': request.pk})
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

        # Check that proposed directory path is displayed
        assert 'proposed_directory_path' in response.context
        proposed_path = response.context['proposed_directory_path']
        assert test_project.name in proposed_path
        assert proposed_path in content

    def test_shows_current_state(
        self, client, test_project, test_user, test_pi
    ):
        """Test view displays current workflow state."""
        # Create a request and approve eligibility
        request = create_fsa_request(
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
        url = reverse('faculty-storage-allocation-request-detail', kwargs={'pk': request.pk})
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
        request = create_fsa_request(
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
        url = reverse('faculty-storage-allocation-request-detail', kwargs={'pk': request.pk})
        response = client.get(url)

        # Should deny access
        assert response.status_code in [302, 403, 404]

    def test_pi_can_view_own_request(
        self, client, test_project, test_pi,
        project_user_role_pi, project_user_status_active,
        sign_user_access_agreement
    ):
        """Test PI can view their own FSA request with access agreement.
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
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_pi,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Log in as PI
        client.force_login(test_pi)

        # Access detail view
        url = reverse('faculty-storage-allocation-request-detail', kwargs={'pk': request.pk})
        response = client.get(url)

        # Should allow access
        assert response.status_code == 200

    def test_requester_can_view_own_request(
        self, client, test_project, test_pi, test_user,
        sign_user_access_agreement
    ):
        """Test requester can view their own FSA request."""
        # Ensure requester has signed access agreement
        sign_user_access_agreement(test_user)

        # Create a request where test_user is the requester
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,  # test_user is requester
            pi=test_pi,           # test_pi is PI
            requested_amount_gb=1000
        )

        # Log in as requester (not PI, not admin)
        client.force_login(test_user)

        # Access detail view
        url = reverse('faculty-storage-allocation-request-detail', kwargs={'pk': request.pk})
        response = client.get(url)

        # Requester should be able to view their own request
        assert response.status_code == 200

    def test_undeny_button_only_visible_for_denied_requests(
        self, client, test_project, test_pi, test_user
    ):
        """Test 'Un-deny Request' button only appears when request is denied."""
        from coldfront.plugins.faculty_storage_allocations.models import (
            FacultyStorageAllocationRequestStatusChoice,
        )

        # Create an Under Review request
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Log in as superuser who can manage requests
        superuser = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='adminpass'
        )
        client.force_login(superuser)

        # Define URLs
        url = reverse('faculty-storage-allocation-request-detail', kwargs={'pk': request.pk})
        undeny_url = reverse('faculty-storage-allocation-request-undeny', kwargs={'pk': request.pk})

        # Access detail view for Under Review request
        response = client.get(url)

        assert response.status_code == 200
        content = response.content.decode()

        # Un-deny button should NOT be visible for Under Review requests
        assert 'Un-deny Request:' not in content
        assert undeny_url not in content

        # Now change the request to Denied status
        denied_status = FacultyStorageAllocationRequestStatusChoice.objects.get(
            name='Denied'
        )
        request.status = denied_status
        request.state['eligibility']['status'] = 'Denied'
        request.state['eligibility']['justification'] = 'Test denial'
        request.save()

        # Access detail view again
        response = client.get(url)

        assert response.status_code == 200
        content = response.content.decode()

        # Un-deny button SHOULD be visible for Denied requests
        assert 'Un-deny Request:' in content
        assert undeny_url in content


@pytest.mark.component
class TestFSARequestAdminAccessMixin:
    """Test admin access control shared across all review views."""

    def test_superuser_can_access_review_views(
        self, client, test_project, test_pi, test_user
    ):
        """Test superusers can access any review view."""
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Create superuser
        superuser = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='adminpass'
        )
        client.force_login(superuser)

        # Test a representative review view (they all use same mixin)
        url = reverse('faculty-storage-allocation-request-review-eligibility',
                     kwargs={'pk': request.pk})
        response = client.get(url)

        assert response.status_code == 200

    def test_staff_with_manage_permission_can_access(
        self, client, test_project, test_pi, test_user
    ):
        """Test staff users with can_manage permission can access."""
        from django.contrib.auth.models import Permission

        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Create staff user with permission
        staff_user = User.objects.create_user(
            username='staff',
            email='staff@test.com',
            password='staffpass',
            is_staff=True
        )
        permission = Permission.objects.get(
            codename='can_manage_fsa_requests'
        )
        staff_user.user_permissions.add(permission)

        client.force_login(staff_user)

        url = reverse('faculty-storage-allocation-request-review-eligibility',
                     kwargs={'pk': request.pk})
        response = client.get(url)

        assert response.status_code == 200

    def test_regular_user_denied_access(
        self, client, test_project, test_pi, test_user
    ):
        """Test regular users cannot access review views."""
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Log in as regular user (not staff, not admin)
        client.force_login(test_user)

        url = reverse('faculty-storage-allocation-request-review-eligibility',
                     kwargs={'pk': request.pk})
        response = client.get(url)

        # Should be denied (403) or redirected
        assert response.status_code in [302, 403]

    def test_staff_without_permission_denied_access(
        self, client, test_project, test_pi, test_user
    ):
        """Test staff users without can_manage permission are denied."""
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Create staff user WITHOUT the permission
        staff_user = User.objects.create_user(
            username='staff_no_perm',
            email='staff_no_perm@test.com',
            password='staffpass',
            is_staff=True
        )

        client.force_login(staff_user)

        url = reverse('faculty-storage-allocation-request-review-eligibility',
                     kwargs={'pk': request.pk})
        response = client.get(url)

        # Should be denied
        assert response.status_code in [302, 403]

    def test_pi_cannot_access_review_views(
        self, client, test_project, test_pi, test_user,
        sign_user_access_agreement
    ):
        """Test PI cannot access admin review views (only detail view).

        The PI can view the detail page of their request, but cannot
        access the admin review/edit views.
        """
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Sign access agreement
        sign_user_access_agreement(test_pi)

        # Log in as PI
        client.force_login(test_pi)

        # Try to access review view (admin-only)
        url = reverse('faculty-storage-allocation-request-review-eligibility',
                     kwargs={'pk': request.pk})
        response = client.get(url)

        # Should be denied (review views are admin-only)
        assert response.status_code in [302, 403]

    def test_requester_cannot_access_review_views(
        self, client, test_project, test_pi, test_user,
        sign_user_access_agreement
    ):
        """Test requester cannot access admin review views (only detail view).

        The requester can view the detail page of their request, but cannot
        access the admin review/edit views.
        """
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Sign access agreement
        sign_user_access_agreement(test_user)

        # Log in as requester
        client.force_login(test_user)

        # Try to access review view (admin-only)
        url = reverse('faculty-storage-allocation-request-review-eligibility',
                     kwargs={'pk': request.pk})
        response = client.get(url)

        # Should be denied (review views are admin-only)
        assert response.status_code in [302, 403]

    def test_non_staff_user_with_permission_can_access(
        self, client, test_project, test_pi, test_user
    ):
        """Test non-staff users with can_manage permission can access.

        This verifies that is_staff is not required - only the
        can_manage_fsa_requests permission matters.
        """
        from django.contrib.auth.models import Permission

        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Create NON-STAFF user with the permission
        non_staff_admin = User.objects.create_user(
            username='non_staff_admin',
            email='non_staff_admin@test.com',
            is_staff=False  # Explicitly not staff
        )
        permission = Permission.objects.get(
            codename='can_manage_fsa_requests'
        )
        non_staff_admin.user_permissions.add(permission)

        client.force_login(non_staff_admin)

        # Try to access review view
        url = reverse('faculty-storage-allocation-request-review-eligibility',
                     kwargs={'pk': request.pk})
        response = client.get(url)

        # Should allow access
        assert response.status_code == 200


@pytest.mark.component
class TestFSARequestReviewEligibilityView:
    """Test eligibility review view unique behavior."""

    def test_get_displays_eligibility_review_form(
        self, client, staff_user, test_project, test_pi, test_user
    ):
        """Test GET displays eligibility review form."""
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        client.force_login(staff_user)
        url = reverse('faculty-storage-allocation-request-review-eligibility',
                     kwargs={'pk': request.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert 'form' in response.context
        assert 'fsa_request' in response.context
        # Check for eligibility-specific text
        content = response.content.decode()
        assert 'eligible' in content.lower()

    def test_approving_eligibility_when_intake_approved_moves_to_queued(
        self, client, staff_user, test_project, test_pi, test_user
    ):
        """Test approving eligibility when intake approved changes status to Approved - Queued."""
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Pre-approve intake consistency
        request.state['intake_consistency']['status'] = 'Approved'
        request.save()

        client.force_login(staff_user)
        url = reverse('faculty-storage-allocation-request-review-eligibility',
                     kwargs={'pk': request.pk})

        # Approve eligibility
        response = client.post(url, data={
            'status': 'Approved',
            'justification': ''
        })

        # Should redirect
        assert response.status_code == 302

        # Check status changed
        request.refresh_from_db()
        assert request.status.name == 'Approved - Queued'
        assert request.state['eligibility']['status'] == 'Approved'

    def test_denying_eligibility_denies_entire_request(
        self, client, staff_user, test_project, test_pi, test_user
    ):
        """Test denying eligibility immediately denies the entire request."""
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        client.force_login(staff_user)
        url = reverse('faculty-storage-allocation-request-review-eligibility',
                     kwargs={'pk': request.pk})

        # Deny eligibility
        response = client.post(url, data={
            'status': 'Denied',
            'justification': 'PI not eligible for faculty storage'
        })

        # Should redirect
        assert response.status_code == 302

        # Check request was denied
        request.refresh_from_db()
        assert request.status.name == 'Denied'
        assert request.state['eligibility']['status'] == 'Denied'
        assert request.state['eligibility']['justification'] == \
            'PI not eligible for faculty storage'

    def test_post_redirects_to_detail_view(
        self, client, staff_user, test_project, test_pi, test_user
    ):
        """Test successful POST redirects to request detail view."""
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        client.force_login(staff_user)
        url = reverse('faculty-storage-allocation-request-review-eligibility',
                     kwargs={'pk': request.pk})

        response = client.post(url, data={
            'status': 'Approved',
            'justification': ''
        })

        assert response.status_code == 302
        assert f'/faculty-storage-allocation-requests/{request.pk}/' in response.url


@pytest.mark.component
class TestFSARequestReviewIntakeConsistencyView:
    """Test intake consistency review view unique behavior."""

    def test_get_displays_intake_consistency_review_form(
        self, client, staff_user, test_project, test_pi, test_user
    ):
        """Test GET displays intake consistency review form."""
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        client.force_login(staff_user)
        url = reverse('faculty-storage-allocation-request-review-intake-consistency',
                     kwargs={'pk': request.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert 'form' in response.context
        # Check for intake-specific text
        content = response.content.decode()
        assert 'intake' in content.lower()

    def test_approving_intake_when_eligibility_approved_moves_to_queued(
        self, client, staff_user, test_project, test_pi, test_user
    ):
        """Test approving intake when eligibility approved changes status to Approved - Queued."""
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Pre-approve eligibility
        request.state['eligibility']['status'] = 'Approved'
        request.save()

        client.force_login(staff_user)
        url = reverse('faculty-storage-allocation-request-review-intake-consistency',
                     kwargs={'pk': request.pk})

        # Approve intake consistency
        response = client.post(url, data={
            'status': 'Approved',
            'justification': ''
        })

        # Check status changed
        request.refresh_from_db()
        assert request.status.name == 'Approved - Queued'
        assert request.state['intake_consistency']['status'] == 'Approved'

    def test_denying_intake_denies_entire_request(
        self, client, staff_user, test_project, test_pi, test_user
    ):
        """Test denying intake consistency immediately denies the entire request."""
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        client.force_login(staff_user)
        url = reverse('faculty-storage-allocation-request-review-intake-consistency',
                     kwargs={'pk': request.pk})

        # Deny intake consistency
        response = client.post(url, data={
            'status': 'Denied',
            'justification': 'Amount does not match external form'
        })

        # Check request was denied
        request.refresh_from_db()
        assert request.status.name == 'Denied'
        assert request.state['intake_consistency']['status'] == 'Denied'


@pytest.mark.component
class TestFSARequestReviewSetupView:
    """Test setup review view unique behavior."""

    def test_get_displays_setup_form(
        self, client, staff_user, test_project, test_pi, test_user
    ):
        """Test GET displays setup form."""
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Need to approve both reviews for setup to be accessible
        request.state['eligibility']['status'] = 'Approved'
        request.state['intake_consistency']['status'] = 'Approved'
        request.save()

        client.force_login(staff_user)
        url = reverse('faculty-storage-allocation-request-review-setup',
                     kwargs={'pk': request.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert 'form' in response.context

    def test_completing_setup_sets_directory_name(
        self, client, staff_user, test_project, test_pi, test_user
    ):
        """Test completing setup sets directory name in state."""
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Approve both reviews
        request.state['eligibility']['status'] = 'Approved'
        request.state['intake_consistency']['status'] = 'Approved'
        request.save()

        client.force_login(staff_user)
        url = reverse('faculty-storage-allocation-request-review-setup',
                     kwargs={'pk': request.pk})

        # Complete setup
        response = client.post(url, data={
            'status': 'Complete',
        })

        # Check setup was completed with directory name
        request.refresh_from_db()
        assert request.state['setup']['status'] == 'Complete'
        # Directory name should be set to project name
        assert request.state['setup']['directory_name'] == test_project.name

    def test_setup_form_pre_populates_with_project_name(
        self, client, staff_user, test_project, test_pi, test_user
    ):
        """Test setup form initial data includes project name as directory."""
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Approve both reviews
        request.state['eligibility']['status'] = 'Approved'
        request.state['intake_consistency']['status'] = 'Approved'
        request.save()

        client.force_login(staff_user)
        url = reverse('faculty-storage-allocation-request-review-setup',
                     kwargs={'pk': request.pk})
        response = client.get(url)

        # Check initial data
        form = response.context['form']
        assert form.initial.get('directory_name') == test_project.name


@pytest.mark.component
class TestFSARequestEditView:
    """Test storage amount edit view unique behavior."""

    def test_get_displays_edit_form(
        self, client, staff_user, test_project, test_pi, test_user
    ):
        """Test GET displays edit form for Under Review requests."""
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=2000
        )

        client.force_login(staff_user)
        url = reverse('faculty-storage-allocation-request-edit', kwargs={'pk': request.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert 'form' in response.context

    def test_can_only_edit_when_under_review(
        self, client, staff_user, test_project, test_pi, test_user
    ):
        """Test edit view only allows editing when status is Under Review."""
        request = create_fsa_request(
            status='Approved - Queued',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=2000
        )

        client.force_login(staff_user)
        url = reverse('faculty-storage-allocation-request-edit', kwargs={'pk': request.pk})
        response = client.get(url)

        # Should redirect with error message
        assert response.status_code == 302
        assert f'/faculty-storage-allocation-requests/{request.pk}/' in response.url

    def test_post_updates_approved_amount(
        self, client, staff_user, test_project, test_pi, test_user
    ):
        """Test POST updates the approved storage amount."""
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=2000
        )

        client.force_login(staff_user)
        url = reverse('faculty-storage-allocation-request-edit', kwargs={'pk': request.pk})

        # Change amount to 3 TB
        response = client.post(url, data={'storage_amount': 3})

        # Check amount was updated
        request.refresh_from_db()
        assert request.approved_amount_gb == 3000


@pytest.mark.component
class TestFSARequestReviewDenyView:
    """Test deny view for 'other' reasons."""

    def test_get_displays_deny_form(
        self, client, staff_user, test_project, test_pi, test_user
    ):
        """Test GET displays deny form."""
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        client.force_login(staff_user)
        url = reverse('faculty-storage-allocation-request-deny', kwargs={'pk': request.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert 'form' in response.context

    def test_post_denies_request_with_other_reason(
        self, client, staff_user, test_project, test_pi, test_user
    ):
        """Test POST denies request with 'other' reason."""
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        client.force_login(staff_user)
        url = reverse('faculty-storage-allocation-request-deny', kwargs={'pk': request.pk})

        # Deny with other reason
        response = client.post(url, data={
            'justification': 'Some other administrative reason'
        })

        # Check request was denied
        request.refresh_from_db()
        assert request.status.name == 'Denied'
        assert request.state['other']['justification'] == \
            'Some other administrative reason'


@pytest.mark.component
class TestFSARequestUndenyView:
    """Test undeny view."""

    def test_undeny_denied_request_returns_to_under_review(
        self, client, staff_user, test_project, test_pi, test_user
    ):
        """Test undenying a denied request returns it to Under Review."""
        request = create_fsa_request(
            status='Denied',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Set a denial reason
        request.state['eligibility']['status'] = 'Denied'
        request.save()

        client.force_login(staff_user)
        url = reverse('faculty-storage-allocation-request-undeny', kwargs={'pk': request.pk})

        # Undeny the request
        response = client.get(url)

        # Should redirect to detail
        assert response.status_code == 302

        # Check status changed back to Under Review
        request.refresh_from_db()
        assert request.status.name == 'Under Review'

    def test_cannot_undeny_non_denied_request(
        self, client, staff_user, test_project, test_pi, test_user
    ):
        """Test cannot undeny a request that isn't denied."""
        request = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        client.force_login(staff_user)
        url = reverse('faculty-storage-allocation-request-undeny', kwargs={'pk': request.pk})

        # Try to undeny
        response = client.get(url)

        # Should redirect with error
        assert response.status_code == 302

        # Status should remain unchanged
        request.refresh_from_db()
        assert request.status.name == 'Under Review'


@pytest.mark.component
class TestFSARequestListView:
    """Test FSA request list view."""

    def test_superuser_can_access_list(
        self, client, test_project, test_pi, test_user
    ):
        """Test superusers can access request list."""
        # Create some requests
        create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        superuser = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='adminpass'
        )
        client.force_login(superuser)

        url = reverse('faculty-storage-allocation-request-list')
        response = client.get(url)

        assert response.status_code == 200
        assert 'fsa_requests' in response.context

    def test_staff_with_view_permission_can_access(
        self, client, test_project, test_pi, test_user
    ):
        """Test staff with can_view_all permission can access list."""
        from django.contrib.auth.models import Permission

        create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Create staff user with view permission
        staff_user = User.objects.create_user(
            username='staff',
            email='staff@test.com',
            password='staffpass',
            is_staff=True
        )
        permission = Permission.objects.get(
            codename='can_view_all_fsa_requests'
        )
        staff_user.user_permissions.add(permission)

        client.force_login(staff_user)

        url = reverse('faculty-storage-allocation-request-list')
        response = client.get(url)

        assert response.status_code == 200

    def test_regular_user_denied_access_to_list(
        self, client, test_user
    ):
        """Test regular users cannot access request list."""
        client.force_login(test_user)

        url = reverse('faculty-storage-allocation-request-list')
        response = client.get(url)

        # Should be denied
        assert response.status_code in [302, 403]

    def test_list_displays_multiple_requests(
        self, client, test_project, test_pi, test_user
    ):
        """Test list view displays multiple requests."""
        # Create multiple requests
        request1 = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )
        request2 = create_fsa_request(
            status='Denied',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=2000
        )

        superuser = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='adminpass'
        )
        client.force_login(superuser)

        url = reverse('faculty-storage-allocation-request-list')
        response = client.get(url)

        # Check both requests are in context
        fsa_requests = response.context['fsa_requests']
        assert request1 in fsa_requests
        assert request2 in fsa_requests

    def test_list_filters_by_status(
        self, client, test_project, test_pi, test_user
    ):
        """Test list view can filter by status."""
        # Create requests with different statuses
        request1 = create_fsa_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )
        request2 = create_fsa_request(
            status='Denied',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=2000
        )

        superuser = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='adminpass'
        )
        client.force_login(superuser)

        # Filter by 'Under Review'
        url = reverse('faculty-storage-allocation-request-list') + '?status=Under Review'
        response = client.get(url)

        fsa_requests = list(response.context['fsa_requests'])
        assert request1 in fsa_requests
        assert request2 not in fsa_requests
