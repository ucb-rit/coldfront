"""Shared fixtures for all API tests."""

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def superuser_token(api_test_data):
    """Provide the superuser's authentication token."""
    return api_test_data['tokens']['superuser']


@pytest.fixture
def api_client(superuser_token):
    """Provide a fresh API client for each test with superuser credentials.

    The client is pre-configured with the superuser's token for convenience.
    Tests can reconfigure credentials as needed using client.credentials().
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token {superuser_token.key}')
    return client
