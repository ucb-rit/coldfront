"""Unit tests for PIChoiceField.to_python() caching."""

import pytest
from unittest.mock import Mock, patch

from django import forms

from coldfront.core.project.forms_.new_project_forms.request_forms import (
    PIChoiceField,
)


def _make_field(cache=None):
    """Return a PIChoiceField with a mock queryset and the given cache dict."""
    field = PIChoiceField(queryset=Mock())
    field._to_python_cache = cache
    return field


@pytest.mark.unit
class TestPIChoiceFieldToPythonCache:
    """Unit tests for the per-request cache in PIChoiceField.to_python()."""

    # -------------------------------------------------------------------------
    # Empty values bypass cache entirely
    # -------------------------------------------------------------------------

    def test_empty_string_returns_none_without_touching_cache(self):
        """Empty string is in empty_values; None is returned before the
        cache is consulted and super() is never called."""
        cache = {}
        field = _make_field(cache=cache)
        with patch.object(forms.ModelChoiceField, 'to_python') as mock_super:
            result = field.to_python('')
        assert result is None
        assert mock_super.call_count == 0
        assert not cache

    # -------------------------------------------------------------------------
    # Cache miss: super() called, result stored
    # -------------------------------------------------------------------------

    def test_cache_miss_calls_super(self):
        """On a cache miss super().to_python() is called exactly once."""
        field = _make_field(cache={})
        user = Mock()
        with patch.object(
                forms.ModelChoiceField, 'to_python',
                return_value=user) as mock_super:
            field.to_python('42')
        assert mock_super.call_count == 1

    def test_cache_miss_stores_result(self):
        """The result of a cache miss is written to _to_python_cache."""
        field = _make_field(cache={})
        user = Mock()
        with patch.object(forms.ModelChoiceField, 'to_python', return_value=user):
            field.to_python('42')
        assert field._to_python_cache['42'] is user

    # -------------------------------------------------------------------------
    # Cache hit: super() skipped
    # -------------------------------------------------------------------------

    def test_cache_hit_skips_super(self):
        """A pre-populated cache entry is returned without calling super()."""
        user = Mock()
        field = _make_field(cache={'42': user})
        with patch.object(forms.ModelChoiceField, 'to_python') as mock_super:
            result = field.to_python('42')
        assert mock_super.call_count == 0
        assert result is user

    def test_repeated_calls_hit_cache_after_first(self):
        """super() is called only on the first call; subsequent calls are
        served from the cache."""
        field = _make_field(cache={})
        user = Mock()
        with patch.object(
                forms.ModelChoiceField, 'to_python',
                return_value=user) as mock_super:
            r1 = field.to_python('42')
            r2 = field.to_python('42')
        assert mock_super.call_count == 1
        assert r1 is user
        assert r2 is user

    # -------------------------------------------------------------------------
    # No cache (_to_python_cache is None): super() called every time
    # -------------------------------------------------------------------------

    def test_no_cache_calls_super_every_time(self):
        """With _to_python_cache=None every call goes to super()."""
        field = _make_field(cache=None)
        user = Mock()
        with patch.object(
                forms.ModelChoiceField, 'to_python',
                return_value=user) as mock_super:
            field.to_python('42')
            field.to_python('42')
        assert mock_super.call_count == 2

    # -------------------------------------------------------------------------
    # None result not stored (invalid pk, validation error path)
    # -------------------------------------------------------------------------

    def test_none_result_not_stored_in_cache(self):
        """When super() returns None the result is not cached; the next call
        retries super() rather than returning a frozen None."""
        field = _make_field(cache={})
        with patch.object(
                forms.ModelChoiceField, 'to_python',
                return_value=None) as mock_super:
            field.to_python('99')
            field.to_python('99')
        assert mock_super.call_count == 2
        assert '99' not in field._to_python_cache
