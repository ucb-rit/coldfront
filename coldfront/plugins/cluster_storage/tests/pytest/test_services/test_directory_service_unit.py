"""Unit tests for DirectoryService.

Tests business logic by mocking database calls. For tests with real database
access, see test_directory_service_integration.py.
"""

import pytest
from unittest.mock import Mock, patch

from coldfront.core.project.models import Project
from coldfront.plugins.cluster_storage.services import DirectoryService


def create_mock_project(name='fc_test'):
    """Helper to create a mock Project that passes isinstance checks."""
    mock_project = Mock(spec=Project)
    mock_project.name = name
    return mock_project


@pytest.mark.unit
class TestDirectoryServiceInit:
    """Unit tests for DirectoryService initialization."""

    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Resource')
    def test_init_with_project_and_directory_name(self, mock_resource):
        """Test DirectoryService initializes with project and directory name."""
        # Setup
        mock_project = create_mock_project()
        directory_name = 'test_dir'

        # Mock the resource lookup
        mock_faculty_storage = Mock()
        mock_resource.objects.get.return_value = mock_faculty_storage

        # Mock the path attribute
        mock_path_attr = Mock()
        mock_path_attr.value = '/global/scratch/fsa'
        mock_faculty_storage.resourceattribute_set.get.return_value = \
            mock_path_attr

        # Execute
        service = DirectoryService(mock_project, directory_name)

        # Assert
        assert service.project == mock_project
        assert service.directory_name == directory_name
        assert service._directory_path == '/global/scratch/fsa/test_dir'
        mock_resource.objects.get.assert_called_once_with(
            name='Scratch Faculty Storage Directory'
        )

    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Resource')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Allocation')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.AllocationAttribute')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.AllocationAttributeType')
    def test_for_project_class_method_finds_existing_allocation(
        self, mock_attr_type_model, mock_attr_model, mock_allocation_model,
        mock_resource_model
    ):
        """Test for_project() finds existing directory allocation."""
        # Setup
        mock_project = create_mock_project()

        # Mock resource lookup
        mock_faculty_storage = Mock()
        mock_resource_model.objects.get.return_value = mock_faculty_storage

        # Mock path resource attribute
        mock_path_attr = Mock()
        mock_path_attr.value = '/global/scratch/fsa'
        mock_faculty_storage.resourceattribute_set.get.return_value = \
            mock_path_attr

        # Mock allocation exists
        mock_allocation = Mock()
        mock_queryset = Mock()
        mock_queryset.exists.return_value = True
        mock_queryset.count.return_value = 1
        mock_queryset.first.return_value = mock_allocation
        mock_allocation_model.objects.filter.return_value = mock_queryset

        # Mock allocation attribute lookup
        mock_allocation_attr_type = Mock()
        mock_attr_type_model.objects.get.return_value = \
            mock_allocation_attr_type

        mock_directory_attr = Mock()
        mock_directory_attr.value = '/global/scratch/fsa/my_test_dir'
        mock_attr_model.objects.get.return_value = mock_directory_attr

        # Execute
        service = DirectoryService.for_project(mock_project)

        # Assert
        assert service is not None
        assert service.directory_name == 'my_test_dir'
        assert service.project == mock_project

    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Resource')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Allocation')
    def test_for_project_returns_none_if_not_found(
        self, mock_allocation_model, mock_resource_model
    ):
        """Test for_project() returns None if no allocation exists."""
        # Setup
        mock_project = create_mock_project()

        # Mock resource lookup
        mock_faculty_storage = Mock()
        mock_resource_model.objects.get.return_value = mock_faculty_storage

        # Mock no allocation exists
        mock_queryset = Mock()
        mock_queryset.exists.return_value = False
        mock_allocation_model.objects.filter.return_value = mock_queryset

        # Execute
        service = DirectoryService.for_project(mock_project)

        # Assert
        assert service is None

    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Resource')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Allocation')
    def test_get_directory_name_raises_on_multiple_allocations(
        self, mock_allocation_model, mock_resource_model
    ):
        """Test get_directory_name_for_project() raises if multiple
        allocations found."""
        # Setup
        mock_project = create_mock_project()

        # Mock resource lookup
        mock_faculty_storage = Mock()
        mock_resource_model.objects.get.return_value = mock_faculty_storage

        # Mock multiple allocations exist
        mock_queryset = Mock()
        mock_queryset.exists.return_value = True
        mock_queryset.count.return_value = 2  # Multiple!
        mock_allocation_model.objects.filter.return_value = mock_queryset

        # Execute & Assert
        with pytest.raises(ValueError, match='multiple faculty storage'):
            DirectoryService.get_directory_name_for_project(mock_project)


@pytest.mark.unit
class TestDirectoryServiceDirectoryOperations:
    """Unit tests for directory creation and management."""

    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.transaction')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Resource')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Allocation')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.AllocationStatusChoice')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.AllocationAttributeType')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.AllocationAttribute')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.display_time_zone_current_date')
    def test_create_directory_creates_allocation_when_not_exists(
        self, mock_date, mock_attr_model, mock_attr_type, mock_status,
        mock_allocation_model, mock_resource, mock_transaction
    ):
        """Test create_directory() creates new allocation when none exists."""
        # Setup
        mock_project = create_mock_project()

        # Mock transaction.atomic context manager
        mock_transaction.atomic.return_value.__enter__ = Mock()
        mock_transaction.atomic.return_value.__exit__ = Mock()

        # Mock resource
        mock_faculty_storage = Mock()
        mock_resource.objects.get.return_value = mock_faculty_storage
        mock_path_attr = Mock()
        mock_path_attr.value = '/global/scratch/fsa'
        mock_faculty_storage.resourceattribute_set.get.return_value = \
            mock_path_attr

        # Mock status
        mock_active_status = Mock()
        mock_status.objects.get.return_value = mock_active_status

        # Mock date
        mock_date.return_value = '2025-01-15'

        # Mock allocation doesn't exist initially - need real exception class
        mock_allocation_model.DoesNotExist = type('DoesNotExist', (Exception,), {})
        mock_allocation_model.objects.get.side_effect = \
            mock_allocation_model.DoesNotExist

        # Mock creating new allocation
        mock_new_allocation = Mock()
        mock_allocation_model.objects.create.return_value = \
            mock_new_allocation

        # Mock attribute type
        mock_path_attr_type = Mock()
        mock_attr_type.objects.get.return_value = mock_path_attr_type

        # Execute
        service = DirectoryService(mock_project, 'test_dir')
        result = service.create_directory()

        # Assert
        mock_allocation_model.objects.create.assert_called_once_with(
            project=mock_project,
            start_date='2025-01-15',
            status=mock_active_status
        )
        mock_new_allocation.resources.add.assert_called_once_with(
            mock_faculty_storage
        )
        mock_attr_model.objects.create.assert_called_once()
        assert result == mock_new_allocation

    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Resource')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Allocation')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.AllocationStatusChoice')
    def test_create_directory_is_idempotent(
        self, mock_status, mock_allocation_model, mock_resource
    ):
        """Test create_directory() updates existing allocation if found."""
        # Setup
        mock_project = create_mock_project()

        # Mock resource
        mock_faculty_storage = Mock()
        mock_resource.objects.get.return_value = mock_faculty_storage
        mock_path_attr = Mock()
        mock_path_attr.value = '/global/scratch/fsa'
        mock_faculty_storage.resourceattribute_set.get.return_value = \
            mock_path_attr

        # Mock status
        mock_active_status = Mock()
        mock_status.objects.get.return_value = mock_active_status

        # Mock allocation already exists
        mock_existing_allocation = Mock()
        mock_existing_allocation.start_date = '2025-01-01'
        mock_allocation_model.objects.get.return_value = \
            mock_existing_allocation

        # Execute
        service = DirectoryService(mock_project, 'test_dir')
        result = service.create_directory()

        # Assert - should update, not create
        mock_allocation_model.objects.create.assert_not_called()
        assert mock_existing_allocation.status == mock_active_status
        mock_existing_allocation.save.assert_called_once()
        assert result == mock_existing_allocation

    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Resource')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Allocation')
    def test_directory_exists_returns_true_when_found(
        self, mock_allocation_model, mock_resource
    ):
        """Test directory_exists() returns True when allocation exists."""
        # Setup
        mock_project = create_mock_project()

        # Mock resource
        mock_faculty_storage = Mock()
        mock_resource.objects.get.return_value = mock_faculty_storage
        mock_path_attr = Mock()
        mock_path_attr.value = '/global/scratch/fsa'
        mock_faculty_storage.resourceattribute_set.get.return_value = \
            mock_path_attr

        # Mock allocation exists
        mock_queryset = Mock()
        mock_queryset.exists.return_value = True
        mock_allocation_model.objects.filter.return_value = mock_queryset

        # Execute
        service = DirectoryService(mock_project, 'test_dir')
        exists = service.directory_exists()

        # Assert
        assert exists is True

    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Resource')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Allocation')
    def test_directory_exists_returns_false_when_not_found(
        self, mock_allocation_model, mock_resource
    ):
        """Test directory_exists() returns False when no allocation."""
        # Setup
        mock_project = create_mock_project()

        # Mock resource
        mock_faculty_storage = Mock()
        mock_resource.objects.get.return_value = mock_faculty_storage
        mock_path_attr = Mock()
        mock_path_attr.value = '/global/scratch/fsa'
        mock_faculty_storage.resourceattribute_set.get.return_value = \
            mock_path_attr

        # Mock allocation doesn't exist
        mock_queryset = Mock()
        mock_queryset.exists.return_value = False
        mock_allocation_model.objects.filter.return_value = mock_queryset

        # Execute
        service = DirectoryService(mock_project, 'test_dir')
        exists = service.directory_exists()

        # Assert
        assert exists is False


@pytest.mark.unit
class TestDirectoryServiceQuotaOperations:
    """Unit tests for quota management."""

    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Resource')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Allocation')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.AllocationAttributeType')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.AllocationAttribute')
    def test_get_current_quota_gb_returns_quota(
        self, mock_attr_model, mock_attr_type, mock_allocation_model,
        mock_resource
    ):
        """Test get_current_quota_gb() retrieves quota from allocation."""
        # Setup
        mock_project = create_mock_project()

        # Mock resource
        mock_faculty_storage = Mock()
        mock_resource.objects.get.return_value = mock_faculty_storage
        mock_path_attr = Mock()
        mock_path_attr.value = '/global/scratch/fsa'
        mock_faculty_storage.resourceattribute_set.get.return_value = \
            mock_path_attr

        # Mock allocation exists
        mock_allocation = Mock()
        mock_allocation_model.objects.get.return_value = mock_allocation

        # Mock quota attribute type
        mock_quota_attr_type = Mock()
        mock_attr_type.objects.get.return_value = mock_quota_attr_type

        # Mock quota attribute
        mock_quota_attr = Mock()
        mock_quota_attr.value = '5000'
        mock_attr_model.objects.get.return_value = mock_quota_attr

        # Execute
        service = DirectoryService(mock_project, 'test_dir')
        quota = service.get_current_quota_gb()

        # Assert
        assert quota == 5000
        mock_attr_type.objects.get.assert_called_once_with(
            name='Storage Quota (GB)'
        )

    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Resource')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Allocation')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.AllocationAttributeType')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.AllocationAttribute')
    def test_get_current_quota_gb_returns_zero_when_no_allocation(
        self, mock_attr_model, mock_attr_type, mock_allocation_model,
        mock_resource
    ):
        """Test get_current_quota_gb() returns 0 when no allocation exists."""
        # Setup
        mock_project = create_mock_project()

        # Mock resource
        mock_faculty_storage = Mock()
        mock_resource.objects.get.return_value = mock_faculty_storage
        mock_path_attr = Mock()
        mock_path_attr.value = '/global/scratch/fsa'
        mock_faculty_storage.resourceattribute_set.get.return_value = \
            mock_path_attr

        # Mock allocation doesn't exist - need real exception class
        mock_allocation_model.DoesNotExist = type('DoesNotExist', (Exception,), {})
        mock_allocation_model.objects.get.side_effect = \
            mock_allocation_model.DoesNotExist

        # Execute
        service = DirectoryService(mock_project, 'test_dir')
        quota = service.get_current_quota_gb()

        # Assert
        assert quota == 0

    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Resource')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Allocation')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.AllocationAttributeType')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.AllocationAttribute')
    def test_get_current_quota_gb_returns_zero_when_no_quota_attr(
        self, mock_attr_model, mock_attr_type, mock_allocation_model,
        mock_resource
    ):
        """Test get_current_quota_gb() returns 0 when allocation has no
        quota."""
        # Setup
        mock_project = create_mock_project()

        # Mock resource
        mock_faculty_storage = Mock()
        mock_resource.objects.get.return_value = mock_faculty_storage
        mock_path_attr = Mock()
        mock_path_attr.value = '/global/scratch/fsa'
        mock_faculty_storage.resourceattribute_set.get.return_value = \
            mock_path_attr

        # Mock allocation exists
        mock_allocation = Mock()
        mock_allocation_model.objects.get.return_value = mock_allocation

        # Mock quota attribute type
        mock_quota_attr_type = Mock()
        mock_attr_type.objects.get.return_value = mock_quota_attr_type

        # Mock quota attribute doesn't exist - need real exception class
        mock_attr_model.DoesNotExist = type('DoesNotExist', (Exception,), {})
        mock_attr_model.objects.get.side_effect = \
            mock_attr_model.DoesNotExist

        # Execute
        service = DirectoryService(mock_project, 'test_dir')
        quota = service.get_current_quota_gb()

        # Assert
        assert quota == 0

    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Resource')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Allocation')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.AllocationAttributeType')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.AllocationAttribute')
    def test_set_directory_quota_updates_quota(
        self, mock_attr_model, mock_attr_type, mock_allocation_model,
        mock_resource
    ):
        """Test set_directory_quota() sets quota attribute."""
        # Setup
        mock_project = create_mock_project()

        # Mock resource
        mock_faculty_storage = Mock()
        mock_resource.objects.get.return_value = mock_faculty_storage
        mock_path_attr = Mock()
        mock_path_attr.value = '/global/scratch/fsa'
        mock_faculty_storage.resourceattribute_set.get.return_value = \
            mock_path_attr

        # Mock allocation exists
        mock_allocation = Mock()
        mock_allocation_model.objects.get.return_value = mock_allocation

        # Mock quota attribute type
        mock_quota_attr_type = Mock()
        mock_attr_type.objects.get.return_value = mock_quota_attr_type

        # Execute
        service = DirectoryService(mock_project, 'test_dir')
        service.set_directory_quota(5000)

        # Assert
        mock_attr_model.objects.update_or_create.assert_called_once_with(
            allocation_attribute_type=mock_quota_attr_type,
            allocation=mock_allocation,
            defaults={'value': '5000'}
        )

    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Resource')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Allocation')
    def test_set_directory_quota_raises_when_no_allocation(
        self, mock_allocation_model, mock_resource
    ):
        """Test set_directory_quota() raises ValueError when allocation
        doesn't exist."""
        # Setup
        mock_project = create_mock_project()

        # Mock resource
        mock_faculty_storage = Mock()
        mock_resource.objects.get.return_value = mock_faculty_storage
        mock_path_attr = Mock()
        mock_path_attr.value = '/global/scratch/fsa'
        mock_faculty_storage.resourceattribute_set.get.return_value = \
            mock_path_attr

        # Mock allocation doesn't exist - need real exception class
        mock_allocation_model.DoesNotExist = type('DoesNotExist', (Exception,), {})
        mock_allocation_model.objects.get.side_effect = \
            mock_allocation_model.DoesNotExist

        # Execute & Assert
        service = DirectoryService(mock_project, 'test_dir')
        with pytest.raises(ValueError, match='Cannot set quota'):
            service.set_directory_quota(5000)

    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Resource')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Allocation')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.AllocationAttributeType')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.AllocationAttribute')
    def test_add_to_directory_quota_adds_to_existing(
        self, mock_attr_model, mock_attr_type, mock_allocation_model,
        mock_resource
    ):
        """Test add_to_directory_quota() adds to current quota."""
        # Setup
        mock_project = create_mock_project()

        # Mock resource
        mock_faculty_storage = Mock()
        mock_resource.objects.get.return_value = mock_faculty_storage
        mock_path_attr = Mock()
        mock_path_attr.value = '/global/scratch/fsa'
        mock_faculty_storage.resourceattribute_set.get.return_value = \
            mock_path_attr

        # Mock allocation exists
        mock_allocation = Mock()
        mock_allocation_model.objects.get.return_value = mock_allocation

        # Mock quota attribute type
        mock_quota_attr_type = Mock()
        mock_attr_type.objects.get.return_value = mock_quota_attr_type

        # Mock existing quota of 1000 GB
        mock_quota_attr = Mock()
        mock_quota_attr.value = '1000'
        mock_attr_model.objects.get.return_value = mock_quota_attr

        # Execute - add 500 GB
        service = DirectoryService(mock_project, 'test_dir')
        service.add_to_directory_quota(500)

        # Assert - should set to 1500 GB
        mock_attr_model.objects.update_or_create.assert_called_once_with(
            allocation_attribute_type=mock_quota_attr_type,
            allocation=mock_allocation,
            defaults={'value': '1500'}
        )


@pytest.mark.unit
class TestDirectoryServiceUserManagement:
    """Unit tests for adding users to directories."""

    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Resource')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Allocation')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.get_or_create_active_allocation_user')
    def test_add_user_to_directory_creates_allocation_user(
        self, mock_get_or_create, mock_allocation_model, mock_resource
    ):
        """Test add_user_to_directory() creates AllocationUser."""
        # Setup
        mock_project = create_mock_project()
        mock_user = Mock()

        # Mock resource
        mock_faculty_storage = Mock()
        mock_resource.objects.get.return_value = mock_faculty_storage
        mock_path_attr = Mock()
        mock_path_attr.value = '/global/scratch/fsa'
        mock_faculty_storage.resourceattribute_set.get.return_value = \
            mock_path_attr

        # Mock allocation exists
        mock_allocation = Mock()
        mock_allocation_model.objects.get.return_value = mock_allocation

        # Mock allocation user creation
        mock_allocation_user = Mock()
        mock_get_or_create.return_value = mock_allocation_user

        # Execute
        service = DirectoryService(mock_project, 'test_dir')
        result = service.add_user_to_directory(mock_user)

        # Assert
        mock_get_or_create.assert_called_once_with(
            mock_allocation, mock_user
        )
        assert result == mock_allocation_user

    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Resource')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Allocation')
    def test_add_user_to_directory_raises_when_no_allocation(
        self, mock_allocation_model, mock_resource
    ):
        """Test add_user_to_directory() raises ValueError when no
        allocation."""
        # Setup
        mock_project = create_mock_project()
        mock_user = Mock()

        # Mock resource
        mock_faculty_storage = Mock()
        mock_resource.objects.get.return_value = mock_faculty_storage
        mock_path_attr = Mock()
        mock_path_attr.value = '/global/scratch/fsa'
        mock_faculty_storage.resourceattribute_set.get.return_value = \
            mock_path_attr

        # Mock allocation doesn't exist - need real exception class
        mock_allocation_model.DoesNotExist = type('DoesNotExist', (Exception,), {})
        mock_allocation_model.objects.get.side_effect = \
            mock_allocation_model.DoesNotExist

        # Execute & Assert
        service = DirectoryService(mock_project, 'test_dir')
        with pytest.raises(ValueError, match='Cannot add user'):
            service.add_user_to_directory(mock_user)

    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.transaction')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Resource')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Allocation')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.ProjectUser')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.get_or_create_active_allocation_user')
    def test_add_project_users_to_directory_adds_all_active_users(
        self, mock_get_or_create, mock_project_user_model,
        mock_allocation_model, mock_resource, mock_transaction
    ):
        """Test add_project_users_to_directory() adds all active project
        users."""
        # Setup
        mock_project = create_mock_project()

        # Mock transaction.atomic context manager
        mock_transaction.atomic.return_value.__enter__ = Mock()
        mock_transaction.atomic.return_value.__exit__ = Mock()

        # Mock resource
        mock_faculty_storage = Mock()
        mock_resource.objects.get.return_value = mock_faculty_storage
        mock_path_attr = Mock()
        mock_path_attr.value = '/global/scratch/fsa'
        mock_faculty_storage.resourceattribute_set.get.return_value = \
            mock_path_attr

        # Mock allocation exists
        mock_allocation = Mock()
        mock_allocation_model.objects.get.return_value = mock_allocation

        # Mock 3 active project users
        mock_pu1 = Mock()
        mock_pu1.user = Mock()
        mock_pu2 = Mock()
        mock_pu2.user = Mock()
        mock_pu3 = Mock()
        mock_pu3.user = Mock()

        mock_queryset = Mock()
        mock_queryset.__iter__ = Mock(return_value=iter([
            mock_pu1, mock_pu2, mock_pu3
        ]))
        mock_project_user_model.objects.filter.return_value = mock_queryset

        # Mock allocation user creation
        mock_au1 = Mock()
        mock_au2 = Mock()
        mock_au3 = Mock()
        mock_get_or_create.side_effect = [mock_au1, mock_au2, mock_au3]

        # Execute
        service = DirectoryService(mock_project, 'test_dir')
        result = service.add_project_users_to_directory()

        # Assert
        assert len(result) == 3
        assert result == [mock_au1, mock_au2, mock_au3]
        assert mock_get_or_create.call_count == 3

    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Resource')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.Allocation')
    @patch('coldfront.plugins.cluster_storage.services.'
           'directory_service.ProjectUser')
    def test_add_project_users_to_directory_raises_when_no_allocation(
        self, mock_project_user_model, mock_allocation_model, mock_resource
    ):
        """Test add_project_users_to_directory() raises ValueError when no
        allocation."""
        # Setup
        mock_project = create_mock_project()

        # Mock resource
        mock_faculty_storage = Mock()
        mock_resource.objects.get.return_value = mock_faculty_storage
        mock_path_attr = Mock()
        mock_path_attr.value = '/global/scratch/fsa'
        mock_faculty_storage.resourceattribute_set.get.return_value = \
            mock_path_attr

        # Mock allocation doesn't exist - need real exception class
        mock_allocation_model.DoesNotExist = type('DoesNotExist', (Exception,), {})
        mock_allocation_model.objects.get.side_effect = \
            mock_allocation_model.DoesNotExist

        # Execute & Assert
        service = DirectoryService(mock_project, 'test_dir')
        with pytest.raises(ValueError, match='Cannot add users'):
            service.add_project_users_to_directory()
