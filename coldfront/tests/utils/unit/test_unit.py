"""
Whitebox tests for tracking framework integration.
Tests internal behavior, data loading, and component interactions.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from coldfront.core.project.utils_.join_request_tracker import (
    JoinRequestTracker, JoinRequestStatus
)
from coldfront.core.project.models import (
    ProjectUserStatusChoice, ProjectUserRoleChoice
)
from coldfront.core.allocation.models import (
    ClusterAccessRequest, ClusterAccessRequestStatusChoice
)


# ============================================================================
# JoinRequestTracker Data Loading Tests
# ============================================================================

class TestJoinRequestTrackerDataLoading:
    """Tests for JoinRequestTracker data loading behavior."""

    @pytest.mark.django_db
    @pytest.mark.whitebox
    def test_load_data_no_project_user(self, user, project):
        """Test data loading when no ProjectUser exists."""
        tracker = JoinRequestTracker(user, project)

        tracker._load_data()

        assert tracker._project_user is None
        assert tracker._join_request is None
        assert tracker._cluster_access_request is None

    @pytest.mark.django_db
    @pytest.mark.whitebox
    def test_load_data_with_project_user_no_join_request(self, active_project_user):
        """Test data loading with ProjectUser but no join request."""
        tracker = JoinRequestTracker(active_project_user.user, active_project_user.project)

        tracker._load_data()

        assert tracker._project_user == active_project_user
        assert tracker._join_request is None

    @pytest.mark.django_db
    @pytest.mark.whitebox
    def test_load_data_with_join_request(self, join_request):
        """Test data loading with join request."""
        project_user = join_request.project_user
        tracker = JoinRequestTracker(project_user.user, project_user.project)

        tracker._load_data()

        assert tracker._project_user == project_user
        assert tracker._join_request == join_request

    @pytest.mark.django_db
    @pytest.mark.whitebox
    def test_load_data_with_allocation_and_cluster_request(
            self, allocation_user, project_user_factory
    ):
        """Test data loading with allocation and cluster access request."""
        # Create project user for the same user and project
        project_user = project_user_factory(
            user=allocation_user.user,
            project=allocation_user.allocation.project,
            status=ProjectUserStatusChoice.objects.get_or_create(name='Active')[0]
        )

        # Create cluster access request status
        cluster_status = ClusterAccessRequestStatusChoice.objects.get_or_create(
            name='Pending - Add'
        )[0]

        # Create cluster access request
        cluster_request = ClusterAccessRequest.objects.create(
            allocation_user=allocation_user,
            status=cluster_status
        )

        tracker = JoinRequestTracker(project_user.user, project_user.project)

        tracker._load_data()

        assert tracker._project_user == project_user
        assert tracker._cluster_access_request == cluster_request

    @pytest.mark.django_db
    @pytest.mark.whitebox
    def test_load_data_multiple_join_requests_gets_latest(self, pending_project_user):
        """Test that the latest join request is loaded when multiple exist."""
        from coldfront.core.project.models import ProjectUserJoinRequest

        # Create multiple join requests
        older_request = ProjectUserJoinRequest.objects.create(
            project_user=pending_project_user,
            reason="Older request",
            created=datetime(2024, 1, 1)
        )
        newer_request = ProjectUserJoinRequest.objects.create(
            project_user=pending_project_user,
            reason="Newer request",
            created=datetime(2024, 2, 1)
        )

        tracker = JoinRequestTracker(pending_project_user.user, pending_project_user.project)

        tracker._load_data()

        assert tracker._join_request == newer_request


# ============================================================================
# JoinRequestTracker Status Determination Tests
# ============================================================================

class TestJoinRequestTrackerStatusDetermination:
    """Tests for status determination logic."""

    @pytest.mark.django_db
    @pytest.mark.whitebox
    @pytest.mark.parametrize("project_user_status,join_request_exists,expected_status", [
        (None, False, JoinRequestStatus.NO_REQUEST),
        ('Pending - Add', True, JoinRequestStatus.REQUEST_SENT),
        ('Denied', True, JoinRequestStatus.NO_REQUEST),
        ('Active', False, JoinRequestStatus.DIRECTLY_ADDED),
    ])
    def test_determine_status_basic_scenarios(
            self, user, project, project_user_status, join_request_exists, expected_status
    ):
        """Test basic status determination scenarios."""
        tracker = JoinRequestTracker(user, project)

        # Set up the tracker's internal state
        if project_user_status:
            mock_project_user = Mock()
            mock_project_user.status.name = project_user_status
            tracker._project_user = mock_project_user
        else:
            tracker._project_user = None

        tracker._join_request = Mock() if join_request_exists else None
        tracker._cluster_access_request = None

        status = tracker._determine_status()

        assert status == expected_status

    @pytest.mark.django_db
    @pytest.mark.whitebox
    @pytest.mark.parametrize("cluster_status,expected_status", [
        ('Pending - Add', JoinRequestStatus.PI_APPROVED_QUEUED),
        ('Processing', JoinRequestStatus.ADMIN_PROCESSING),
        ('Complete', JoinRequestStatus.ACCESS_GRANTED),
        ('Denied', JoinRequestStatus.PI_APPROVED_QUEUED),
    ])
    def test_determine_status_with_cluster_access(
            self, user, project, cluster_status, expected_status
    ):
        """Test status determination with cluster access requests."""
        tracker = JoinRequestTracker(user, project)

        # Set up active project user with join request
        mock_project_user = Mock()
        mock_project_user.status.name = 'Active'
        tracker._project_user = mock_project_user
        tracker._join_request = Mock()

        # Set up cluster access request
        mock_cluster_request = Mock()
        mock_cluster_request.status.name = cluster_status
        tracker._cluster_access_request = mock_cluster_request

        status = tracker._determine_status()

        assert status == expected_status

    @pytest.mark.django_db
    @pytest.mark.whitebox
    def test_determine_status_active_user_no_cluster_request(self, user, project):
        """Test status for active user without cluster access request."""
        tracker = JoinRequestTracker(user, project)

        mock_project_user = Mock()
        mock_project_user.status.name = 'Active'
        tracker._project_user = mock_project_user
        tracker._join_request = Mock()
        tracker._cluster_access_request = None

        status = tracker._determine_status()

        assert status == JoinRequestStatus.PI_APPROVED_QUEUED


# ============================================================================
# JoinRequestTracker Message and Details Tests
# ============================================================================

class TestJoinRequestTrackerMessagesAndDetails:
    """Tests for status messages and details."""

    @pytest.mark.whitebox
    @pytest.mark.parametrize("status,expected_message_contains", [
        (JoinRequestStatus.REQUEST_SENT, "awaiting approval"),
        (JoinRequestStatus.PI_APPROVED_QUEUED, "queued for cluster access"),
        (JoinRequestStatus.ADMIN_PROCESSING, "processing your cluster access"),
        (JoinRequestStatus.ACCESS_GRANTED, "granted access"),
        (JoinRequestStatus.DIRECTLY_ADDED, "directly added"),
        (JoinRequestStatus.ERROR, "Unable to determine"),
        (JoinRequestStatus.NO_REQUEST, "No active request"),
    ])
    def test_get_status_message(self, user, project, status, expected_message_contains):
        """Test status message generation."""
        tracker = JoinRequestTracker(user, project)

        message = tracker._get_status_message(status)

        assert expected_message_contains.lower() in message.lower()

    @pytest.mark.whitebox
    def test_get_status_details_with_all_data(self, user, project):
        """Test status details with all available data."""
        tracker = JoinRequestTracker(user, project)

        # Mock all data components
        mock_join_request = Mock()
        mock_join_request.created = datetime(2024, 1, 1)
        mock_join_request.reason = "Test reason"
        tracker._join_request = mock_join_request

        mock_project_user = Mock()
        mock_project_user.status.name = 'Active'
        mock_project_user.role.name = 'User'
        tracker._project_user = mock_project_user

        mock_cluster_request = Mock()
        mock_cluster_request.status.name = 'Complete'
        mock_cluster_request.request_time = datetime(2024, 1, 2)
        tracker._cluster_access_request = mock_cluster_request

        details = tracker._get_status_details(JoinRequestStatus.ACCESS_GRANTED)

        assert details['request_date'] == datetime(2024, 1, 1)
        assert details['reason'] == "Test reason"
        assert details['project_user_status'] == 'Active'
        assert details['role'] == 'User'
        assert details['cluster_request_status'] == 'Complete'
        assert details['cluster_request_date'] == datetime(2024, 1, 2)

    @pytest.mark.whitebox
    def test_get_status_details_no_data(self, user, project):
        """Test status details with no data."""
        tracker = JoinRequestTracker(user, project)

        # No data set
        tracker._join_request = None
        tracker._project_user = None
        tracker._cluster_access_request = None

        details = tracker._get_status_details(JoinRequestStatus.NO_REQUEST)

        assert details is None


# ============================================================================
# JoinRequestTracker Progress Steps Tests
# ============================================================================

class TestJoinRequestTrackerProgressSteps:
    """Tests for progress step generation."""

    @pytest.mark.whitebox
    def test_get_progress_steps_directly_added(self, user, project):
        """Test progress steps for directly added users."""
        tracker = JoinRequestTracker(user, project)

        # Mock cluster access request as complete
        mock_cluster_request = Mock()
        mock_cluster_request.status.name = 'Complete'
        tracker._cluster_access_request = mock_cluster_request

        steps = tracker._get_progress_steps(JoinRequestStatus.DIRECTLY_ADDED)

        assert len(steps) == 3
        assert steps[0].label == 'Directly Added by PI'
        assert steps[0].completed is True
        assert steps[0].current is False

        assert steps[1].label == 'Admin Processing'
        assert steps[1].completed is True
        assert steps[1].current is False

        assert steps[2].label == 'Access Granted'
        assert steps[2].completed is True
        assert steps[2].current is False

    @pytest.mark.whitebox
    @pytest.mark.parametrize("current_status,expected_step_states", [
        (JoinRequestStatus.REQUEST_SENT, [
            ('Request Sent', True, True),  # completed=True because status != 'No Request'
            ('PI Approved & Queued', False, False),
            ('Admin Processing', False, False),
            ('Access Granted', False, False)
        ]),
        (JoinRequestStatus.PI_APPROVED_QUEUED, [
            ('Request Sent', True, False),
            ('PI Approved & Queued', True, True),  # completed=True because in approved states
            ('Admin Processing', False, False),
            ('Access Granted', False, False)
        ]),
        (JoinRequestStatus.ADMIN_PROCESSING, [
            ('Request Sent', True, False),
            ('PI Approved & Queued', True, False),  # completed=True because in processing states
            ('Admin Processing', True, True),  # completed=True because in processing states
            ('Access Granted', False, False)
        ]),
        (JoinRequestStatus.ACCESS_GRANTED, [
            ('Request Sent', True, False),
            ('PI Approved & Queued', True, False),
            ('Admin Processing', True, False),
            ('Access Granted', True, False)
        ])
    ])
    def test_get_progress_steps_standard_flow(
            self, user, project, current_status, expected_step_states
    ):
        """Test progress steps for standard join request flow."""
        tracker = JoinRequestTracker(user, project)

        steps = tracker._get_progress_steps(current_status)

        assert len(steps) == 4
        for i, (label, completed, current) in enumerate(expected_step_states):
            assert steps[i].label == label
            assert steps[i].completed == completed
            assert steps[i].current == current


# ============================================================================
# JoinRequestTracker Permission Tests
# ============================================================================

class TestJoinRequestTrackerPermissions:
    """Tests for view permission logic."""

    @pytest.mark.whitebox
    def test_can_view_status_with_project_user(self, user, project):
        """Test can_view_status returns True when project user exists."""
        tracker = JoinRequestTracker(user, project)
        tracker._project_user = Mock()  # Any project user

        can_view = tracker._can_view_status()

        assert can_view is True

    @pytest.mark.whitebox
    def test_can_view_status_no_project_user(self, user, project):
        """Test can_view_status returns False when no project user exists."""
        tracker = JoinRequestTracker(user, project)
        tracker._project_user = None

        can_view = tracker._can_view_status()

        assert can_view is False


# ============================================================================
# JoinRequestTracker Error Handling Tests
# ============================================================================

class TestJoinRequestTrackerErrorHandling:
    """Tests for error handling behavior."""

    @pytest.mark.whitebox
    def test_get_error_status(self, user, project):
        """Test get_error_status returns correct enum."""
        tracker = JoinRequestTracker(user, project)

        error_status = tracker.get_error_status()

        assert error_status == JoinRequestStatus.ERROR

    @pytest.mark.whitebox
    def test_get_default_error_message(self, user, project):
        """Test default error message."""
        tracker = JoinRequestTracker(user, project)

        error_message = tracker.get_default_error_message()

        assert "join status" in error_message.lower()
        assert "contact support" in error_message.lower()

    @pytest.mark.django_db
    @pytest.mark.whitebox
    @patch('coldfront.core.utils.tracking.base.logger')
    def test_get_status_handles_load_data_exception(self, mock_logger, user, project):
        """Test that get_status handles exceptions in _load_data."""
        tracker = JoinRequestTracker(user, project)

        # Make _load_data raise an exception
        def raise_error():
            raise ValueError("Database error")

        tracker._load_data = raise_error

        result = tracker.get_status()

        assert result['status'] == JoinRequestStatus.ERROR
        assert result['error'] is not None
        mock_logger.exception.assert_called_once()


# ============================================================================
# JoinRequestTracker Backward Compatibility Tests
# ============================================================================

class TestJoinRequestTrackerBackwardCompatibility:
    """Tests for backward compatibility with existing API."""

    @pytest.mark.django_db
    @pytest.mark.whitebox
    def test_get_status_returns_dict(self, user, project):
        """Test that get_status returns a dict for backward compatibility."""
        tracker = JoinRequestTracker(user, project)

        result = tracker.get_status()

        assert isinstance(result, dict)
        assert 'status' in result
        assert 'message' in result
        assert 'details' in result
        assert 'error' in result
        assert 'steps' in result
        assert 'can_view' in result

    @pytest.mark.django_db
    @pytest.mark.whitebox
    def test_get_status_dict_structure(self, active_project_user):
        """Test the structure of the returned status dict."""
        tracker = JoinRequestTracker(active_project_user.user, active_project_user.project)

        result = tracker.get_status()

        # Test that steps are properly converted to dicts
        assert isinstance(result['steps'], list)
        if result['steps']:
            step = result['steps'][0]
            assert isinstance(step, dict)
            assert 'label' in step
            assert 'completed' in step
            assert 'current' in step