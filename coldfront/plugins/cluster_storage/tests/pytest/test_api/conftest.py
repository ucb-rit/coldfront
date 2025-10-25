"""Fixtures specific to API tests."""

import pytest
from rest_framework.test import APIClient

from coldfront.core.user.models import ExpiringToken


@pytest.fixture
def api_client():
    """Return a DRF APIClient instance."""
    return APIClient()


@pytest.fixture
def authenticated_api_client(test_user, api_client):
    """Return an authenticated API client with token."""
    token, _ = ExpiringToken.objects.get_or_create(user=test_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return api_client


@pytest.fixture
def staff_api_client(test_staff_user, api_client):
    """Return an authenticated staff API client with token."""
    token, _ = ExpiringToken.objects.get_or_create(user=test_staff_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return api_client


@pytest.fixture
def sample_api_request_payload():
    """Return a sample API request payload for creating a storage request."""
    return {
        'requested_amount_gb': 1000,
        'justification': 'API test request',
    }


@pytest.fixture
def sample_api_completion_payload():
    """Return a sample API payload for completing a storage request."""
    return {
        'directory_name': 'test_directory',
        'setup_complete': True,
    }
