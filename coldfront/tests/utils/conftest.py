"""
Fixtures for utils tests - whitebox and unit tests.
"""
import pytest
from datetime import datetime
import factory
from factory.django import DjangoModelFactory

from django.contrib.auth.models import User
from coldfront.core.project.models import (
    Project, ProjectUser, ProjectStatusChoice,
    ProjectUserStatusChoice, ProjectUserRoleChoice,
    ProjectUserJoinRequest
)
from coldfront.core.allocation.models import (
    Allocation, AllocationUser, AllocationStatusChoice,
    ClusterAccessRequest, ClusterAccessRequestStatusChoice
)
from coldfront.core.resource.models import Resource, ResourceType
from coldfront.core.field_of_science.models import FieldOfScience


# ============================================================================
# Factory Classes
# ============================================================================

class ProjectUserFactory(DjangoModelFactory):
    """Factory for creating ProjectUser instances."""

    class Meta:
        model = ProjectUser

    status = factory.LazyFunction(
        lambda: ProjectUserStatusChoice.objects.get_or_create(name='Active')[0]
    )
    role = factory.LazyFunction(
        lambda: ProjectUserRoleChoice.objects.get_or_create(name='User')[0]
    )


class AllocationUserFactory(DjangoModelFactory):
    """Factory for creating AllocationUser instances."""

    class Meta:
        model = AllocationUser

    # AllocationUser doesn't have a status field - removing it


class ProjectUserJoinRequestFactory(DjangoModelFactory):
    """Factory for creating ProjectUserJoinRequest instances."""

    class Meta:
        model = ProjectUserJoinRequest


class ClusterAccessRequestFactory(DjangoModelFactory):
    """Factory for creating ClusterAccessRequest instances."""

    class Meta:
        model = ClusterAccessRequest

    status = factory.LazyFunction(
        lambda: ClusterAccessRequestStatusChoice.objects.get_or_create(name='Pending - Add')[0]
    )


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def project_user_factory():
    """Provide ProjectUserFactory for creating test project users."""
    return ProjectUserFactory


@pytest.fixture
def allocation_user_factory():
    """Provide AllocationUserFactory for creating test allocation users."""
    return AllocationUserFactory


@pytest.fixture
def join_request_factory():
    """Provide ProjectUserJoinRequestFactory for creating test join requests."""
    return ProjectUserJoinRequestFactory


@pytest.fixture
def cluster_access_request_factory():
    """Provide ClusterAccessRequestFactory for creating test cluster access requests."""
    return ClusterAccessRequestFactory


@pytest.fixture
def active_project_user(db, user, project):
    """Create an active ProjectUser without a join request."""
    status = ProjectUserStatusChoice.objects.get_or_create(name='Active')[0]
    role = ProjectUserRoleChoice.objects.get_or_create(name='User')[0]
    return ProjectUser.objects.create(
        project=project,
        user=user,
        status=status,
        role=role
    )


@pytest.fixture
def pending_project_user(db, user, project):
    """Create a pending ProjectUser."""
    status = ProjectUserStatusChoice.objects.get_or_create(name='Pending - Add')[0]
    role = ProjectUserRoleChoice.objects.get_or_create(name='User')[0]
    return ProjectUser.objects.create(
        project=project,
        user=user,
        status=status,
        role=role
    )


@pytest.fixture
def join_request(db, pending_project_user):
    """Create a ProjectUserJoinRequest."""
    return ProjectUserJoinRequest.objects.create(
        project_user=pending_project_user,
        reason='Test join request'
    )


@pytest.fixture
def allocation_user(db, user, allocation):
    """Create an AllocationUser."""
    from coldfront.core.allocation.models import AllocationUserStatusChoice
    status = AllocationUserStatusChoice.objects.get_or_create(name='Active')[0]
    return AllocationUser.objects.create(
        allocation=allocation,
        user=user,
        status=status
    )


@pytest.fixture
def cluster_access_request(db, allocation_user):
    """Create a ClusterAccessRequest."""
    status = ClusterAccessRequestStatusChoice.objects.get_or_create(name='Pending - Add')[0]
    return ClusterAccessRequest.objects.create(
        allocation_user=allocation_user,
        status=status
    )


@pytest.fixture
def mock_join_request_with_dates(db, pending_project_user):
    """Create a mock join request with specific dates."""
    return ProjectUserJoinRequest.objects.create(
        project_user=pending_project_user,
        reason='Test join request with dates',
        created=datetime(2025, 1, 1, 10, 0, 0),
        modified=datetime(2025, 1, 2, 15, 30, 0)
    )


@pytest.fixture
def mock_cluster_request_with_dates(db, allocation_user):
    """Create a mock cluster request with specific dates."""
    status = ClusterAccessRequestStatusChoice.objects.get_or_create(name='Processing')[0]
    return ClusterAccessRequest.objects.create(
        allocation_user=allocation_user,
        status=status,
        created=datetime(2025, 1, 3, 9, 0, 0),
        modified=datetime(2025, 1, 4, 14, 15, 0)
    )