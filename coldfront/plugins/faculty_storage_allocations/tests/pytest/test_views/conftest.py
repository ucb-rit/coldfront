"""Fixtures specific to view tests."""

import pytest
from django.test import Client, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware


@pytest.fixture
def authenticated_client(test_user):
    """Return an authenticated Django test client."""
    client = Client()
    client.force_login(test_user)
    return client


@pytest.fixture
def staff_client(test_staff_user):
    """Return an authenticated staff client."""
    client = Client()
    client.force_login(test_staff_user)
    return client


@pytest.fixture
def request_factory():
    """Return a Django RequestFactory instance."""
    return RequestFactory()


@pytest.fixture
def request_with_session(request_factory):
    """Return a factory for creating requests with session support."""
    def _create_request(method='GET', path='/', user=None, **kwargs):
        if method.upper() == 'GET':
            request = request_factory.get(path, **kwargs)
        elif method.upper() == 'POST':
            request = request_factory.post(path, **kwargs)
        else:
            raise ValueError(f'Unsupported method: {method}')

        # Add session support
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(request)
        request.session.save()

        # Add messages support
        messages_middleware = MessageMiddleware(lambda x: x)
        messages_middleware.process_request(request)

        # Add user if provided
        if user:
            request.user = user

        return request

    return _create_request
