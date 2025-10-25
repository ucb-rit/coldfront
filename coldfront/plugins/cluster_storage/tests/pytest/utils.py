"""Shared test utilities for cluster_storage plugin tests.

This module provides common utilities, mocks, and helper functions
used across multiple test modules. Not a test file itself.
"""

from datetime import datetime
from unittest.mock import Mock
from django.utils import timezone


class MockCache:
    """Mock Django cache for testing."""

    def __init__(self):
        self._store = {}

    def get(self, key, default=None):
        return self._store.get(key, default)

    def set(self, key, value, timeout=None):
        self._store[key] = value

    def delete(self, key):
        if key in self._store:
            del self._store[key]

    def clear(self):
        self._store.clear()

    def __contains__(self, key):
        return key in self._store

    def __getitem__(self, key):
        if key in self._store:
            return self._store[key]
        raise KeyError(key)

    def __setitem__(self, key, value):
        self.set(key, value)


class MockUser:
    """Mock Django User object for testing."""

    def __init__(self, user_id, username='testuser', email='test@example.com'):
        self.id = user_id
        self.username = username
        self.email = email
        self.is_staff = False
        self.is_superuser = False


def assert_request_state_valid(request):
    """Assert that a storage request has valid state structure.

    Args:
        request: FacultyStorageAllocationRequest instance
    """
    assert 'eligibility' in request.state
    assert 'status' in request.state['eligibility']
    assert 'timestamp' in request.state['eligibility']

    assert 'setup' in request.state
    assert 'intake_consistency' in request.state


def create_test_request_data(**kwargs):
    """Factory function for creating test request data.

    Args:
        **kwargs: Override default values

    Returns:
        dict: Test request data
    """
    defaults = {
        'requested_amount_gb': 1000,
        'justification': 'Test justification for storage request',
    }
    defaults.update(kwargs)
    return defaults


def assert_state_transition_valid(request, stage, expected_status):
    """Assert that a request's state transition is valid.

    Args:
        request: FacultyStorageAllocationRequest instance
        stage: str - State stage name (e.g., 'eligibility', 'setup')
        expected_status: str - Expected status value
    """
    assert stage in request.state
    assert request.state[stage]['status'] == expected_status

    # Timestamp should be set when status changes
    if expected_status != 'Pending':
        assert 'timestamp' in request.state[stage]
        assert request.state[stage]['timestamp'] is not None


# ============================================================================
# Factory Functions
# ============================================================================

def create_storage_request(status='Under Review', **overrides):
    """Factory for creating storage requests with custom attributes.

    Args:
        status: Status name (default 'Under Review')
        **overrides: Override default field values

    Returns:
        FacultyStorageAllocationRequest instance

    Example:
        request = create_storage_request(
            status='Approved - Queued',
            requested_amount_gb=2000,
            approved_amount_gb=2000,
            project=my_project,
            requester=my_user,
            pi=my_pi,
        )
    """
    from coldfront.plugins.cluster_storage.models import (
        FacultyStorageAllocationRequest,
        FacultyStorageAllocationRequestStatusChoice,
        faculty_storage_allocation_request_state_schema,
    )

    defaults = {
        'requested_amount_gb': 1000,
        'state': faculty_storage_allocation_request_state_schema(),
    }
    defaults.update(overrides)

    # Handle status separately to get or create the status choice
    if 'status' not in defaults:
        status_obj, _ = (
            FacultyStorageAllocationRequestStatusChoice.objects
            .get_or_create(name=status)
        )
        defaults['status'] = status_obj

    return FacultyStorageAllocationRequest.objects.create(**defaults)


def create_allocation_with_storage(project, resource, quota_gb=1000):
    """Factory for creating allocations with storage attributes.

    Args:
        project: Project instance
        resource: Resource instance to attach
        quota_gb: Storage quota in GB (default 1000)

    Returns:
        Allocation instance with attached resource and quota attribute

    Example:
        allocation = create_allocation_with_storage(
            project=my_project,
            resource=storage_resource,
            quota_gb=5000
        )
    """
    from coldfront.core.allocation.models import (
        Allocation,
        AllocationStatusChoice,
        AllocationAttribute,
        AllocationAttributeType,
    )

    allocation = Allocation.objects.create(
        project=project,
        status=AllocationStatusChoice.objects.get_or_create(
            name='Active'
        )[0],
    )
    allocation.resources.add(resource)

    # Add quota attribute
    quota_attr_type, _ = AllocationAttributeType.objects.get_or_create(
        name='Storage Quota (GB)',
        defaults={
            'is_required': True,
            'is_unique': False,
            'is_private': False,
        }
    )
    AllocationAttribute.objects.create(
        allocation=allocation,
        allocation_attribute_type=quota_attr_type,
        value=str(quota_gb),
    )

    return allocation


def update_request_state(request, stage, status, justification='',
                         directory_name=None):
    """Update a storage request's state field for a specific stage.

    Args:
        request: FacultyStorageAllocationRequest instance
        stage: State stage name ('eligibility', 'intake_consistency',
               'setup', 'other')
        status: New status value
        justification: Optional justification text
        directory_name: Optional directory name (for setup stage)

    Returns:
        Updated request instance (not saved to DB)

    Example:
        request = update_request_state(
            request,
            'eligibility',
            'Approved',
            justification='PI is eligible'
        )
        request.save()
    """
    if stage not in request.state:
        raise ValueError(f'Invalid stage: {stage}')

    request.state[stage]['status'] = status
    request.state[stage]['timestamp'] = timezone.now().isoformat()

    if justification:
        request.state[stage]['justification'] = justification

    if directory_name and stage == 'setup':
        request.state[stage]['directory_name'] = directory_name

    return request


def assert_email_sent(mailoutbox, subject_contains, recipient,
                      expected_count=1):
    """Assert that an email was sent with expected properties.

    Args:
        mailoutbox: Django test mail outbox
        subject_contains: String that should be in email subject
        recipient: Email address that should receive the email
        expected_count: Expected number of matching emails (default 1)

    Raises:
        AssertionError: If email expectations not met

    Example:
        assert_email_sent(
            mailoutbox,
            'Storage Request Created',
            'admin@example.com'
        )
    """
    matching_emails = [
        email for email in mailoutbox
        if subject_contains.lower() in email.subject.lower()
        and recipient in email.to
    ]

    assert len(matching_emails) == expected_count, (
        f'Expected {expected_count} email(s) with subject containing '
        f'"{subject_contains}" to {recipient}, '
        f'but found {len(matching_emails)}'
    )


def assert_request_has_allocations(request, expected_count=2):
    """Assert that a storage request has created the expected allocations.

    Args:
        request: FacultyStorageAllocationRequest instance
        expected_count: Expected number of allocations (default 2: groups
                       and scratch)

    Raises:
        AssertionError: If allocation count doesn't match
    """
    allocations = request.project.allocation_set.all()
    assert allocations.count() == expected_count, (
        f'Expected {expected_count} allocation(s), '
        f'but found {allocations.count()}'
    )
