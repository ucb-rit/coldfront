"""Shared pytest fixtures for analytics plugin tests."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
import pytest

User = get_user_model()


def pytest_configure(config):
    """Ensure the analytics plugin is in INSTALLED_APPS for tests.

    Must run before Django setup so the conditional URL include in
    coldfront/config/urls.py picks up the plugin.
    """
    from django.conf import settings

    plugin_app = "coldfront.plugins.analytics"
    if plugin_app not in settings.INSTALLED_APPS:
        settings.INSTALLED_APPS = [*list(settings.INSTALLED_APPS), plugin_app]


@pytest.fixture
def analytics_viewers_group(db):
    """Return (or create) the analytics_viewers Group."""
    group, _ = Group.objects.get_or_create(name="analytics_viewers")
    return group


@pytest.fixture
def regular_user(db):
    """Authenticated user with no special privileges."""
    return User.objects.create_user(
        username="regular",
        email="regular@example.com",
        password="pass",
    )


@pytest.fixture
def analytics_viewer(db, analytics_viewers_group):
    """User who is a member of the analytics_viewers group."""
    user = User.objects.create_user(
        username="viewer",
        email="viewer@example.com",
        password="pass",
    )
    user.groups.add(analytics_viewers_group)
    return user


@pytest.fixture
def staff_user(db):
    """User with is_staff=True."""
    return User.objects.create_user(
        username="staff",
        email="staff@example.com",
        password="pass",
        is_staff=True,
    )


@pytest.fixture
def superuser(db):
    """Superuser."""
    return User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="pass",
    )
