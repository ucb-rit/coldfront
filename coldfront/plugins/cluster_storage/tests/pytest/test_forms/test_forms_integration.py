"""Component tests for forms with database."""

import pytest
from django.utils import timezone

from coldfront.plugins.cluster_storage.forms.form_utils import (
    ReviewStatusForm,
    ReviewDenyForm,
)
from coldfront.plugins.cluster_storage.forms.approval_forms import (
    StorageRequestSearchForm,
    StorageRequestEditForm,
)
from coldfront.plugins.cluster_storage.forms.request_forms import (
    StorageRequestForm,
)
from coldfront.plugins.cluster_storage.models import (
    FacultyStorageAllocationRequest,
)
from coldfront.plugins.cluster_storage.services import (
    FacultyStorageAllocationRequestService,
)
from coldfront.plugins.cluster_storage.tests.pytest.utils import (
    create_storage_request,
)


@pytest.mark.component
class TestReviewStatusFormIntegration:
    """Integration tests for ReviewStatusForm with database."""

    def test_form_with_database_request_data(
        self, test_project, test_user, test_pi
    ):
        """Test form works with real request from database."""
        # Create a request in the database
        request = create_storage_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=2000
        )

        # Use form to approve it
        data = {'status': 'Approved', 'justification': ''}
        form = ReviewStatusForm(data=data)

        assert form.is_valid()

        # Manually apply the form's validated data to update the request
        FacultyStorageAllocationRequestService.update_eligibility_state(
            request,
            form.cleaned_data['status'],
            form.cleaned_data['justification']
        )

        request.refresh_from_db()
        assert request.state['eligibility']['status'] == 'Approved'

    def test_form_validates_with_existing_request_state(
        self, test_project, test_user, test_pi
    ):
        """Test form validation works with existing request state."""
        request = create_storage_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Deny the request
        data = {
            'status': 'Denied',
            'justification': 'PI not eligible for faculty storage'
        }
        form = ReviewStatusForm(data=data)

        assert form.is_valid()

        # Apply the denial
        FacultyStorageAllocationRequestService.update_eligibility_state(
            request,
            form.cleaned_data['status'],
            form.cleaned_data['justification']
        )
        FacultyStorageAllocationRequestService.deny_request(request)

        request.refresh_from_db()
        assert request.status.name == 'Denied'
        assert request.state['eligibility']['status'] == 'Denied'
        assert request.state['eligibility']['justification'] == \
            'PI not eligible for faculty storage'

    def test_form_history_tracking(
        self, test_project, test_user, test_pi
    ):
        """Test request changes are tracked in history."""
        request = create_storage_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1500
        )

        initial_history_count = request.history.count()

        # Update the request
        data = {'status': 'Approved', 'justification': 'All criteria met'}
        form = ReviewStatusForm(data=data)
        assert form.is_valid()

        FacultyStorageAllocationRequestService.update_eligibility_state(
            request,
            form.cleaned_data['status'],
            form.cleaned_data['justification']
        )

        # Check history was created
        assert request.history.count() > initial_history_count

        # Verify the historical record
        latest_history = request.history.first()
        assert latest_history.state['eligibility']['status'] == 'Approved'


@pytest.mark.component
class TestStorageRequestSearchFormIntegration:
    """Integration tests for search form with database."""

    def test_form_initializes_with_database_projects(self, test_project, db):
        """Test form queryset loads projects from database."""
        form = StorageRequestSearchForm()

        # Check that project queryset is populated
        assert form.fields['project'].queryset is not None

        # Projects are filtered by FCA prefix
        projects = form.fields['project'].queryset
        for project in projects:
            assert project.name.startswith('fc_')

    def test_form_initializes_with_database_users(self, test_pi, db):
        """Test form queryset loads users from database."""
        form = StorageRequestSearchForm()

        # Check that PI queryset is populated and excludes users without email
        pi_queryset = form.fields['pi'].queryset
        assert pi_queryset is not None

        # Should include our test PI who has an email
        assert test_pi in pi_queryset

    def test_form_excludes_users_without_email(self, db):
        """Test form excludes users with no email address."""
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Create user without email
        user_no_email = User.objects.create_user(
            username='noemail',
            email='',  # Empty email
            first_name='No',
            last_name='Email'
        )

        form = StorageRequestSearchForm()
        pi_queryset = form.fields['pi'].queryset

        # User without email should be excluded
        assert user_no_email not in pi_queryset

    def test_form_filters_requests_by_status(
        self, test_project, test_user, test_pi
    ):
        """Test form can be used to filter requests by status."""
        # Create requests with different statuses
        request1 = create_storage_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=1000
        )

        request2 = create_storage_request(
            status='Denied',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=2000
        )

        # Use form to filter by status
        data = {'status': 'Under Review'}
        form = StorageRequestSearchForm(data=data)

        assert form.is_valid()

        # Manually apply the filter (form doesn't do this automatically)
        filtered = FacultyStorageAllocationRequest.objects.filter(
            status__name=form.cleaned_data['status']
        )

        assert request1 in filtered
        assert request2 not in filtered


@pytest.mark.component
class TestStorageRequestEditFormIntegration:
    """Integration tests for edit form with database."""

    def test_form_updates_request_amount_in_database(
        self, test_project, test_user, test_pi
    ):
        """Test form can update storage amount in database."""
        request = create_storage_request(
            status='Under Review',
            project=test_project,
            requester=test_user,
            pi=test_pi,
            requested_amount_gb=2000
        )

        # Change the amount to 4 TB
        data = {'storage_amount': 4}
        form = StorageRequestEditForm(data=data)

        assert form.is_valid()

        # Update the request (converting TB to GB)
        new_amount_gb = int(form.cleaned_data['storage_amount']) * 1000
        request.requested_amount_gb = new_amount_gb
        request.save()

        request.refresh_from_db()
        assert request.requested_amount_gb == 4000

    def test_form_validates_against_database_constraints(self):
        """Test form validation respects storage amount constraints."""
        # Test various amounts
        valid_amounts = [1, 2, 3, 4, 5]

        for amount in valid_amounts:
            data = {'storage_amount': amount}
            form = StorageRequestEditForm(data=data)
            assert form.is_valid(), f"{amount} TB should be valid"

        # Invalid amount
        data = {'storage_amount': 10}
        form = StorageRequestEditForm(data=data)
        assert not form.is_valid()


@pytest.mark.component
class TestStorageRequestFormIntegration:
    """Integration tests for request creation form."""

    def test_form_initializes_with_project_data(
        self, test_project, test_user, test_pi,
        project_user_role_pi, project_user_status_active
    ):
        """Test form loads PI choices from project in database."""
        from coldfront.core.project.models import ProjectUser

        # Create a ProjectUser for the PI
        pi_project_user = ProjectUser.objects.create(
            project=test_project,
            user=test_pi,
            role=project_user_role_pi,
            status=project_user_status_active
        )

        # Initialize form with project
        form = StorageRequestForm(project_pk=test_project.pk)

        # Check that PI queryset includes our project user
        assert pi_project_user in form.fields['pi'].queryset

    def test_form_disables_ineligible_pis(
        self, test_project, test_pi,
        project_user_role_pi, project_user_status_active
    ):
        """Test form disables PIs who are not eligible for storage."""
        from coldfront.core.project.models import ProjectUser

        # Create a ProjectUser for the PI
        pi_project_user = ProjectUser.objects.create(
            project=test_project,
            user=test_pi,
            role=project_user_role_pi,
            status=project_user_status_active
        )

        # Create an existing storage request for this PI (makes them ineligible)
        create_storage_request(
            status='Under Review',
            project=test_project,
            requester=test_pi,
            pi=test_pi,
            requested_amount_gb=1000
        )

        # Initialize form - should disable this PI
        form = StorageRequestForm(project_pk=test_project.pk)

        # Check that this PI is in disabled choices
        assert pi_project_user.pk in \
            form.fields['pi'].widget.disabled_choices

    def test_form_validation_with_valid_data(
        self, test_project, test_pi,
        project_user_role_pi, project_user_status_active
    ):
        """Test form validates with valid project and PI data."""
        from coldfront.core.project.models import ProjectUser

        pi_project_user = ProjectUser.objects.create(
            project=test_project,
            user=test_pi,
            role=project_user_role_pi,
            status=project_user_status_active
        )

        data = {
            'pi': pi_project_user.pk,
            'storage_amount': 3,
            'confirm_external_intake': True
        }
        form = StorageRequestForm(data=data, project_pk=test_project.pk)

        assert form.is_valid()
        assert form.cleaned_data['pi'] == pi_project_user
        assert form.cleaned_data['storage_amount'] == '3'

    def test_form_requires_external_intake_confirmation(
        self, test_project, test_pi,
        project_user_role_pi, project_user_status_active
    ):
        """Test form requires external intake confirmation checkbox."""
        from coldfront.core.project.models import ProjectUser

        pi_project_user = ProjectUser.objects.create(
            project=test_project,
            user=test_pi,
            role=project_user_role_pi,
            status=project_user_status_active
        )

        # Without confirmation
        data = {
            'pi': pi_project_user.pk,
            'storage_amount': 2,
            'confirm_external_intake': False
        }
        form = StorageRequestForm(data=data, project_pk=test_project.pk)

        assert not form.is_valid()
        assert 'confirm_external_intake' in form.errors

    def test_form_only_shows_active_pi_project_users(
        self, test_project, test_pi,
        project_user_role_pi, project_user_status_active
    ):
        """Test form only includes active PIs."""
        from coldfront.core.project.models import (
            ProjectUser,
            ProjectUserStatusChoice
        )

        # Create an active PI
        active_pi = ProjectUser.objects.create(
            project=test_project,
            user=test_pi,
            role=project_user_role_pi,
            status=project_user_status_active
        )

        # Create an inactive PI
        from django.contrib.auth import get_user_model
        User = get_user_model()
        inactive_user = User.objects.create_user(
            username='inactive_pi',
            email='inactive@test.com'
        )

        removed_status = ProjectUserStatusChoice.objects.get(name='Removed')
        inactive_pi = ProjectUser.objects.create(
            project=test_project,
            user=inactive_user,
            role=project_user_role_pi,
            status=removed_status
        )

        # Initialize form
        form = StorageRequestForm(project_pk=test_project.pk)

        # Active PI should be in queryset
        assert active_pi in form.fields['pi'].queryset

        # Inactive PI should NOT be in queryset
        assert inactive_pi not in form.fields['pi'].queryset
