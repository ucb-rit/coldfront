"""Fixtures specific to signal tests."""

from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_signal_handler():
    """Return a mock signal handler for testing."""
    handler = Mock()
    handler.return_value = None
    return handler
