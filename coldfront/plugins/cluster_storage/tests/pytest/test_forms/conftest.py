"""Fixtures specific to form tests."""

import pytest


@pytest.fixture
def valid_request_form_data(test_project, test_pi):
    """Return valid form data for creating a storage request."""
    return {
        'project': test_project.id,
        'pi': test_pi.id,
        'requested_amount_gb': 1000,
        'justification': 'We need storage for our research data.',
    }


@pytest.fixture
def invalid_request_form_data():
    """Return invalid form data (missing required fields)."""
    return {
        'requested_amount_gb': -1000,  # Invalid: negative amount
    }
