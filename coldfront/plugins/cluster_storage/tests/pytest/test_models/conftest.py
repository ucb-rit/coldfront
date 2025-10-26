"""Fixtures specific to model tests."""

import pytest
from datetime import datetime
from django.utils import timezone

from coldfront.plugins.cluster_storage.models import (
    faculty_storage_allocation_request_state_schema,
)


@pytest.fixture
def sample_state_pending():
    """Return a state dict with all stages pending."""
    return faculty_storage_allocation_request_state_schema()


@pytest.fixture
def sample_state_approved():
    """Return a state dict with eligibility and intake approved."""
    state = faculty_storage_allocation_request_state_schema()
    now = timezone.now().isoformat()

    state['eligibility']['status'] = 'Approved'
    state['eligibility']['timestamp'] = now
    state['intake_consistency']['status'] = 'Approved'
    state['intake_consistency']['timestamp'] = now

    return state


@pytest.fixture
def sample_state_denied_eligibility():
    """Return a state dict denied at eligibility stage."""
    state = faculty_storage_allocation_request_state_schema()

    state['eligibility']['status'] = 'Denied'
    state['eligibility']['justification'] = 'PI not eligible'
    state['eligibility']['timestamp'] = timezone.now().isoformat()

    return state


@pytest.fixture
def sample_state_denied_intake():
    """Return a state dict denied at intake consistency stage."""
    state = faculty_storage_allocation_request_state_schema()
    now = timezone.now().isoformat()

    # Eligibility passed
    state['eligibility']['status'] = 'Approved'
    state['eligibility']['timestamp'] = now

    # But intake consistency denied
    state['intake_consistency']['status'] = 'Denied'
    state['intake_consistency']['justification'] = (
        'Inconsistent data provided'
    )
    state['intake_consistency']['timestamp'] = now

    return state


@pytest.fixture
def sample_state_setup_in_progress():
    """Return a state dict with setup in progress."""
    state = faculty_storage_allocation_request_state_schema()
    now = timezone.now().isoformat()

    state['eligibility']['status'] = 'Approved'
    state['eligibility']['timestamp'] = now
    state['intake_consistency']['status'] = 'Approved'
    state['intake_consistency']['timestamp'] = now
    state['setup']['status'] = 'In Progress'
    state['setup']['timestamp'] = now
    state['setup']['directory_name'] = 'fc_test_dir'

    return state


@pytest.fixture
def sample_state_complete():
    """Return a state dict with all stages complete."""
    state = faculty_storage_allocation_request_state_schema()
    now = timezone.now().isoformat()

    state['eligibility']['status'] = 'Approved'
    state['eligibility']['timestamp'] = now
    state['intake_consistency']['status'] = 'Approved'
    state['intake_consistency']['timestamp'] = now
    state['setup']['status'] = 'Complete'
    state['setup']['directory_name'] = 'fc_test_dir'
    state['setup']['timestamp'] = now

    return state


@pytest.fixture
def sample_state_denied_other():
    """Return a state dict denied for other reasons."""
    state = faculty_storage_allocation_request_state_schema()
    now = timezone.now().isoformat()

    # Could be denied at any stage, but using 'other' for custom reason
    state['other']['justification'] = 'Custom denial reason'
    state['other']['timestamp'] = now

    return state


@pytest.fixture(params=[
    'Pending',
    'Approved',
    'Denied',
])
def eligibility_status(request):
    """Parametrized fixture for different eligibility statuses."""
    return request.param


@pytest.fixture(params=[
    'Pending',
    'Approved',
    'Denied',
])
def intake_consistency_status(request):
    """Parametrized fixture for different intake consistency statuses."""
    return request.param


@pytest.fixture(params=[
    'Pending',
    'In Progress',
    'Complete',
])
def setup_status(request):
    """Parametrized fixture for different setup statuses."""
    return request.param


@pytest.fixture(params=[
    ('eligibility', 'Denied', 'PI not eligible'),
    ('intake_consistency', 'Denied', 'Inconsistent data'),
    ('other', '', 'Custom denial reason'),
])
def denial_scenarios(request):
    """Parametrized fixture for different denial scenarios.

    Returns:
        tuple: (stage, status, justification)
    """
    return request.param
