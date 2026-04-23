"""Unit tests for SavioProjectRequestWizard.get_cleaned_data_for_step caching."""

import pytest
from unittest.mock import Mock, patch

from formtools.wizard.views import SessionWizardView

from coldfront.core.project.views_.new_project_views.request_views import (
    SavioProjectRequestWizard,
)


def _make_wizard(current_step):
    """Return a bare wizard instance with steps.current set.

    Uses __new__ to skip __init__, which requires full form/session setup.
    """
    wizard = SavioProjectRequestWizard.__new__(SavioProjectRequestWizard)
    steps = Mock()
    steps.current = current_step
    wizard.steps = steps
    return wizard


@pytest.mark.unit
class TestGetCleanedDataForStepCache:
    """Unit tests for the per-request cleaned-data cache on
    SavioProjectRequestWizard."""

    # -------------------------------------------------------------------------
    # Current step: never cached (session data may be stale mid-request)
    # -------------------------------------------------------------------------

    def test_current_step_calls_super_every_time(self):
        """super() is called on every call for the current step; result is
        never cached so stale session data cannot be frozen."""
        wizard = _make_wizard(current_step='2')
        data = {'PI': Mock()}

        with patch.object(
                SessionWizardView, 'get_cleaned_data_for_step',
                return_value=data) as super_mock:
            wizard.get_cleaned_data_for_step('2')
            wizard.get_cleaned_data_for_step('2')

        assert super_mock.call_count == 2

    def test_current_step_not_stored_in_cache(self):
        """The result for the current step is never stored in
        _cleaned_data_cache."""
        wizard = _make_wizard(current_step='2')
        data = {'PI': Mock()}

        with patch.object(
                SessionWizardView, 'get_cleaned_data_for_step',
                return_value=data):
            wizard.get_cleaned_data_for_step('2')

        assert '2' not in getattr(wizard, '_cleaned_data_cache', {})

    # -------------------------------------------------------------------------
    # Non-current step with non-None result is cached in _cleaned_data_cache
    # -------------------------------------------------------------------------

    def test_non_current_step_cached_after_first_call(self):
        """super() is called only once for a non-current step with data."""
        wizard = _make_wizard(current_step='3')
        data = {'computing_allowance': Mock()}

        with patch.object(
                SessionWizardView, 'get_cleaned_data_for_step',
                return_value=data) as super_mock:
            result1 = wizard.get_cleaned_data_for_step('0')
            result2 = wizard.get_cleaned_data_for_step('0')

        assert super_mock.call_count == 1
        assert result1 is result2

    def test_non_current_step_cached_value_is_returned(self):
        """Cached value is the exact object returned by the first super() call."""
        wizard = _make_wizard(current_step='3')
        data = {'computing_allowance': Mock()}

        with patch.object(
                SessionWizardView, 'get_cleaned_data_for_step',
                return_value=data):
            wizard.get_cleaned_data_for_step('0')

        assert wizard._cleaned_data_cache['0'] is data

    def test_different_steps_cached_independently(self):
        """Each step gets its own cache entry; looking up one does not affect
        another."""
        wizard = _make_wizard(current_step='5')
        data_0 = {'computing_allowance': Mock()}
        data_2 = {'PI': Mock()}

        def _side_effect(step):
            return data_0 if step == '0' else data_2

        with patch.object(
                SessionWizardView, 'get_cleaned_data_for_step',
                side_effect=_side_effect) as super_mock:
            wizard.get_cleaned_data_for_step('0')
            wizard.get_cleaned_data_for_step('2')
            wizard.get_cleaned_data_for_step('0')
            wizard.get_cleaned_data_for_step('2')

        # super() called once per unique step
        assert super_mock.call_count == 2
        assert wizard._cleaned_data_cache['0'] is data_0
        assert wizard._cleaned_data_cache['2'] is data_2

    # -------------------------------------------------------------------------
    # None result is not cached (step not yet in session)
    # -------------------------------------------------------------------------

    def test_none_result_not_cached(self):
        """super() is called again when the previous result was None."""
        wizard = _make_wizard(current_step='3')

        with patch.object(
                SessionWizardView, 'get_cleaned_data_for_step',
                return_value=None) as super_mock:
            wizard.get_cleaned_data_for_step('0')
            wizard.get_cleaned_data_for_step('0')

        assert super_mock.call_count == 2

    def test_none_not_stored_in_cache(self):
        """The cache dict has no entry when super() returned None."""
        wizard = _make_wizard(current_step='3')

        with patch.object(
                SessionWizardView, 'get_cleaned_data_for_step',
                return_value=None):
            wizard.get_cleaned_data_for_step('0')

        assert '0' not in getattr(wizard, '_cleaned_data_cache', {})

    def test_none_then_data_is_cached(self):
        """After an initial None, a subsequent non-None result is cached."""
        wizard = _make_wizard(current_step='3')
        data = {'computing_allowance': Mock()}
        side_effects = [None, data]

        with patch.object(
                SessionWizardView, 'get_cleaned_data_for_step',
                side_effect=side_effects) as super_mock:
            result1 = wizard.get_cleaned_data_for_step('0')
            result2 = wizard.get_cleaned_data_for_step('0')
            result3 = wizard.get_cleaned_data_for_step('0')

        # Third call served from cache
        assert super_mock.call_count == 2
        assert result1 is None
        assert result2 is data
        assert result3 is data
