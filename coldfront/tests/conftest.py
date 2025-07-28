"""
Global pytest configuration and fixtures for ColdFront tests.
"""
import pytest
from django.contrib.auth.models import User
from django.test import Client
from unittest.mock import Mock, patch

import factory
from factory.django import DjangoModelFactory


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