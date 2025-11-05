"""Unit tests for API serializers."""

import pytest
from unittest.mock import Mock, patch
from django.utils import timezone

from coldfront.plugins.faculty_storage_allocations.api.serializers import (
    StorageRequestNextSerializer,
    StorageRequestCompletionSerializer,
)


def create_mock_request(
    request_id=1,
    project_name='fc_test',
    approved_amount_gb=1000,
    directory_name='fc_test_dir',
    approval_time=None
):
    """Create a mock FacultyStorageAllocationRequest for testing."""
    mock_request = Mock()
    mock_request.id = request_id
    mock_request.approved_amount_gb = approved_amount_gb
    mock_request.approval_time = approval_time or timezone.now()

    # Mock project
    mock_project = Mock()
    mock_project.name = project_name
    mock_request.project = mock_project

    # Mock status
    mock_status = Mock()
    mock_status.name = 'Approved - Processing'
    mock_request.status = mock_status

    # Mock state
    mock_request.state = {
        'setup': {
            'directory_name': directory_name,
            'status': 'Pending',
            'timestamp': ''
        }
    }

    return mock_request


@pytest.mark.unit
class TestStorageRequestNextSerializer:
    """Unit tests for StorageRequestNextSerializer."""

    def test_serializer_includes_all_required_fields(self):
        """Test serializer includes all expected fields."""
        # Setup
        mock_request = create_mock_request()

        # Execute
        serializer = StorageRequestNextSerializer(mock_request)

        # Assert - check all fields are present
        expected_fields = {
            'id',
            'project_name',
            'directory_path',
            'set_size_gb',
            'requested_delta_gb',
            'status',
            'approval_time',
        }
        assert set(serializer.fields.keys()) == expected_fields

    @patch('coldfront.plugins.faculty_storage_allocations.services.DirectoryService')
    def test_serializer_transforms_data_correctly(
        self, mock_directory_service_class
    ):
        """Test serializer transforms model instance to dict correctly."""
        # Setup
        mock_request = create_mock_request(
            request_id=123,
            project_name='fc_test_project',
            approved_amount_gb=2000,
            directory_name='fc_custom_dir'
        )

        # Mock DirectoryService static methods
        mock_directory_service_class.get_directory_path_for_project.return_value = \
            '/global/scratch/projects/fc/fc_custom_dir'
        mock_directory_service_class.get_directory_name_for_project.return_value = \
            'fc_custom_dir'

        # Mock DirectoryService instance for current quota
        mock_service = Mock()
        mock_service.get_current_quota_gb.return_value = 1000
        mock_directory_service_class.return_value = mock_service

        # Execute
        serializer = StorageRequestNextSerializer(mock_request)
        data = serializer.data

        # Assert
        assert data['id'] == 123
        assert data['project_name'] == 'fc_test_project'
        assert data['requested_delta_gb'] == 2000
        assert data['directory_path'] == \
            '/global/scratch/projects/fc/fc_custom_dir'
        assert data['set_size_gb'] == 3000  # 1000 current + 2000 approved

    def test_serializer_is_read_only(self):
        """Test serializer fields are all read-only."""
        # Execute
        serializer = StorageRequestNextSerializer()

        # Assert - all fields should be read-only
        for field_name in serializer.fields:
            assert serializer.fields[field_name].read_only

    @patch('coldfront.plugins.faculty_storage_allocations.services.DirectoryService')
    def test_get_directory_path_uses_state_directory_name(
        self, mock_directory_service_class
    ):
        """Test get_directory_path uses directory_name from state."""
        # Setup
        mock_request = create_mock_request(directory_name='fc_my_special_dir')

        # Mock DirectoryService static methods
        mock_directory_service_class.get_directory_path_for_project.return_value = \
            '/global/scratch/projects/fc/fc_my_special_dir'
        mock_directory_service_class.get_directory_name_for_project.return_value = \
            'fc_my_special_dir'

        # Mock DirectoryService instance for current quota
        mock_service = Mock()
        mock_service.get_current_quota_gb.return_value = 0
        mock_directory_service_class.return_value = mock_service

        # Execute
        serializer = StorageRequestNextSerializer(mock_request)
        data = serializer.data

        # Assert
        assert data['directory_path'] == \
            '/global/scratch/projects/fc/fc_my_special_dir'

    @patch('coldfront.plugins.faculty_storage_allocations.services.DirectoryService')
    def test_get_directory_path_falls_back_to_project_name(
        self, mock_directory_service_class
    ):
        """Test get_directory_path uses project name when directory_name not
        set."""
        # Setup
        mock_request = create_mock_request(
            project_name='fc_fallback_project',
            directory_name=''  # Empty directory name
        )

        # Mock DirectoryService static methods - when directory_name is empty,
        # it should fall back to project name
        mock_directory_service_class.get_directory_path_for_project.return_value = \
            '/global/scratch/projects/fc/fc_fallback_project'
        mock_directory_service_class.get_directory_name_for_project.return_value = \
            'fc_fallback_project'

        # Mock DirectoryService instance for current quota
        mock_service = Mock()
        mock_service.get_current_quota_gb.return_value = 0
        mock_directory_service_class.return_value = mock_service

        # Execute
        serializer = StorageRequestNextSerializer(mock_request)
        data = serializer.data

        # Assert - should use project name as fallback
        assert data['directory_path'] == \
            '/global/scratch/projects/fc/fc_fallback_project'

    @patch('coldfront.plugins.faculty_storage_allocations.services.DirectoryService')
    def test_get_set_size_gb_adds_current_and_approved(
        self, mock_directory_service_class
    ):
        """Test get_set_size_gb calculates total quota correctly."""
        # Setup
        mock_request = create_mock_request(approved_amount_gb=500)

        # Mock DirectoryService static methods
        mock_directory_service_class.get_directory_path_for_project.return_value = \
            '/global/scratch/projects/fc/fc_test_dir'
        mock_directory_service_class.get_directory_name_for_project.return_value = \
            'fc_test_dir'

        # Current quota is 2000 GB
        mock_service = Mock()
        mock_service.get_current_quota_gb.return_value = 2000
        mock_directory_service_class.return_value = mock_service

        # Execute
        serializer = StorageRequestNextSerializer(mock_request)
        data = serializer.data

        # Assert - should be 2000 + 500 = 2500
        assert data['set_size_gb'] == 2500

    @patch('coldfront.plugins.faculty_storage_allocations.services.DirectoryService')
    def test_get_set_size_gb_when_no_existing_quota(
        self, mock_directory_service_class
    ):
        """Test get_set_size_gb when allocation has no current quota."""
        # Setup
        mock_request = create_mock_request(approved_amount_gb=1000)

        # Mock DirectoryService static methods
        mock_directory_service_class.get_directory_path_for_project.return_value = \
            '/global/scratch/projects/fc/fc_test_dir'
        mock_directory_service_class.get_directory_name_for_project.return_value = \
            'fc_test_dir'

        # No existing quota
        mock_service = Mock()
        mock_service.get_current_quota_gb.return_value = 0
        mock_directory_service_class.return_value = mock_service

        # Execute
        serializer = StorageRequestNextSerializer(mock_request)
        data = serializer.data

        # Assert - should be 0 + 1000 = 1000
        assert data['set_size_gb'] == 1000

    @patch('coldfront.plugins.faculty_storage_allocations.services.DirectoryService')
    def test_serializer_handles_status_object(
        self, mock_directory_service_class
    ):
        """Test serializer correctly handles status choice object."""
        # Setup
        mock_request = create_mock_request()
        mock_request.status.name = 'Approved - Queued'

        # Mock DirectoryService static methods
        mock_directory_service_class.get_directory_path_for_project.return_value = \
            '/global/scratch/projects/fc/fc_test_dir'
        mock_directory_service_class.get_directory_name_for_project.return_value = \
            'fc_test_dir'

        # Mock DirectoryService instance for current quota
        mock_service = Mock()
        mock_service.get_current_quota_gb.return_value = 0
        mock_directory_service_class.return_value = mock_service

        # Execute
        serializer = StorageRequestNextSerializer(mock_request)
        data = serializer.data

        # Assert - status should be serialized (as string or object)
        assert 'status' in data


@pytest.mark.unit
class TestStorageRequestCompletionSerializer:
    """Unit tests for StorageRequestCompletionSerializer."""

    def test_completion_serializer_requires_directory_name(self):
        """Test completion serializer validates directory_name is present."""
        # Setup - empty data
        data = {}

        # Execute
        serializer = StorageRequestCompletionSerializer(data=data)

        # Assert - should not be valid
        assert not serializer.is_valid()
        assert 'directory_name' in serializer.errors

    def test_completion_serializer_validates_data_format(self):
        """Test serializer validates data types and formats."""
        # Setup - valid data
        data = {'directory_name': 'fc_test_dir'}

        # Execute
        serializer = StorageRequestCompletionSerializer(data=data)

        # Assert - should be valid
        assert serializer.is_valid()
        assert serializer.validated_data['directory_name'] == 'fc_test_dir'

    def test_completion_serializer_rejects_empty_directory_name(self):
        """Test serializer rejects empty directory_name."""
        # Setup - empty string
        data = {'directory_name': ''}

        # Execute
        serializer = StorageRequestCompletionSerializer(data=data)

        # Assert - should not be valid
        assert not serializer.is_valid()
        assert 'directory_name' in serializer.errors

    def test_completion_serializer_rejects_whitespace_only_directory_name(
        self
    ):
        """Test serializer rejects directory_name with only whitespace."""
        # Setup - whitespace only
        data = {'directory_name': '   '}

        # Execute
        serializer = StorageRequestCompletionSerializer(data=data)

        # Assert - should not be valid
        assert not serializer.is_valid()
        assert 'directory_name' in serializer.errors

    def test_completion_serializer_strips_whitespace(self):
        """Test serializer strips leading/trailing whitespace."""
        # Setup - directory name with spaces
        data = {'directory_name': '  fc_test_dir  '}

        # Execute
        serializer = StorageRequestCompletionSerializer(data=data)

        # Assert - should strip whitespace
        assert serializer.is_valid()
        assert serializer.validated_data['directory_name'] == 'fc_test_dir'

    def test_completion_serializer_enforces_max_length(self):
        """Test serializer enforces max_length of 255."""
        # Setup - very long directory name (256 characters)
        data = {'directory_name': 'a' * 256}

        # Execute
        serializer = StorageRequestCompletionSerializer(data=data)

        # Assert - should not be valid
        assert not serializer.is_valid()
        assert 'directory_name' in serializer.errors

    def test_completion_serializer_accepts_valid_directory_name(self):
        """Test serializer accepts valid directory names."""
        # Setup - various valid names
        valid_names = [
            'fc_test',
            'fc_my_project_123',
            'fc_dir-with-dashes',
            'fc_dir_with_underscores',
            'fc_' + 'x' * 250,  # 253 chars (within limit)
        ]

        for directory_name in valid_names:
            # Execute
            data = {'directory_name': directory_name}
            serializer = StorageRequestCompletionSerializer(data=data)

            # Assert
            assert serializer.is_valid(), \
                f"Failed for: {directory_name}"
            assert serializer.validated_data['directory_name'] == \
                directory_name
