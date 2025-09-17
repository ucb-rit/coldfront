"""
Global pytest configuration and fixtures for ColdFront tests.
"""
import os
import sys
import django
import pytest

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coldfront.config.test_settings')
django.setup()

from django.contrib.auth.models import User, Group
from django.test import Client
from unittest.mock import Mock, patch

import factory
from factory.django import DjangoModelFactory

# Import required models for fixtures
from coldfront.core.project.models import (
    Project, ProjectUser, ProjectStatusChoice,
    ProjectUserStatusChoice, ProjectUserRoleChoice,
    ProjectUserJoinRequest
)
from coldfront.core.allocation.models import (
    Allocation, AllocationStatusChoice, AllocationAttributeType,
    ClusterAccessRequest, ClusterAccessRequestStatusChoice
)
from coldfront.core.resource.models import Resource, ResourceType
from coldfront.core.field_of_science.models import FieldOfScience


# ============================================================================
# Database Setup Fixtures
# ============================================================================

@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """Set up test database with required data."""
    with django_db_blocker.unblock():
        # Create required groups
        Group.objects.get_or_create(name='staff_group')

        # Create required status choices
        ProjectStatusChoice.objects.get_or_create(name='Active')
        ProjectStatusChoice.objects.get_or_create(name='New')
        ProjectStatusChoice.objects.get_or_create(name='Archived')

        ProjectUserStatusChoice.objects.get_or_create(name='Active')
        ProjectUserStatusChoice.objects.get_or_create(name='Pending - Add')
        ProjectUserStatusChoice.objects.get_or_create(name='Denied')
        ProjectUserStatusChoice.objects.get_or_create(name='Removed')

        ProjectUserRoleChoice.objects.get_or_create(name='Principal Investigator')
        ProjectUserRoleChoice.objects.get_or_create(name='Manager')
        ProjectUserRoleChoice.objects.get_or_create(name='User')

        # Create allocation status choices
        AllocationStatusChoice.objects.get_or_create(name='Active')
        AllocationStatusChoice.objects.get_or_create(name='New')
        AllocationStatusChoice.objects.get_or_create(name='Renewal Requested')
        AllocationStatusChoice.objects.get_or_create(name='Denied')
        AllocationStatusChoice.objects.get_or_create(name='Expired')

        # Create cluster access request status choices
        ClusterAccessRequestStatusChoice.objects.get_or_create(name='Pending - Add')
        ClusterAccessRequestStatusChoice.objects.get_or_create(name='Processing')
        ClusterAccessRequestStatusChoice.objects.get_or_create(name='Complete')
        ClusterAccessRequestStatusChoice.objects.get_or_create(name='Denied')

        # Create allocation user status choices
        from coldfront.core.allocation.models import AllocationUserStatusChoice
        AllocationUserStatusChoice.objects.get_or_create(name='Active')
        AllocationUserStatusChoice.objects.get_or_create(name='Pending - Add')
        AllocationUserStatusChoice.objects.get_or_create(name='Denied')
        AllocationUserStatusChoice.objects.get_or_create(name='Removed')

        # Create a default field of science
        FieldOfScience.objects.get_or_create(
            description='Other',
            defaults={'is_selectable': True}
        )

        # Create a default resource type and resource
        resource_type, _ = ResourceType.objects.get_or_create(name='Cluster')
        ResourceType.objects.get_or_create(name='Storage')  # Add Storage resource type
        Resource.objects.get_or_create(
            name='Compute Cluster',  # Changed to include 'Compute' in the name
            defaults={
                'resource_type': resource_type,
                'description': 'Test compute cluster resource',
                'is_available': True,
                'is_public': True,
                'is_allocatable': True,
                'requires_payment': False
            }
        )


# ============================================================================
# Test Markers
# ============================================================================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "whitebox: Whitebox integration tests")
    config.addinivalue_line("markers", "blackbox: Blackbox end-to-end tests")
    config.addinivalue_line("markers", "slow: Slow running tests")


# ============================================================================
# Factory Classes
# ============================================================================

class UserFactory(DjangoModelFactory):
    """Factory for creating User instances."""

    class Meta:
        model = User
        django_get_or_create = ('username',)

    username = factory.Sequence(lambda n: f'testuser{n}')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    is_active = True
    is_staff = False
    is_superuser = False


class ProjectFactory(DjangoModelFactory):
    """Factory for creating Project instances."""

    class Meta:
        model = Project
        django_get_or_create = ('title',)

    title = factory.Sequence(lambda n: f'Test Project {n}')
    description = factory.Faker('text')
    status = factory.LazyFunction(
        lambda: ProjectStatusChoice.objects.get_or_create(name='Active')[0]
    )
    field_of_science = factory.LazyFunction(
        lambda: FieldOfScience.objects.get_or_create(description='Other')[0]
    )


class AllocationFactory(DjangoModelFactory):
    """Factory for creating Allocation instances."""

    class Meta:
        model = Allocation

    status = factory.LazyFunction(
        lambda: AllocationStatusChoice.objects.get_or_create(name='Active')[0]
    )
    justification = factory.Faker('text')
    description = factory.Faker('text')
    is_locked = False


# ============================================================================
# Basic Fixtures
# ============================================================================

@pytest.fixture
def user_factory():
    """Provide UserFactory for creating test users."""
    return UserFactory


@pytest.fixture
def user(db):
    """Create a standard test user."""
    return UserFactory()


@pytest.fixture
def staff_user(db):
    """Create a staff user."""
    return UserFactory(is_staff=True)


@pytest.fixture
def superuser(db):
    """Create a superuser."""
    return UserFactory(is_superuser=True, is_staff=True)


@pytest.fixture
def client():
    """Provide Django test client."""
    return Client()


@pytest.fixture
def authenticated_client(client, user):
    """Provide authenticated Django test client."""
    client.force_login(user)
    return client


@pytest.fixture
def staff_client(client, staff_user):
    """Provide staff authenticated Django test client."""
    client.force_login(staff_user)
    return client


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_logger():
    """Provide a mock logger for testing logging calls."""
    with patch('logging.getLogger') as mock_get_logger:
        mock_logger_instance = Mock()
        mock_get_logger.return_value = mock_logger_instance
        yield mock_logger_instance


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def project_factory():
    """Provide ProjectFactory for creating test projects."""
    return ProjectFactory


@pytest.fixture
def allocation_factory():
    """Provide AllocationFactory for creating test allocations."""
    return AllocationFactory


@pytest.fixture
def project(db):
    """Create a test project."""
    return ProjectFactory()


@pytest.fixture
def allocation(db, project):
    """Create a test allocation."""
    resource = Resource.objects.get_or_create(
        name='Compute Cluster',  # Changed to match the resource created in django_db_setup
        defaults={
            'resource_type': ResourceType.objects.get_or_create(name='Cluster')[0],
            'description': 'Test compute cluster resource',
            'is_available': True,
            'is_public': True,
            'is_allocatable': True,
            'requires_payment': False
        }
    )[0]
    allocation = AllocationFactory(project=project)
    allocation.resources.add(resource)
    return allocation


@pytest.fixture
def project_user(db, project, user):
    """Create a ProjectUser relationship."""
    status = ProjectUserStatusChoice.objects.get_or_create(name='Active')[0]
    role = ProjectUserRoleChoice.objects.get_or_create(name='User')[0]
    return ProjectUser.objects.create(
        project=project,
        user=user,
        status=status,
        role=role
    )


@pytest.fixture
def pi_user(db):
    """Create a PI user."""
    return UserFactory(username='pi_user', first_name='Principal', last_name='Investigator')


@pytest.fixture
def project_with_pi(db, pi_user):
    """Create a project with a PI."""
    project = ProjectFactory()
    status = ProjectUserStatusChoice.objects.get_or_create(name='Active')[0]
    role = ProjectUserRoleChoice.objects.get_or_create(name='Principal Investigator')[0]
    ProjectUser.objects.create(
        project=project,
        user=pi_user,
        status=status,
        role=role
    )
    return project


@pytest.fixture
def sample_tracking_data():
    """Provide sample tracking data for tests."""
    return {
        'status': 'PENDING',
        'message': 'Request is pending approval',
        'details': {
            'request_date': '2025-01-01',
            'reason': 'Test request'
        },
        'can_view': True
    }


@pytest.fixture
def sample_tracking_steps():
    """Provide sample tracking steps for tests."""
    return [
        {'label': 'Request Sent', 'completed': True, 'current': False},
        {'label': 'Under Review', 'completed': False, 'current': True},
        {'label': 'Approved', 'completed': False, 'current': False},
        {'label': 'Complete', 'completed': False, 'current': False},
    ]