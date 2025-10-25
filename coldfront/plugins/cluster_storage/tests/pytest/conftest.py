"""Shared pytest fixtures for cluster_storage plugin tests.

This conftest.py provides fixtures that are used across multiple test modules.
Module-specific fixtures should be placed in the module's own conftest.py.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.utils import timezone

from coldfront.core.project.models import (
    Project,
    ProjectStatusChoice,
    ProjectUser,
    ProjectUserRoleChoice,
    ProjectUserStatusChoice,
)
from coldfront.core.allocation.models import (
    Allocation,
    AllocationStatusChoice,
    AllocationAttribute,
    AllocationAttributeType,
    AllocationUser,
    AllocationUserStatusChoice,
)
from coldfront.core.resource.models import (
    Resource,
    ResourceType,
    ResourceAttribute,
    ResourceAttributeType,
    AttributeType,
)

from coldfront.plugins.cluster_storage.models import (
    FacultyStorageAllocationRequest,
    FacultyStorageAllocationRequestStatusChoice,
    faculty_storage_allocation_request_state_schema,
)


User = get_user_model()


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
def mock_user():
    """Return a basic mock user object."""
    user = Mock()
    user.id = 1
    user.username = 'testuser'
    user.email = 'test@example.com'
    user.first_name = 'Test'
    user.last_name = 'User'
    user.is_staff = False
    user.is_superuser = False
    return user


@pytest.fixture
def test_user(db):
    """Create a real user in the database."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        first_name='Test',
        last_name='User',
        password='testpass123'
    )


@pytest.fixture
def test_pi(db):
    """Create a PI user in the database."""
    return User.objects.create_user(
        username='pi',
        email='pi@example.com',
        first_name='Principal',
        last_name='Investigator',
        password='testpass123'
    )


@pytest.fixture
def staff_user(db):
    """Create a staff user for API and admin testing."""
    return User.objects.create_user(
        username='staff',
        email='staff@example.com',
        first_name='Staff',
        last_name='User',
        password='staffpass123',
        is_staff=True
    )


@pytest.fixture
def test_staff_user(db):
    """Create a staff user in the database."""
    return User.objects.create_user(
        username='staffuser',
        email='staff@example.com',
        first_name='Staff',
        last_name='User',
        password='testpass123',
        is_staff=True
    )


# ============================================================================
# Project Fixtures
# ============================================================================

@pytest.fixture
def project_status_choice_new(db):
    """Return or create a 'New' project status."""
    status, _ = ProjectStatusChoice.objects.get_or_create(name='New')
    return status


@pytest.fixture
def project_status_choice_active(db):
    """Return or create an 'Active' project status."""
    status, _ = ProjectStatusChoice.objects.get_or_create(name='Active')
    return status


@pytest.fixture
def test_project(db, test_pi, project_status_choice_active):
    """Create a test project."""
    return Project.objects.create(
        title='Test Project',
        name='fc_test',
        description='Test project description',
        status=project_status_choice_active,
    )


# ============================================================================
# ProjectUser Relationship Fixtures
# ============================================================================

@pytest.fixture
def project_user_role_pi(db):
    """Return or create PI role."""
    role, _ = ProjectUserRoleChoice.objects.get_or_create(
        name='Principal Investigator'
    )
    return role


@pytest.fixture
def project_user_role_manager(db):
    """Return or create Manager role."""
    role, _ = ProjectUserRoleChoice.objects.get_or_create(name='Manager')
    return role


@pytest.fixture
def project_user_role_user(db):
    """Return or create User role."""
    role, _ = ProjectUserRoleChoice.objects.get_or_create(name='User')
    return role


@pytest.fixture
def project_user_status_active(db):
    """Return or create Active project user status."""
    status, _ = ProjectUserStatusChoice.objects.get_or_create(name='Active')
    return status


@pytest.fixture
def test_project_user_pi(
    db, test_project, test_pi, project_user_role_pi,
    project_user_status_active
):
    """Create PI ProjectUser relationship."""
    return ProjectUser.objects.create(
        project=test_project,
        user=test_pi,
        role=project_user_role_pi,
        status=project_user_status_active,
    )


@pytest.fixture
def test_project_user_member(
    db, test_project, test_user, project_user_role_user,
    project_user_status_active
):
    """Create regular user ProjectUser relationship."""
    return ProjectUser.objects.create(
        project=test_project,
        user=test_user,
        role=project_user_role_user,
        status=project_user_status_active,
    )


# ============================================================================
# Resource and Allocation Fixtures
# ============================================================================

@pytest.fixture
def resource_type(db):
    """Return or create a default ResourceType."""
    resource_type, _ = ResourceType.objects.get_or_create(
        name='Storage',
        description='Storage resource type'
    )
    return resource_type


@pytest.fixture
def resource_type_cluster_directory(db):
    """Get 'Cluster Directory' ResourceType.

    Note: This is created by the session-level django_db_setup fixture
    which runs add_faculty_directory_defaults.
    """
    return ResourceType.objects.get(name='Cluster Directory')


@pytest.fixture
def resource_scratch_directory(db):
    """Get Scratch Directory parent resource.

    Note: This is created by the session-level django_db_setup fixture
    which runs add_directory_defaults.
    """
    return Resource.objects.get(name='Scratch Directory')


@pytest.fixture
def resource_faculty_storage_directory(db):
    """Get Scratch Faculty Storage Directory resource.

    Note: This is created by the session-level django_db_setup fixture
    which runs add_faculty_directory_defaults.
    """
    return Resource.objects.get(name='Scratch Faculty Storage Directory')


@pytest.fixture
def test_resource(db, resource_type):
    """Create a test resource."""
    return Resource.objects.create(
        name='Faculty Groups',
        resource_type=resource_type,
        description='Faculty storage groups directory',
    )


@pytest.fixture
def resource_groups_directory(db, resource_type_cluster_directory):
    """Create Faculty Groups Directory resource."""
    return Resource.objects.create(
        name='Faculty Groups Directory',
        resource_type=resource_type_cluster_directory,
        description='Faculty storage groups directory',
    )


@pytest.fixture
def allocation_status_choice_active(db):
    """Return or create an 'Active' allocation status."""
    status, _ = AllocationStatusChoice.objects.get_or_create(name='Active')
    return status


@pytest.fixture
def test_allocation(db, test_project, test_resource, allocation_status_choice_active):
    """Create a test allocation."""
    allocation = Allocation.objects.create(
        project=test_project,
        status=allocation_status_choice_active,
    )
    allocation.resources.add(test_resource)
    return allocation


@pytest.fixture
def allocation_attribute_type_directory_path(db):
    """Return or create allocation attribute type for directory path."""
    attr_type, _ = AllocationAttributeType.objects.get_or_create(
        name='Cluster Directory Access',
        defaults={
            'is_required': True,
            'is_unique': False,
            'is_private': False,
        }
    )
    return attr_type


@pytest.fixture
def allocation_attribute_type_storage_quota(db):
    """Return or create allocation attribute type for storage quota."""
    attr_type, _ = AllocationAttributeType.objects.get_or_create(
        name='Storage Quota (GB)',
        defaults={
            'is_required': True,
            'is_unique': False,
            'is_private': False,
        }
    )
    return attr_type


@pytest.fixture
def allocation_attribute_type_storage_name(db):
    """Return or create allocation attribute type for storage name."""
    attr_type, _ = AllocationAttributeType.objects.get_or_create(
        name='Storage Name',
        defaults={
            'is_required': False,
            'is_unique': True,
            'is_private': False,
        }
    )
    return attr_type


# ============================================================================
# AllocationUser Relationship Fixtures
# ============================================================================

@pytest.fixture
def allocation_user_status_active(db):
    """Return or create Active allocation user status."""
    status, _ = AllocationUserStatusChoice.objects.get_or_create(
        name='Active'
    )
    return status


@pytest.fixture
def test_allocation_user(
    db, test_allocation, test_user, allocation_user_status_active
):
    """Create an AllocationUser relationship."""
    return AllocationUser.objects.create(
        allocation=test_allocation,
        user=test_user,
        status=allocation_user_status_active,
    )


@pytest.fixture
def test_allocation_user_pi(
    db, test_allocation, test_pi, allocation_user_status_active
):
    """Create an AllocationUser relationship for the PI."""
    return AllocationUser.objects.create(
        allocation=test_allocation,
        user=test_pi,
        status=allocation_user_status_active,
    )


# ============================================================================
# Storage Request Status Fixtures
# ============================================================================

@pytest.fixture
def storage_request_status_pending(db):
    """Return or create 'Pending' storage request status."""
    status, _ = FacultyStorageAllocationRequestStatusChoice.objects.get_or_create(
        name='Under Review'
    )
    return status


@pytest.fixture
def storage_request_status_approved_queued(db):
    """Return or create 'Approved - Queued' storage request status."""
    status, _ = FacultyStorageAllocationRequestStatusChoice.objects.get_or_create(
        name='Approved - Queued'
    )
    return status


@pytest.fixture
def storage_request_status_approved_processing(db):
    """Return or create 'Approved - Processing' storage request status."""
    status, _ = FacultyStorageAllocationRequestStatusChoice.objects.get_or_create(
        name='Approved - Processing'
    )
    return status


@pytest.fixture
def storage_request_status_approved_complete(db):
    """Return or create 'Approved - Complete' storage request status."""
    status, _ = FacultyStorageAllocationRequestStatusChoice.objects.get_or_create(
        name='Approved - Complete'
    )
    return status


@pytest.fixture
def storage_request_status_denied(db):
    """Return or create 'Denied' storage request status."""
    status, _ = FacultyStorageAllocationRequestStatusChoice.objects.get_or_create(
        name='Denied'
    )
    return status


# ============================================================================
# Storage Request Fixtures
# ============================================================================

@pytest.fixture
def test_storage_request(db, test_project, test_user, test_pi, storage_request_status_pending):
    """Create a basic storage request."""
    return FacultyStorageAllocationRequest.objects.create(
        status=storage_request_status_pending,
        project=test_project,
        requester=test_user,
        pi=test_pi,
        requested_amount_gb=1000,
        state=faculty_storage_allocation_request_state_schema(),
    )


@pytest.fixture
def approved_storage_request(
    db, test_project, test_user, test_pi, storage_request_status_approved_queued
):
    """Create an approved storage request."""
    state = faculty_storage_allocation_request_state_schema()
    state['eligibility']['status'] = 'Approved'
    state['eligibility']['timestamp'] = timezone.now().isoformat()
    state['intake_consistency']['status'] = 'Approved'
    state['intake_consistency']['timestamp'] = timezone.now().isoformat()

    return FacultyStorageAllocationRequest.objects.create(
        status=storage_request_status_approved_queued,
        project=test_project,
        requester=test_user,
        pi=test_pi,
        requested_amount_gb=1000,
        approved_amount_gb=1000,
        approval_time=timezone.now(),
        state=state,
    )


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_cache():
    """Return a mock cache instance."""
    from coldfront.plugins.cluster_storage.tests.pytest.utils import MockCache
    return MockCache()


@pytest.fixture
def mock_email_strategy():
    """Return a mock email notification strategy."""
    mock = Mock()
    mock.send_request_created_email = Mock()
    mock.send_approval_email = Mock()
    mock.send_denial_email = Mock()
    mock.send_completion_email = Mock()
    return mock


# ============================================================================
# Email Testing Fixtures
# ============================================================================

@pytest.fixture
def mailoutbox():
    """Return Django's mail outbox for testing emails.

    Note: Requires settings.EMAIL_BACKEND =
    'django.core.mail.backends.locmem.EmailBackend'
    """
    from django.core import mail
    mail.outbox = []
    return mail.outbox


@pytest.fixture
def mock_email_settings():
    """Return mock email settings for testing."""
    return {
        'CENTER_BASE_URL': 'https://portal.example.com',
        'CENTER_NAME': 'Test Research Center',
        'EMAIL_SENDER': 'noreply@example.com',
        'CENTER_HELP_EMAIL': 'help@example.com',
        'EMAIL_SIGNATURE': 'Test Research Team',
        'ADMIN_EMAIL_LIST': ['admin1@example.com', 'admin2@example.com'],
    }
