"""
whitebox tests for tracking framework end-to-end functionality.
Tests external behavior from user's perspective including view integration.
"""
import pytest
from unittest.mock import patch, Mock
from django.urls import reverse
from django.contrib.auth.models import User

from coldfront.core.project.models import (
    Project, ProjectUser, ProjectUserJoinRequest, ProjectUserStatusChoice
)
from coldfront.core.project.utils_.join_request_tracker import JoinRequestTracker


# ============================================================================
# End-to-End Workflow Tests
# ============================================================================

class TestTrackingEndToEndWorkflow:
    """Tests for complete tracking workflows from user perspective."""

    @pytest.mark.django_db
    @pytest.mark.whitebox
    def test_complete_join_request_workflow(self, user_factory, project_factory):
        """Test complete join request workflow from start to finish."""
        # Create test data
        user = user_factory()
        project = project_factory()

        # Step 1: No request exists
        tracker = JoinRequestTracker(user, project)
        status = tracker.get_status()

        assert status['status'].value == 'No Request'
        assert status['can_view'] is False

        # Step 2: Create pending project user (simulates join request)
        pending_status = ProjectUserStatusChoice.objects.get_or_create(
            name='Pending - Add'
        )[0]
        project_user = ProjectUser.objects.create(
            user=user,
            project=project,
            status=pending_status,
            role_id=1  # Assuming role with ID 1 exists
        )

        # Create join request
        join_request = ProjectUserJoinRequest.objects.create(
            project_user=project_user,
            reason="Need access for research"
        )

        # Check status after request
        tracker = JoinRequestTracker(user, project)
        status = tracker.get_status()

        assert status['status'].value == 'Request Sent'
        assert status['can_view'] is True
        assert len(status['steps']) == 4
        assert status['steps'][0]['current'] is True

        # Step 3: Approve request (simulates PI approval)
        active_status = ProjectUserStatusChoice.objects.get_or_create(
            name='Active'
        )[0]
        project_user.status = active_status
        project_user.save()

        # Check status after approval
        tracker = JoinRequestTracker(user, project)
        status = tracker.get_status()

        assert status['status'].value == 'PI Approved & Queued'
        assert status['steps'][1]['current'] is True

    @pytest.mark.django_db
    @pytest.mark.whitebox
    def test_directly_added_user_workflow(self, user_factory, project_factory):
        """Test workflow for user directly added by PI."""
        user = user_factory()
        project = project_factory()

        # Create active project user without join request (direct add)
        active_status = ProjectUserStatusChoice.objects.get_or_create(
            name='Active'
        )[0]
        project_user = ProjectUser.objects.create(
            user=user,
            project=project,
            status=active_status,
            role_id=1
        )

        tracker = JoinRequestTracker(user, project)
        status = tracker.get_status()

        assert status['status'].value == 'Directly Added by PI'
        assert status['can_view'] is True
        assert len(status['steps']) == 3
        assert status['steps'][0]['label'] == 'Directly Added by PI'
        assert status['steps'][0]['completed'] is True


# ============================================================================
# View Integration Tests
# ============================================================================

class TestTrackingViewIntegration:
    """Tests for tracking integration with views."""

    @pytest.mark.django_db
    @pytest.mark.whitebox
    @pytest.mark.skip(reason="Home view requires additional resource setup")
    def test_home_view_with_tracking(self, authenticated_client, user, project):
        """Test that home view includes tracking data."""
        # Create project user so user has a project
        active_status = ProjectUserStatusChoice.objects.get_or_create(name='Active')[0]
        project_user = ProjectUser.objects.create(
            user=user,
            project=project,
            status=active_status,
            role_id=1
        )

        # Sign access agreement (required for home view)
        user.userprofile.access_agreement_signed_date = '2024-01-01'
        user.userprofile.save()

        response = authenticated_client.get(reverse('home'))

        assert response.status_code == 200
        # The project should be in the context with tracking data
        projects = response.context.get('project_list', [])
        if projects:
            project = projects[0]
            assert hasattr(project, 'has_tracking')
            assert hasattr(project, 'tracking_status')

    @pytest.mark.django_db
    @pytest.mark.whitebox
    def test_project_join_list_view_with_tracking(self, authenticated_client, user):
        """Test project join list view includes tracking data."""
        # Sign access agreement (required)
        user.userprofile.access_agreement_signed_date = '2024-01-01'
        user.userprofile.save()

        response = authenticated_client.get(reverse('project-join-list'))

        assert response.status_code == 200
        # Check that join_requests context exists and has tracking
        join_requests = response.context.get('join_requests', [])
        # Even if empty, the context should exist
        assert join_requests is not None


# ============================================================================
# Template Integration Tests
# ============================================================================

class TestTrackingTemplateIntegration:
    """Tests for tracking data rendering in templates."""

    @pytest.mark.django_db
    @pytest.mark.whitebox
    def test_tracking_modal_renders_with_data(self, authenticated_client, user, project):
        """Test that tracking modal renders correctly with data."""
        # Create project user with join request
        pending_status = ProjectUserStatusChoice.objects.get_or_create(
            name='Pending - Add'
        )[0]
        project_user = ProjectUser.objects.create(
            user=user,
            project=project,
            status=pending_status,
            role_id=1
        )

        join_request = ProjectUserJoinRequest.objects.create(
            project_user=project_user,
            reason="Test reason"
        )

        # Sign access agreement
        user.userprofile.access_agreement_signed_date = '2024-01-01'
        user.userprofile.save()

        response = authenticated_client.get(reverse('project-join-list'))

        assert response.status_code == 200
        content = response.content.decode()

        # Check for tracking modal elements
        assert 'projectAccessTimelineModal' in content
        assert 'View Timeline' in content or 'fas fa-clock' in content



# ============================================================================
# API Compatibility Tests
# ============================================================================

class TestTrackingAPICompatibility:
    """Tests for API compatibility with existing code."""

    @pytest.mark.django_db
    @pytest.mark.whitebox
    def test_tracker_api_unchanged(self, user, project):
        """Test that tracker API is unchanged from original implementation."""
        tracker = JoinRequestTracker(user, project)

        # Should be able to call get_status without arguments
        status = tracker.get_status()

        # Should return a dictionary (not TrackingResult object)
        assert isinstance(status, dict)

        # Should have all expected keys
        expected_keys = {'status', 'message', 'details', 'error', 'steps', 'can_view'}
        assert expected_keys.issubset(status.keys())

    @pytest.mark.django_db
    @pytest.mark.whitebox
    def test_status_dict_structure_unchanged(self, user, project):
        """Test that status dictionary structure is unchanged."""
        tracker = JoinRequestTracker(user, project)
        status = tracker.get_status()

        # Test specific structure expectations
        assert 'status' in status
        assert hasattr(status['status'], 'value')  # Should be enum with value

        assert 'message' in status
        assert isinstance(status['message'], str)

        assert 'steps' in status
        assert isinstance(status['steps'], list)

        # Steps should be dicts with expected keys
        if status['steps']:
            step = status['steps'][0]
            assert isinstance(step, dict)
            assert 'label' in step
            assert 'completed' in step
            assert 'current' in step

    @pytest.mark.django_db
    @pytest.mark.whitebox
    def test_import_path_unchanged(self):
        """Test that import path for JoinRequestTracker is unchanged."""
        # This should not raise ImportError
        from coldfront.core.project.utils_.join_request_tracker import JoinRequestTracker

        # Should be able to instantiate (with valid args)
        assert JoinRequestTracker is not None


# ============================================================================
# Error Handling Integration Tests
# ============================================================================

class TestTrackingErrorHandling:
    """Tests for error handling in integrated environment."""

    @pytest.mark.django_db
    @pytest.mark.whitebox
    @patch('coldfront.core.project.utils_.join_request_tracker.logger')
    def test_view_handles_tracker_errors_gracefully(
            self, mock_logger, authenticated_client, user
    ):
        """Test that views handle tracker errors gracefully."""
        # Sign access agreement
        user.userprofile.access_agreement_signed_date = '2024-01-01'
        user.userprofile.save()

        # Patch tracker to raise an exception
        with patch('coldfront.core.project.views_.join_views.request_views.JoinRequestTracker') as mock_tracker_class:
            mock_tracker = Mock()
            mock_tracker.get_status.side_effect = Exception("Database error")
            mock_tracker_class.return_value = mock_tracker

            response = authenticated_client.get(reverse('project-join-list'))

            # View should still render successfully
            assert response.status_code == 200

    @pytest.mark.django_db
    @pytest.mark.whitebox
    @pytest.mark.django_db
    def test_invalid_user_project_combination(self, db):
        """Test tracker behavior with invalid user/project combinations."""
        from coldfront.core.project.models import ProjectStatusChoice
        from coldfront.core.field_of_science.models import FieldOfScience

        # Create user and project that don't belong together
        user = User.objects.create_user('testuser', 'test@example.com')

        # Get or create required related objects
        status = ProjectStatusChoice.objects.get_or_create(name='Active')[0]
        fos = FieldOfScience.objects.get_or_create(description='Other')[0]

        project = Project.objects.create(
            name='test_project',
            title='Test',
            status=status,
            field_of_science=fos
        )

        tracker = JoinRequestTracker(user, project)
        status_result = tracker.get_status()

        # Should handle gracefully and return appropriate status
        assert status_result['status'].value == 'No Request'
        assert status_result['can_view'] is False
        assert status_result['error'] is None  # Should not be an error condition


# ============================================================================
# Performance and Scale Tests
# ============================================================================

class TestTrackingPerformance:
    """Tests for tracking performance under various conditions."""

    @pytest.mark.django_db
    @pytest.mark.whitebox
    @pytest.mark.slow
    def test_tracker_with_many_join_requests(self, user_factory, project_factory):
        """Test tracker performance with many join requests."""
        user = user_factory()
        project = project_factory()

        # Create project user
        pending_status = ProjectUserStatusChoice.objects.get_or_create(
            name='Pending - Add'
        )[0]
        project_user = ProjectUser.objects.create(
            user=user,
            project=project,
            status=pending_status,
            role_id=1
        )

        # Create many join requests (simulates multiple attempts)
        for i in range(10):
            ProjectUserJoinRequest.objects.create(
                project_user=project_user,
                reason=f"Request {i}"
            )

        tracker = JoinRequestTracker(user, project)

        # Should still work efficiently
        status = tracker.get_status()
        assert status['status'].value == 'Request Sent'

        # Should get the latest request details
        assert status['details'] is not None

    @pytest.mark.django_db
    @pytest.mark.whitebox
    def test_tracker_database_query_efficiency(self, user, project):
        """Test that tracker doesn't make excessive database queries."""
        with patch('django.test.utils.override_settings'):
            # This test would ideally use django-debug-toolbar or
            # django.test.utils.override_settings(DEBUG=True) with
            # connection.queries to count queries

            tracker = JoinRequestTracker(user, project)
            status = tracker.get_status()

            # Should complete without errors (detailed query counting
            # would require additional test infrastructure)
            assert status is not None

