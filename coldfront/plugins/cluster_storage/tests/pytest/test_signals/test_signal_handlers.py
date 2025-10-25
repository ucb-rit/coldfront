"""Component tests for signal handlers.

These tests verify that signal handlers respond correctly to core application
events and integrate properly with the DirectoryService.
"""

import pytest
from unittest.mock import Mock, patch
import logging

from coldfront.core.project.utils_.new_project_user_utils import (
    project_user_activated
)
from coldfront.core.allocation.models import AllocationUser
from coldfront.plugins.cluster_storage.services import DirectoryService
from coldfront.plugins.cluster_storage.signals import (
    add_project_user_to_faculty_storage_allocation
)


@pytest.mark.component
class TestProjectUserActivatedSignal:
    """Test project_user_activated signal handler."""

    def test_signal_adds_user_to_faculty_storage_allocation(
        self, test_project, test_user, resource_faculty_storage_directory
    ):
        """Test activating project user adds them to faculty storage
        allocation."""
        # Setup - create faculty storage allocation
        directory_service = DirectoryService(test_project, 'fc_test_dir')
        allocation = directory_service.create_directory()

        # Create mock project_user
        mock_project_user = Mock()
        mock_project_user.project = test_project
        mock_project_user.user = test_user

        # Execute - send signal
        project_user_activated.send(
            sender=None,
            project_user=mock_project_user
        )

        # Assert - user was added to allocation
        allocation_users = AllocationUser.objects.filter(
            allocation=allocation,
            user=test_user
        )
        assert allocation_users.exists()
        assert allocation_users.count() == 1
        assert allocation_users.first().status.name == 'Active'

    def test_signal_is_idempotent(
        self, test_project, test_user, resource_faculty_storage_directory
    ):
        """Test signal can be called multiple times for same user without
        error."""
        # Setup
        directory_service = DirectoryService(test_project, 'fc_test_dir')
        allocation = directory_service.create_directory()

        mock_project_user = Mock()
        mock_project_user.project = test_project
        mock_project_user.user = test_user

        # Execute - send signal twice
        project_user_activated.send(
            sender=None,
            project_user=mock_project_user
        )
        project_user_activated.send(
            sender=None,
            project_user=mock_project_user
        )

        # Assert - still only one AllocationUser
        allocation_users = AllocationUser.objects.filter(
            allocation=allocation,
            user=test_user
        )
        assert allocation_users.count() == 1

    def test_signal_skips_if_no_storage_allocation_exists(
        self, test_project, test_user
    ):
        """Test signal handles case where project has no storage allocation."""
        # Setup - no faculty storage allocation for project
        mock_project_user = Mock()
        mock_project_user.project = test_project
        mock_project_user.user = test_user

        # Execute - send signal (should not raise error)
        project_user_activated.send(
            sender=None,
            project_user=mock_project_user
        )

        # Assert - no AllocationUser created
        allocation_users = AllocationUser.objects.filter(
            user=test_user
        )
        assert allocation_users.count() == 0

    @patch('coldfront.plugins.cluster_storage.signals.DirectoryService')
    def test_signal_calls_directory_service(
        self, mock_directory_service_class, test_project, test_user
    ):
        """Test signal delegates to DirectoryService.add_user_to_directory()."""
        # Setup
        mock_service = Mock()
        mock_directory_service_class.for_project.return_value = mock_service

        mock_project_user = Mock()
        mock_project_user.project = test_project
        mock_project_user.user = test_user

        # Execute
        project_user_activated.send(
            sender=None,
            project_user=mock_project_user
        )

        # Assert
        mock_directory_service_class.for_project.assert_called_once_with(
            test_project
        )
        mock_service.add_user_to_directory.assert_called_once_with(test_user)

    @patch('coldfront.plugins.cluster_storage.signals.logger')
    @patch('coldfront.plugins.cluster_storage.signals.DirectoryService')
    def test_signal_handles_errors_gracefully(
        self, mock_directory_service_class, mock_logger,
        test_project, test_user
    ):
        """Test signal catches and logs errors without breaking activation."""
        # Setup - make DirectoryService raise an error
        mock_service = Mock()
        mock_service.add_user_to_directory.side_effect = Exception(
            'Test error'
        )
        mock_directory_service_class.for_project.return_value = mock_service

        mock_project_user = Mock()
        mock_project_user.project = test_project
        mock_project_user.user = test_user

        # Execute - should not raise
        project_user_activated.send(
            sender=None,
            project_user=mock_project_user
        )

        # Assert - error was logged
        mock_logger.exception.assert_called_once()
        assert 'Error adding User' in str(mock_logger.exception.call_args)

    @patch('coldfront.plugins.cluster_storage.signals.logger')
    def test_signal_warns_if_missing_project(
        self, mock_logger
    ):
        """Test signal warns if project_user has no project."""
        # Setup - project_user with no project
        mock_project_user = Mock()
        mock_project_user.project = None
        mock_project_user.user = Mock()

        # Execute
        add_project_user_to_faculty_storage_allocation(
            sender=None,
            project_user=mock_project_user
        )

        # Assert - warning logged
        mock_logger.warning.assert_called_once()
        assert 'without project or user' in str(
            mock_logger.warning.call_args
        )

    @patch('coldfront.plugins.cluster_storage.signals.logger')
    def test_signal_warns_if_missing_user(
        self, mock_logger
    ):
        """Test signal warns if project_user has no user."""
        # Setup - project_user with no user
        mock_project_user = Mock()
        mock_project_user.project = Mock()
        mock_project_user.user = None

        # Execute
        add_project_user_to_faculty_storage_allocation(
            sender=None,
            project_user=mock_project_user
        )

        # Assert - warning logged
        mock_logger.warning.assert_called_once()
        assert 'without project or user' in str(
            mock_logger.warning.call_args
        )

    @patch('coldfront.plugins.cluster_storage.signals.logger')
    def test_signal_logs_success(
        self, mock_logger, test_project, test_user,
        resource_faculty_storage_directory
    ):
        """Test signal logs successful user addition."""
        # Setup
        directory_service = DirectoryService(test_project, 'fc_test_dir')
        directory_service.create_directory()

        mock_project_user = Mock()
        mock_project_user.project = test_project
        mock_project_user.user = test_user

        # Execute
        project_user_activated.send(
            sender=None,
            project_user=mock_project_user
        )

        # Assert - success logged
        mock_logger.info.assert_called_once()
        assert 'Added User' in str(mock_logger.info.call_args)
        assert test_user.username in str(mock_logger.info.call_args)
        assert test_project.name in str(mock_logger.info.call_args)

    @patch('coldfront.plugins.cluster_storage.signals.logger')
    def test_signal_logs_debug_when_no_allocation(
        self, mock_logger, test_project, test_user
    ):
        """Test signal logs debug message when project has no allocation."""
        # Setup - no allocation for project
        mock_project_user = Mock()
        mock_project_user.project = test_project
        mock_project_user.user = test_user

        # Execute
        project_user_activated.send(
            sender=None,
            project_user=mock_project_user
        )

        # Assert - debug logged
        mock_logger.debug.assert_called_once()
        assert 'does not have a faculty storage allocation' in str(
            mock_logger.debug.call_args
        )


@pytest.mark.component
class TestSignalIntegration:
    """Test signal integration with real workflow."""

    def test_adding_project_user_triggers_signal_and_adds_to_allocation(
        self, test_project, test_user, test_pi, test_project_user_pi,
        project_user_status_active, project_user_role_user,
        resource_faculty_storage_directory
    ):
        """Test complete workflow: create storage → add project user →
        automatic allocation user creation."""
        # Setup - create faculty storage allocation
        directory_service = DirectoryService(test_project, 'fc_test_dir')
        allocation = directory_service.create_directory()

        # Initially no users in allocation
        assert AllocationUser.objects.filter(
            allocation=allocation
        ).count() == 0

        # Execute - create ProjectUser (this triggers the signal in real code)
        # For testing, we manually send the signal
        from coldfront.core.project.models import ProjectUser

        project_user = ProjectUser.objects.create(
            project=test_project,
            user=test_user,
            role=project_user_role_user,
            status=project_user_status_active
        )

        # Send signal manually (in real code, this would be triggered
        # automatically)
        project_user_activated.send(
            sender=ProjectUser,
            project_user=project_user
        )

        # Assert - user was automatically added to allocation
        allocation_users = AllocationUser.objects.filter(
            allocation=allocation,
            user=test_user
        )
        assert allocation_users.exists()
        assert allocation_users.first().status.name == 'Active'

    def test_signal_works_with_multiple_users(
        self, test_project, test_pi, project_user_status_active,
        project_user_role_user, resource_faculty_storage_directory
    ):
        """Test signal correctly handles multiple users being added to same
        project."""
        # Setup
        from coldfront.core.project.models import ProjectUser
        from django.contrib.auth import get_user_model

        User = get_user_model()

        directory_service = DirectoryService(test_project, 'fc_test_dir')
        allocation = directory_service.create_directory()

        # Create 3 users
        user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com'
        )
        user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com'
        )
        user3 = User.objects.create_user(
            username='user3',
            email='user3@test.com'
        )

        # Execute - add all 3 users and trigger signals
        for user in [user1, user2, user3]:
            project_user = ProjectUser.objects.create(
                project=test_project,
                user=user,
                role=project_user_role_user,
                status=project_user_status_active
            )
            project_user_activated.send(
                sender=ProjectUser,
                project_user=project_user
            )

        # Assert - all 3 users added to allocation
        allocation_users = AllocationUser.objects.filter(
            allocation=allocation
        )
        assert allocation_users.count() == 3

        user_ids = {au.user.id for au in allocation_users}
        assert user1.id in user_ids
        assert user2.id in user_ids
        assert user3.id in user_ids
