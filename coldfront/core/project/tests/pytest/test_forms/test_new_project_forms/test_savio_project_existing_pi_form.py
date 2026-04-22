"""Tests for SavioProjectExistingPIForm.disable_pi_choices() per-request cache."""

import pytest
from unittest.mock import Mock, patch

from coldfront.core.project.forms_.new_project_forms.request_forms import (
    SavioProjectExistingPIForm,
)

_BASE = 'coldfront.core.project.forms_.new_project_forms.request_forms'


def _qs_mock():
    """Return a mock queryset whose .values_list() returns an empty list."""
    qs = Mock()
    qs.values_list.return_value = []
    return qs


def _patches(ca_wrapper):
    """Return a list of (target, kwargs) pairs for the five expensive functions
    and the ComputingAllowance constructor, ready to be used with patch()."""
    return [
        (f'{_BASE}.ComputingAllowance', dict(return_value=ca_wrapper)),
        (f'{_BASE}.project_pi_pks', dict(return_value=set())),
        (f'{_BASE}.non_denied_new_project_request_statuses',
         dict(return_value=_qs_mock())),
        (f'{_BASE}.pis_with_new_project_requests_pks',
         dict(return_value=set())),
        (f'{_BASE}.non_denied_renewal_request_statuses',
         dict(return_value=_qs_mock())),
        (f'{_BASE}.pis_with_renewal_requests_pks', dict(return_value=set())),
    ]


def _ca_wrapper(is_one_per_pi=True):
    wrapper = Mock()
    wrapper.is_one_per_pi.return_value = is_one_per_pi
    wrapper.get_resource.return_value = Mock()
    return wrapper


@pytest.mark.django_db
class TestDisablePIChoicesCache:
    """Tests for the per-request cache in disable_pi_choices()."""

    # -------------------------------------------------------------------------
    # Cache hit: queries run only once across multiple instantiations
    # -------------------------------------------------------------------------

    def test_queries_run_once_when_cache_shared(self):
        """With a shared pi_choices_cache dict, the five expensive queries run
        exactly once across two form instantiations."""
        wrapper = _ca_wrapper()
        cache = {}
        kwargs = dict(
            computing_allowance=Mock(),
            allocation_period=Mock(),
            pi_choices_cache=cache,
        )

        with patch(f'{_BASE}.ComputingAllowance', return_value=wrapper), \
             patch(f'{_BASE}.project_pi_pks',
                   return_value=set()) as mock_pks, \
             patch(f'{_BASE}.non_denied_new_project_request_statuses',
                   return_value=_qs_mock()) as mock_new_statuses, \
             patch(f'{_BASE}.pis_with_new_project_requests_pks',
                   return_value=set()) as mock_new_pks, \
             patch(f'{_BASE}.non_denied_renewal_request_statuses',
                   return_value=_qs_mock()) as mock_renewal_statuses, \
             patch(f'{_BASE}.pis_with_renewal_requests_pks',
                   return_value=set()) as mock_renewal_pks:

            SavioProjectExistingPIForm(**kwargs)   # cache miss → queries run
            SavioProjectExistingPIForm(**kwargs)   # cache hit  → queries skip

        assert mock_pks.call_count == 1
        assert mock_new_statuses.call_count == 1
        assert mock_new_pks.call_count == 1
        assert mock_renewal_statuses.call_count == 1
        assert mock_renewal_pks.call_count == 1

    # -------------------------------------------------------------------------
    # Cache populated after first call
    # -------------------------------------------------------------------------

    def test_cache_populated_after_first_instantiation(self):
        """The cache dict gains a 'disabled_pks' entry after the first form
        instantiation and is not re-computed on the second."""
        wrapper = _ca_wrapper()
        cache = {}

        with patch(f'{_BASE}.ComputingAllowance', return_value=wrapper), \
             patch(f'{_BASE}.project_pi_pks', return_value={10, 20}), \
             patch(f'{_BASE}.non_denied_new_project_request_statuses',
                   return_value=_qs_mock()), \
             patch(f'{_BASE}.pis_with_new_project_requests_pks',
                   return_value={30}), \
             patch(f'{_BASE}.non_denied_renewal_request_statuses',
                   return_value=_qs_mock()), \
             patch(f'{_BASE}.pis_with_renewal_requests_pks',
                   return_value={40}):

            assert 'disabled_pks' not in cache
            SavioProjectExistingPIForm(
                computing_allowance=Mock(),
                allocation_period=Mock(),
                pi_choices_cache=cache,
            )

        assert 'disabled_pks' in cache
        assert cache['disabled_pks'] == {10, 20, 30, 40}

    def test_second_form_uses_cached_disabled_pks(self):
        """The second form's disabled_choices equals the cached set from the
        first form, even though different return values would be produced by a
        fresh query."""
        wrapper = _ca_wrapper()
        cache = {}
        kwargs = dict(
            computing_allowance=Mock(),
            allocation_period=Mock(),
            pi_choices_cache=cache,
        )

        with patch(f'{_BASE}.ComputingAllowance', return_value=wrapper), \
             patch(f'{_BASE}.project_pi_pks', return_value={99}), \
             patch(f'{_BASE}.non_denied_new_project_request_statuses',
                   return_value=_qs_mock()), \
             patch(f'{_BASE}.pis_with_new_project_requests_pks',
                   return_value=set()), \
             patch(f'{_BASE}.non_denied_renewal_request_statuses',
                   return_value=_qs_mock()), \
             patch(f'{_BASE}.pis_with_renewal_requests_pks',
                   return_value=set()):

            form1 = SavioProjectExistingPIForm(**kwargs)

            # Mutate the cache to simulate a different value; the second form
            # must use the cached set, not re-run queries.
            cache['disabled_pks'] = {42}
            form2 = SavioProjectExistingPIForm(**kwargs)

        assert form2.fields['PI'].widget.disabled_choices == {42}

    # -------------------------------------------------------------------------
    # No cache (None): queries run on every instantiation
    # -------------------------------------------------------------------------

    def test_queries_run_each_time_without_cache(self):
        """With pi_choices_cache=None, the five expensive queries fire on
        every form instantiation (backward-compatible behaviour)."""
        wrapper = _ca_wrapper()
        kwargs = dict(
            computing_allowance=Mock(),
            allocation_period=Mock(),
            pi_choices_cache=None,
        )

        with patch(f'{_BASE}.ComputingAllowance', return_value=wrapper), \
             patch(f'{_BASE}.project_pi_pks',
                   return_value=set()) as mock_pks, \
             patch(f'{_BASE}.non_denied_new_project_request_statuses',
                   return_value=_qs_mock()) as mock_new_statuses, \
             patch(f'{_BASE}.pis_with_new_project_requests_pks',
                   return_value=set()) as mock_new_pks, \
             patch(f'{_BASE}.non_denied_renewal_request_statuses',
                   return_value=_qs_mock()) as mock_renewal_statuses, \
             patch(f'{_BASE}.pis_with_renewal_requests_pks',
                   return_value=set()) as mock_renewal_pks:

            SavioProjectExistingPIForm(**kwargs)
            SavioProjectExistingPIForm(**kwargs)

        assert mock_pks.call_count == 2
        assert mock_new_statuses.call_count == 2
        assert mock_new_pks.call_count == 2
        assert mock_renewal_statuses.call_count == 2
        assert mock_renewal_pks.call_count == 2

    # -------------------------------------------------------------------------
    # is_one_per_pi() == False: queries are not called regardless of cache
    # -------------------------------------------------------------------------

    def test_queries_not_called_when_not_one_per_pi(self):
        """When is_one_per_pi() returns False, disable_pi_choices() skips
        the expensive queries — the cache is populated with an empty set."""
        wrapper = _ca_wrapper(is_one_per_pi=False)
        cache = {}

        with patch(f'{_BASE}.ComputingAllowance', return_value=wrapper), \
             patch(f'{_BASE}.project_pi_pks',
                   return_value=set()) as mock_pks, \
             patch(f'{_BASE}.pis_with_new_project_requests_pks',
                   return_value=set()) as mock_new_pks, \
             patch(f'{_BASE}.pis_with_renewal_requests_pks',
                   return_value=set()) as mock_renewal_pks:

            SavioProjectExistingPIForm(
                computing_allowance=Mock(),
                allocation_period=Mock(),
                pi_choices_cache=cache,
            )

        assert mock_pks.call_count == 0
        assert mock_new_pks.call_count == 0
        assert mock_renewal_pks.call_count == 0
        assert cache['disabled_pks'] == set()
