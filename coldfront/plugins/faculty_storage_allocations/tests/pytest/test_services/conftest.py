"""Fixtures specific to service tests."""

import pytest
from unittest.mock import Mock


@pytest.fixture
def mock_allocation():
    """Return a mock allocation for service tests."""
    allocation = Mock()
    allocation.id = 1
    allocation.project = Mock()
    allocation.project.id = 1
    allocation.project.name = 'fc_test'
    allocation.project.title = 'Test Project'
    return allocation


@pytest.fixture
def mock_directory_service():
    """Return a mock DirectoryService for testing.

    Use this when you need to mock the backend system interactions
    without actually provisioning storage.
    """
    service = Mock()
    service.create_directory = Mock(return_value=Mock(id=1))
    service.set_directory_quota = Mock()
    service.get_current_quota_gb = Mock(return_value=0)
    service.add_user_to_directory = Mock()
    service.remove_user_from_directory = Mock()
    service.directory_exists = Mock(return_value=False)
    return service


@pytest.fixture
def mock_request_service():
    """Return a mock FacultyStorageAllocationRequestService."""
    service = Mock()
    service.create_request = Mock(return_value=Mock(id=1))
    service.update_request_state = Mock()
    service.approve_eligibility = Mock()
    service.deny_eligibility = Mock()
    service.approve_intake_consistency = Mock()
    service.deny_intake_consistency = Mock()
    service.complete_setup = Mock()
    return service


@pytest.fixture
def mock_eligibility_service():
    """Return a mock FSARequestEligibilityService."""
    service = Mock()
    service.check_pi_eligibility = Mock(return_value={
        'is_eligible': True,
        'reason': ''
    })
    service.check_project_eligibility = Mock(return_value={
        'is_eligible': True,
        'reason': ''
    })
    return service
