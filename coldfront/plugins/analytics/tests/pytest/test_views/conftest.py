"""Fixtures specific to analytics view tests."""

from unittest.mock import MagicMock, patch

from django.test import Client
import pytest


@pytest.fixture
def anon_client():
    """Unauthenticated client."""
    return Client()


@pytest.fixture
def regular_client(regular_user):
    """Client logged in as a regular (unprivileged) user."""
    client = Client()
    client.force_login(regular_user)
    return client


@pytest.fixture
def viewer_client(analytics_viewer):
    """Client logged in as an analytics_viewers group member."""
    client = Client()
    client.force_login(analytics_viewer)
    return client


@pytest.fixture
def staff_client(staff_user):
    """Client logged in as a staff user."""
    client = Client()
    client.force_login(staff_user)
    return client


@pytest.fixture
def superuser_client(superuser):
    """Client logged in as a superuser."""
    client = Client()
    client.force_login(superuser)
    return client


def _brc(flag_name, **kwargs):
    return flag_name == "BRC_ONLY"


@pytest.fixture
def brc_infra():
    """Patch analytics views to use the BRC cluster with a stubbed cache and DB.

    Yields a dict with keys 'cache', 'conn', and 'cursor' so individual tests
    can override return values (e.g. simulate a cache hit or a DB error).
    """
    mock_cursor = MagicMock()
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    with patch("coldfront.plugins.analytics.views.flag_enabled", side_effect=_brc):
        with patch("coldfront.plugins.analytics.views.cache") as mock_cache:
            with patch("coldfront.plugins.analytics.views.connection") as mock_conn:
                mock_cache.get.return_value = None
                mock_conn.cursor.return_value = mock_cursor
                yield {
                    "cache": mock_cache,
                    "conn": mock_conn,
                    "cursor": mock_cursor,
                }
