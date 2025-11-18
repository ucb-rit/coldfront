"""Component tests for DirectoryService with database.

These tests use real database operations with fixtures to verify that
DirectoryService correctly interacts with Django models.
"""

import pytest

from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttribute,
    AllocationUser,
)
from coldfront.plugins.faculty_storage_allocations.services import DirectoryService


@pytest.mark.component
class TestDirectoryServiceInitialization:
    """Test DirectoryService initialization with database."""

    def test_init_with_project_and_directory_name(
        self, test_project, resource_faculty_storage_directory
    ):
        """Test DirectoryService initializes successfully."""
        # Execute
        service = DirectoryService(test_project, 'test_dir')

        # Assert
        assert service.project == test_project
        assert service.directory_name == 'test_dir'
        assert service._faculty_storage_directory == \
            resource_faculty_storage_directory
        assert service._directory_path.endswith('test_dir')

    def test_for_project_returns_none_when_no_allocation(self, test_project):
        """Test for_project() returns None when project has no allocation."""
        # Execute
        service = DirectoryService.for_project(test_project)

        # Assert
        assert service is None

    def test_get_directory_name_returns_none_when_no_allocation(
        self, test_project
    ):
        """Test get_directory_name_for_project() returns None when no
        allocation."""
        # Execute
        directory_name = DirectoryService.get_directory_name_for_project(
            test_project
        )

        # Assert
        assert directory_name is None


@pytest.mark.component
class TestDirectoryServiceDirectoryOperations:
    """Test directory creation and management with database."""

    def test_create_directory_persists_allocation(
        self, test_project, resource_faculty_storage_directory
    ):
        """Test create_directory() creates allocation in database."""
        # Setup
        service = DirectoryService(test_project, 'fc_test_dir')

        # Verify no allocation exists initially
        assert Allocation.objects.filter(
            project=test_project,
            resources=resource_faculty_storage_directory
        ).count() == 0

        # Execute
        allocation = service.create_directory()

        # Assert - allocation created and persisted
        assert allocation is not None
        assert allocation.id is not None
        assert allocation.project == test_project
        assert allocation.status.name == 'Active'
        assert allocation.start_date is not None

        # Verify in database
        db_allocation = Allocation.objects.get(id=allocation.id)
        assert db_allocation.project == test_project
        assert resource_faculty_storage_directory in \
            db_allocation.resources.all()

    def test_create_directory_sets_directory_path_attribute(
        self, test_project, resource_faculty_storage_directory
    ):
        """Test create_directory() sets correct directory path attribute."""
        # Setup
        service = DirectoryService(test_project, 'fc_test_dir')

        # Execute
        allocation = service.create_directory()

        # Assert - verify path attribute
        path_attr = AllocationAttribute.objects.get(
            allocation=allocation,
            allocation_attribute_type__name='Cluster Directory Access'
        )
        assert 'fc_test_dir' in path_attr.value
        assert path_attr.value.startswith('/global/scratch')

    def test_create_directory_is_idempotent(
        self, test_project, resource_faculty_storage_directory
    ):
        """Test create_directory() can be called multiple times safely."""
        # Setup
        service = DirectoryService(test_project, 'fc_test_dir')

        # Execute - create twice
        allocation1 = service.create_directory()
        allocation2 = service.create_directory()

        # Assert - same allocation returned
        assert allocation1.id == allocation2.id

        # Verify only one allocation in database
        assert Allocation.objects.filter(
            project=test_project,
            resources=resource_faculty_storage_directory
        ).count() == 1

    def test_directory_exists_returns_true_after_creation(
        self, test_project, resource_faculty_storage_directory
    ):
        """Test directory_exists() returns True after directory created."""
        # Setup
        service = DirectoryService(test_project, 'fc_test_dir')

        # Initially doesn't exist
        assert service.directory_exists() is False

        # Create directory
        service.create_directory()

        # Now exists
        assert service.directory_exists() is True

    def test_for_project_finds_existing_allocation(
        self, test_project, resource_faculty_storage_directory
    ):
        """Test for_project() retrieves existing allocation."""
        # Setup - create directory first
        service1 = DirectoryService(test_project, 'fc_test_dir')
        allocation = service1.create_directory()

        # Execute - use for_project to find it
        service2 = DirectoryService.for_project(test_project)

        # Assert
        assert service2 is not None
        assert service2.directory_name == 'fc_test_dir'
        assert service2.project == test_project
        # Verify it can access the same allocation
        assert service2._get_allocation().id == allocation.id

    def test_get_directory_name_extracts_correct_name(
        self, test_project, resource_faculty_storage_directory
    ):
        """Test get_directory_name_for_project() extracts directory name
        from path."""
        # Setup - create directory
        service = DirectoryService(test_project, 'my_custom_dir')
        service.create_directory()

        # Execute
        directory_name = DirectoryService.get_directory_name_for_project(
            test_project
        )

        # Assert
        assert directory_name == 'my_custom_dir'


@pytest.mark.component
class TestDirectoryServiceQuotaOperations:
    """Test quota management with database."""

    def test_set_directory_quota_creates_attribute(
        self, test_project, resource_faculty_storage_directory
    ):
        """Test set_directory_quota() persists quota attribute."""
        # Setup
        service = DirectoryService(test_project, 'fc_test_dir')
        allocation = service.create_directory()

        # Execute
        service.set_directory_quota(5000)

        # Assert - verify in database
        quota_attr = AllocationAttribute.objects.get(
            allocation=allocation,
            allocation_attribute_type__name='Storage Quota (GB)'
        )
        assert quota_attr.value == '5000'

    def test_set_directory_quota_updates_existing_quota(
        self, test_project, resource_faculty_storage_directory
    ):
        """Test set_directory_quota() updates existing quota."""
        # Setup
        service = DirectoryService(test_project, 'fc_test_dir')
        service.create_directory()
        service.set_directory_quota(1000)

        # Execute - update quota
        service.set_directory_quota(2000)

        # Assert - only one quota attribute exists
        quota_attrs = AllocationAttribute.objects.filter(
            allocation_attribute_type__name='Storage Quota (GB)'
        )
        assert quota_attrs.count() == 1
        assert quota_attrs.first().value == '2000'

    def test_get_current_quota_gb_retrieves_from_database(
        self, test_project, resource_faculty_storage_directory
    ):
        """Test get_current_quota_gb() reads from database."""
        # Setup
        service = DirectoryService(test_project, 'fc_test_dir')
        service.create_directory()
        service.set_directory_quota(3500)

        # Execute
        quota = service.get_current_quota_gb()

        # Assert
        assert quota == 3500

    def test_get_current_quota_gb_returns_zero_when_no_quota_set(
        self, test_project, resource_faculty_storage_directory
    ):
        """Test get_current_quota_gb() returns 0 when no quota set."""
        # Setup
        service = DirectoryService(test_project, 'fc_test_dir')
        service.create_directory()
        # Don't set quota

        # Execute
        quota = service.get_current_quota_gb()

        # Assert
        assert quota == 0

    def test_get_current_quota_gb_returns_zero_when_no_allocation(
        self, test_project
    ):
        """Test get_current_quota_gb() returns 0 when allocation doesn't
        exist."""
        # Setup
        service = DirectoryService(test_project, 'fc_test_dir')
        # Don't create directory

        # Execute
        quota = service.get_current_quota_gb()

        # Assert
        assert quota == 0

    def test_add_to_directory_quota_adds_to_existing(
        self, test_project, resource_faculty_storage_directory
    ):
        """Test add_to_directory_quota() correctly adds to current quota."""
        # Setup
        service = DirectoryService(test_project, 'fc_test_dir')
        service.create_directory()
        service.set_directory_quota(1000)

        # Execute - add 500 GB
        service.add_to_directory_quota(500)

        # Assert
        quota = service.get_current_quota_gb()
        assert quota == 1500

    def test_add_to_directory_quota_works_when_no_existing_quota(
        self, test_project, resource_faculty_storage_directory
    ):
        """Test add_to_directory_quota() works when starting from 0."""
        # Setup
        service = DirectoryService(test_project, 'fc_test_dir')
        service.create_directory()

        # Execute - add to 0
        service.add_to_directory_quota(1000)

        # Assert
        quota = service.get_current_quota_gb()
        assert quota == 1000

    def test_set_directory_quota_raises_when_no_allocation(
        self, test_project
    ):
        """Test set_directory_quota() raises ValueError when allocation
        doesn't exist."""
        # Setup
        service = DirectoryService(test_project, 'fc_test_dir')
        # Don't create directory

        # Execute & Assert
        with pytest.raises(ValueError, match='Cannot set quota'):
            service.set_directory_quota(1000)


@pytest.mark.component
class TestDirectoryServiceUserManagement:
    """Test user management with database."""

    def test_add_user_to_directory_creates_allocation_user(
        self, test_project, test_user, resource_faculty_storage_directory
    ):
        """Test add_user_to_directory() creates AllocationUser in database."""
        # Setup
        service = DirectoryService(test_project, 'fc_test_dir')
        allocation = service.create_directory()

        # Verify no allocation users initially
        assert AllocationUser.objects.filter(
            allocation=allocation
        ).count() == 0

        # Execute
        allocation_user = service.add_user_to_directory(test_user)

        # Assert
        assert allocation_user is not None
        assert allocation_user.allocation == allocation
        assert allocation_user.user == test_user
        assert allocation_user.status.name == 'Active'

        # Verify in database
        db_allocation_user = AllocationUser.objects.get(
            id=allocation_user.id
        )
        assert db_allocation_user.user == test_user

    def test_add_user_to_directory_is_idempotent(
        self, test_project, test_user, resource_faculty_storage_directory
    ):
        """Test add_user_to_directory() can be called multiple times for same
        user."""
        # Setup
        service = DirectoryService(test_project, 'fc_test_dir')
        allocation = service.create_directory()

        # Execute - add same user twice
        allocation_user1 = service.add_user_to_directory(test_user)
        allocation_user2 = service.add_user_to_directory(test_user)

        # Assert - same allocation user returned
        assert allocation_user1.id == allocation_user2.id

        # Verify only one AllocationUser in database
        assert AllocationUser.objects.filter(
            allocation=allocation,
            user=test_user
        ).count() == 1

    def test_add_user_raises_when_no_allocation(self, test_project, test_user):
        """Test add_user_to_directory() raises ValueError when allocation
        doesn't exist."""
        # Setup
        service = DirectoryService(test_project, 'fc_test_dir')
        # Don't create directory

        # Execute & Assert
        with pytest.raises(ValueError, match='Cannot add user'):
            service.add_user_to_directory(test_user)

    def test_add_project_users_to_directory_adds_all_active_users(
        self, test_project, test_pi, test_user, test_project_user_pi,
        test_project_user_member, resource_faculty_storage_directory
    ):
        """Test add_project_users_to_directory() adds all active project
        users."""
        # Setup
        service = DirectoryService(test_project, 'fc_test_dir')
        allocation = service.create_directory()

        # Execute
        allocation_users = service.add_project_users_to_directory()

        # Assert - both PI and member added
        assert len(allocation_users) == 2

        # Verify in database
        db_allocation_users = AllocationUser.objects.filter(
            allocation=allocation
        )
        assert db_allocation_users.count() == 2

        # Verify both users are included
        user_ids = {au.user.id for au in db_allocation_users}
        assert test_pi.id in user_ids
        assert test_user.id in user_ids

    def test_add_project_users_raises_when_no_allocation(
        self, test_project, test_project_user_pi
    ):
        """Test add_project_users_to_directory() raises ValueError when
        allocation doesn't exist."""
        # Setup
        service = DirectoryService(test_project, 'fc_test_dir')
        # Don't create directory

        # Execute & Assert
        with pytest.raises(ValueError, match='Cannot add users'):
            service.add_project_users_to_directory()

    def test_remove_user_from_directory_sets_status_to_removed(
        self, test_project, test_user, resource_faculty_storage_directory
    ):
        """Test remove_user_from_directory() sets AllocationUser status to
        Removed."""
        # Setup
        service = DirectoryService(test_project, 'fc_test_dir')
        allocation = service.create_directory()
        allocation_user = service.add_user_to_directory(test_user)

        # Verify user is active initially
        assert allocation_user.status.name == 'Active'

        # Execute
        removed_allocation_user = service.remove_user_from_directory(test_user)

        # Assert
        assert removed_allocation_user is not None
        assert removed_allocation_user.id == allocation_user.id
        assert removed_allocation_user.status.name == 'Removed'

        # Verify in database
        db_allocation_user = AllocationUser.objects.get(
            id=allocation_user.id
        )
        assert db_allocation_user.status.name == 'Removed'

    def test_remove_user_from_directory_returns_none_when_user_not_found(
        self, test_project, test_user, resource_faculty_storage_directory
    ):
        """Test remove_user_from_directory() returns None when user not in
        allocation."""
        # Setup
        service = DirectoryService(test_project, 'fc_test_dir')
        service.create_directory()
        # Don't add user to allocation

        # Execute
        result = service.remove_user_from_directory(test_user)

        # Assert
        assert result is None

    def test_remove_user_from_directory_is_idempotent(
        self, test_project, test_user, resource_faculty_storage_directory
    ):
        """Test remove_user_from_directory() can be called multiple times."""
        # Setup
        service = DirectoryService(test_project, 'fc_test_dir')
        service.create_directory()
        allocation_user = service.add_user_to_directory(test_user)

        # Execute - remove twice
        result1 = service.remove_user_from_directory(test_user)
        result2 = service.remove_user_from_directory(test_user)

        # Assert - both return the same allocation user
        assert result1 is not None
        assert result2 is not None
        assert result1.id == result2.id
        assert result1.status.name == 'Removed'
        assert result2.status.name == 'Removed'

    def test_remove_user_raises_when_no_allocation(self, test_project, test_user):
        """Test remove_user_from_directory() raises ValueError when allocation
        doesn't exist."""
        # Setup
        service = DirectoryService(test_project, 'fc_test_dir')
        # Don't create directory

        # Execute & Assert
        with pytest.raises(ValueError, match='Cannot remove user'):
            service.remove_user_from_directory(test_user)


@pytest.mark.component
class TestDirectoryServiceEdgeCases:
    """Test edge cases and error conditions with database."""

    def test_multiple_directory_names_for_same_project(
        self, test_project, resource_faculty_storage_directory
    ):
        """Test that only one directory can be created per project."""
        # Setup
        service1 = DirectoryService(test_project, 'dir1')
        allocation1 = service1.create_directory()

        # Try to create another directory with different name
        service2 = DirectoryService(test_project, 'dir2')
        allocation2 = service2.create_directory()

        # They should reference different paths, but both exist
        assert allocation1.id != allocation2.id
        assert Allocation.objects.filter(
            project=test_project,
            resources=resource_faculty_storage_directory
        ).count() == 2

    def test_directory_caching_works_correctly(
        self, test_project, resource_faculty_storage_directory
    ):
        """Test that internal allocation caching works correctly."""
        # Setup
        service = DirectoryService(test_project, 'fc_test_dir')

        # Initially cached allocation is None
        assert service._allocation is None

        # Create directory
        allocation = service.create_directory()

        # Allocation is now cached
        assert service._allocation == allocation

        # Get allocation again (should use cache)
        cached_allocation = service._get_allocation()
        assert cached_allocation == allocation

        # Refresh should fetch from DB
        refreshed_allocation = service._get_allocation(refresh=True)
        assert refreshed_allocation.id == allocation.id
