"""Fixtures specific to signal tests."""

import pytest
from unittest.mock import Mock


@pytest.fixture
def mock_signal_handler():
    """Return a mock signal handler for testing."""
    handler = Mock()
    handler.return_value = None
    return handler
