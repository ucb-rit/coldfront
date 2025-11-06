import os
import sys
from io import StringIO

import pytest
from django.core.management import call_command
from flags.state import enable_flag


def pytest_configure(config):
    """Pytest hook that runs before Django setup.

    This configures Django settings before Django loads URL patterns,
    ensuring feature flags are enabled for URL registration.
    """
    from django.conf import settings

    # Ensure FLAGS setting exists
    if not hasattr(settings, 'FLAGS'):
        settings.FLAGS = {}

    # Enable feature flags needed for URL registration
    settings.FLAGS['FACULTY_STORAGE_ALLOCATIONS_ENABLED'] = [
        {'condition': 'boolean', 'value': True}
    ]
    settings.FLAGS['SERVICE_UNITS_PURCHASABLE'] = [
        {'condition': 'boolean', 'value': True}
    ]


def pytest_ignore_collect(collection_path, path, config):
    """Skip collection of plugin tests if the plugin is not installed.

    This prevents pytest from trying to import plugin modules (and their
    models) when the plugin isn't in INSTALLED_APPS, which would cause
    RuntimeError during test collection.
    """
    from django.conf import settings

    # Convert to string for path matching
    path_str = str(collection_path)

    # Skip faculty_storage_allocations plugin tests if not installed
    if 'faculty_storage_allocations' in path_str:
        if 'coldfront.plugins.faculty_storage_allocations' not in settings.INSTALLED_APPS:
            return True

    return False


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """Set up the test database with required objects.

    This runs ONCE per test session (not per test!), before any tests run.
    It calls all the management commands that create essential database
    objects needed for the application to function.

    This replaces the BaseTestMixin.call_setup_commands() approach which
    runs for every test class in Django unittest.
    """
    with django_db_blocker.unblock():
        # FLAGS in settings were enabled in pytest_configure hook above
        # Now enable flags for runtime checks (requires database access)
        enable_flag('FACULTY_STORAGE_ALLOCATIONS_ENABLED', create_boolean_condition=True)
        enable_flag('SERVICE_UNITS_PURCHASABLE', create_boolean_condition=True)

        # Suppress command output
        out, err = StringIO(), StringIO()
        sys.stdout = open(os.devnull, 'w')

        # Run setup commands in order
        commands = [
            'add_resource_defaults',
            'add_allocation_defaults',
            'add_accounting_defaults',
            'create_allocation_periods',
            'add_allowance_defaults',
            'import_field_of_science_data',
            'add_default_project_choices',
            'create_staff_group',
            'add_default_user_choices',
            'add_directory_defaults',
        ]

        for command in commands:
            call_command(command, stdout=out, stderr=err)

        # Add faculty_storage_allocations plugin defaults (flag already enabled above)
        call_command('add_faculty_directory_defaults', stdout=out, stderr=err)

        # Restore stdout
        sys.stdout = sys.__stdout__


# ============================================================================
# Common Helper Fixtures (based on TestBase methods)
# ============================================================================

@pytest.fixture
def create_active_project_with_pi(db):
    """Factory fixture for creating active projects with a PI.

    Returns a function that creates an 'Active' Project with a PI.
    Mimics TestBase.create_active_project_with_pi() method.

    Usage:
        project = create_active_project_with_pi('fc_test', pi_user)
    """
    from coldfront.core.project.models import (
        Project, ProjectStatusChoice, ProjectUser,
        ProjectUserRoleChoice, ProjectUserStatusChoice
    )

    def _create(project_name, pi_user):
        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        project = Project.objects.create(
            name=project_name,
            title=project_name,
            status=active_project_status
        )
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator'
        )
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active'
        )
        ProjectUser.objects.create(
            project=project,
            role=pi_role,
            status=active_project_user_status,
            user=pi_user
        )
        return project

    return _create


@pytest.fixture
def sign_user_access_agreement(db):
    """Factory fixture for signing user access agreements.

    Returns a function that signs the access agreement for a user.
    This creates the UserProfile if it doesn't exist, sets the
    access_agreement_signed_date, and refreshes the user from the
    database to clear cached relationships.

    Mimics TestBase.sign_user_access_agreement() method.

    Usage:
        sign_user_access_agreement(user)
    """
    from coldfront.core.user.models import UserProfile
    from coldfront.core.utils.common import utc_now_offset_aware

    def _sign(user):
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.access_agreement_signed_date = utc_now_offset_aware()
        profile.save()
        # Refresh user to clear cached userprofile relationship
        user.refresh_from_db()

    return _sign


@pytest.fixture
def password():
    """Return a standard test password.

    Mimics TestBase.password attribute.
    """
    return 'password'


def pytest_collection_modifyitems(items):
    """Mark all unmarked tests as acceptance tests."""
    for item in items:
        markers = list(item.iter_markers())
        if not markers:
            item.add_marker(pytest.mark.acceptance)


# def pytest_collection_modifyitems(config, items):
#     selected_items = []
#     deselected = []

#     for item in items:
#         # Check if the test has *any* markers
#         # Though this isn't correct either b/c it ignores the provided mark in pytest -m "mark"???
#         if list(item.iter_markers()):
#             selected_items.append(item)
#         else:
#             deselected.append(item)

#     if deselected:
#         config.hook.pytest_deselected(items=deselected)

#     items[:] = selected_items
