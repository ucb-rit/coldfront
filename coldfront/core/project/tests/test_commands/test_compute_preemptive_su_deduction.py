"""Tests for the compute_preemptive_su_deduction management command.

Structure
---------
TestComputeE
    Pure unit tests (no DB) for Command._compute_E, the algorithm that
    recovers estimated job charges from usage-history positive diffs.

TestComputePreemptiveSuDeductionHandle
    Tests for the end-to-end handle() method.  All external DB lookups are
    replaced with unittest.mock objects so the tests are self-contained and
    fast.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import StringIO
from unittest.mock import MagicMock, Mock, patch

import pytest

from django.core.exceptions import ObjectDoesNotExist
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from coldfront.core.project.management.commands.compute_preemptive_su_deduction import (
    Command,
    TIMESTAMP_THRESHOLD_SECONDS,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

# Midnight US/Pacific on June 1, 2026 expressed in UTC (Pacific is UTC-7 in PDT)
CUTOFF = datetime(2026, 6, 1, 7, 0, 0, tzinfo=timezone.utc)


def _make_entry(value, history_date):
    """Minimal HistoricalAllocationAttributeUsage substitute."""
    e = Mock()
    e.value = value
    e.history_date = history_date
    return e


def _make_job(job_id, startdate, amount=10.0, enddate=None):
    """Minimal Job substitute."""
    j = Mock()
    j.jobslurmid = job_id
    j.startdate = startdate
    j.enddate = enddate or (CUTOFF + timedelta(hours=1))
    j.amount = amount
    return j


def _make_usage_mock(ascending_entries, pre_reset_entry=None):
    """Return a mock AllocationAttributeUsage whose .history chain handles
    both query patterns used by the command:

      * .filter(...).order_by('-history_date', '-history_id').first()
        → returns pre_reset_entry (defaults to last element of ascending_entries)
      * list(.filter(...).order_by('history_date', 'history_id'))
        → returns ascending_entries
    """
    if pre_reset_entry is None and ascending_entries:
        pre_reset_entry = ascending_entries[-1]

    descending_mock = MagicMock()
    descending_mock.first.return_value = pre_reset_entry

    def order_by_effect(*args):
        if args and str(args[0]).startswith('-'):
            return descending_mock
        # ascending order — return plain list so list() and iteration work
        return ascending_entries

    usage = Mock()
    usage.history.filter.return_value.order_by.side_effect = order_by_effect
    return usage


# ---------------------------------------------------------------------------
# Unit tests for _compute_E (no database required)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestComputeE:
    """Unit tests for Command._compute_E."""

    @staticmethod
    def _compute_e(entries, boundary_jobs):
        usage = Mock()
        usage.history.filter.return_value.order_by.return_value = entries
        return Command()._compute_E(usage, boundary_jobs, CUTOFF)

    # --- edge cases ---

    def test_no_boundary_jobs_returns_zero(self):
        E, e_per_job, ambiguous = self._compute_e([], [])
        assert E == Decimal('0')
        assert e_per_job == {}
        assert ambiguous == []

    def test_no_positive_diffs_all_jobs_flagged_ambiguous(self):
        """History with no positive diffs → every boundary job is ambiguous with E_i = 0."""
        entries = [
            _make_entry(100, CUTOFF - timedelta(hours=3)),
            _make_entry(100, CUTOFF - timedelta(hours=2)),  # diff = 0
            _make_entry(90,  CUTOFF - timedelta(hours=1)),  # diff = -10
        ]
        job = _make_job('111', CUTOFF - timedelta(hours=2))

        E, e_per_job, ambiguous = self._compute_e(entries, [job])

        assert E == Decimal('0')
        assert e_per_job['111'] == Decimal('0')
        assert len(ambiguous) == 1
        assert ambiguous[0][0] == '111'
        assert 'no positive diffs' in ambiguous[0][1]

    # --- single job, clean match ---

    def test_single_job_within_threshold_no_ambiguity(self):
        """Diff timestamp within TIMESTAMP_THRESHOLD_SECONDS of startdate → clean match."""
        job_start = CUTOFF - timedelta(hours=4)
        diff_date = job_start + timedelta(seconds=30)
        entries = [
            _make_entry(200, CUTOFF - timedelta(hours=5)),
            _make_entry(215, diff_date),  # diff = +15
        ]
        job = _make_job('222', job_start, amount=12.0)

        E, e_per_job, ambiguous = self._compute_e(entries, [job])

        assert e_per_job['222'] == Decimal('15')
        assert E == Decimal('15')
        assert ambiguous == []

    # --- single job, suspicious timestamp ---

    def test_single_job_beyond_threshold_flagged_but_value_used(self):
        """Diff > TIMESTAMP_THRESHOLD_SECONDS → flagged ambiguous, but E_i is still assigned."""
        job_start = CUTOFF - timedelta(hours=5)
        diff_date = job_start + timedelta(seconds=TIMESTAMP_THRESHOLD_SECONDS + 60)
        entries = [
            _make_entry(100, CUTOFF - timedelta(hours=6)),
            _make_entry(120, diff_date),  # diff = +20
        ]
        job = _make_job('333', job_start)

        E, e_per_job, ambiguous = self._compute_e(entries, [job])

        assert e_per_job['333'] == Decimal('20')
        assert E == Decimal('20')
        assert len(ambiguous) == 1
        assert '333' in ambiguous[0][0]
        assert 'threshold' in ambiguous[0][1]

    # --- competing jobs (shared diff entry) ---

    def test_two_jobs_competing_for_same_diff_both_zeroed(self):
        """Both jobs map to the same nearest positive diff → both E_i = 0, both flagged."""
        diff_date = CUTOFF - timedelta(hours=4)
        entries = [
            _make_entry(300, CUTOFF - timedelta(hours=5)),
            _make_entry(350, diff_date),  # diff = +50
        ]
        # jobs close together on either side of diff_date
        job_a = _make_job('aaa', diff_date - timedelta(seconds=5))
        job_b = _make_job('bbb', diff_date + timedelta(seconds=5))

        E, e_per_job, ambiguous = self._compute_e(entries, [job_a, job_b])

        assert E == Decimal('0')
        assert e_per_job['aaa'] == Decimal('0')
        assert e_per_job['bbb'] == Decimal('0')
        ambiguous_ids = {a[0] for a in ambiguous}
        assert ambiguous_ids == {'aaa', 'bbb'}
        assert all('shares diff entry' in a[1] for a in ambiguous)

    # --- two jobs, distinct diffs ---

    def test_two_jobs_distinct_diffs_each_matched_correctly(self):
        """Each boundary job is nearest to a different positive diff → clean match for both."""
        t1 = CUTOFF - timedelta(hours=8)
        t2 = CUTOFF - timedelta(hours=4)
        entries = [
            _make_entry(100, CUTOFF - timedelta(hours=9)),
            _make_entry(130, t1 + timedelta(seconds=10)),   # diff = +30
            _make_entry(110, t1 + timedelta(hours=1)),      # diff = -20
            _make_entry(145, t2 + timedelta(seconds=20)),   # diff = +35
        ]
        job_a = _make_job('c1', t1, amount=25.0)
        job_b = _make_job('c2', t2, amount=30.0)

        E, e_per_job, ambiguous = self._compute_e(entries, [job_a, job_b])

        assert e_per_job['c1'] == Decimal('30')
        assert e_per_job['c2'] == Decimal('35')
        assert E == Decimal('65')
        assert ambiguous == []


# ---------------------------------------------------------------------------
# handle() tests (via call_command with mocked DB dependencies)
# ---------------------------------------------------------------------------

_HANDLE_TARGET = 'coldfront.core.project.management.commands.compute_preemptive_su_deduction'

COMMON_ARGS = dict(
    project_name='fc_singlecell',
    previous_allowance=300000,
    year_cutoff_date='2026-06-01',
)


def _run_command(**kwargs):
    """Call compute_preemptive_su_deduction and return captured stdout."""
    out = StringIO()
    opts = {**COMMON_ARGS, **kwargs, 'stdout': out}
    call_command('compute_preemptive_su_deduction', **opts)
    return out.getvalue()


class TestComputePreemptiveSuDeductionHandle(TestCase):
    """Tests for handle(), mocking all external DB dependencies."""

    # --- input validation ---

    def test_invalid_date_format_raises_command_error(self):
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command(
                'compute_preemptive_su_deduction',
                project_name='fc_singlecell',
                previous_allowance=300000,
                year_cutoff_date='01-06-2026',  # wrong format
                stdout=out,
            )

    @patch(f'{_HANDLE_TARGET}.Project')
    def test_nonexistent_project_raises_command_error(self, mock_project):
        mock_project.DoesNotExist = Exception
        mock_project.objects.get.side_effect = mock_project.DoesNotExist
        with self.assertRaises(CommandError):
            _run_command()

    @patch(f'{_HANDLE_TARGET}.get_primary_compute_resource_name',
           return_value='Savio Compute')
    @patch(f'{_HANDLE_TARGET}.get_accounting_allocation_objects')
    @patch(f'{_HANDLE_TARGET}.Project')
    def test_no_active_allocation_raises_command_error(
        self, mock_project, mock_get_accounting, mock_resource_name
    ):
        mock_get_accounting.side_effect = ObjectDoesNotExist
        with self.assertRaises(CommandError):
            _run_command()

    @patch(f'{_HANDLE_TARGET}.Job')
    @patch(f'{_HANDLE_TARGET}.get_accounting_allocation_objects')
    @patch(f'{_HANDLE_TARGET}.Project')
    def test_no_pre_reset_history_raises_command_error(
        self, mock_project, mock_get_accounting, mock_job
    ):
        accounting = MagicMock()
        accounting.allocation_attribute.value = '300000'
        accounting.allocation_attribute_usage.history \
            .filter.return_value.order_by.return_value.first.return_value = None
        mock_get_accounting.return_value = accounting
        mock_job.objects.filter.return_value.order_by.return_value = []

        with self.assertRaises(CommandError):
            _run_command()

    # --- deduction arithmetic: no boundary jobs ---

    @patch(f'{_HANDLE_TARGET}.Job')
    @patch(f'{_HANDLE_TARGET}.get_accounting_allocation_objects')
    @patch(f'{_HANDLE_TARGET}.Project')
    def test_no_boundary_jobs_deduction_equals_u_minus_previous_allowance(
        self, mock_project, mock_get_accounting, mock_job
    ):
        """No boundary jobs: deduction = max(U - previous_allowance, 0)."""
        pre_reset = _make_entry(350000, CUTOFF - timedelta(minutes=5))

        usage = _make_usage_mock([pre_reset])
        accounting = MagicMock()
        accounting.allocation_attribute.value = '300000'
        accounting.allocation_attribute_usage = Mock()
        accounting.allocation_attribute_usage.history = usage.history
        mock_get_accounting.return_value = accounting

        mock_job.objects.filter.return_value.order_by.return_value = []

        output = _run_command()

        # deduction = max(350000 - 300000, 0) = 50000
        assert '50000' in output
        assert 'add_service_units_to_project' in output
        assert '--amount -50000' in output

    @patch(f'{_HANDLE_TARGET}.Job')
    @patch(f'{_HANDLE_TARGET}.get_accounting_allocation_objects')
    @patch(f'{_HANDLE_TARGET}.Project')
    def test_no_boundary_jobs_deduction_clamps_to_zero(
        self, mock_project, mock_get_accounting, mock_job
    ):
        """If U <= previous_allowance, deduction = 0 (no borrowing occurred)."""
        pre_reset = _make_entry(250000, CUTOFF - timedelta(minutes=5))

        usage = _make_usage_mock([pre_reset])
        accounting = MagicMock()
        accounting.allocation_attribute.value = '300000'
        accounting.allocation_attribute_usage = Mock()
        accounting.allocation_attribute_usage.history = usage.history
        mock_get_accounting.return_value = accounting

        mock_job.objects.filter.return_value.order_by.return_value = []

        output = _run_command()

        assert '--amount -0' in output

    # --- deduction arithmetic: with boundary jobs ---

    @patch(f'{_HANDLE_TARGET}.Job')
    @patch(f'{_HANDLE_TARGET}.get_accounting_allocation_objects')
    @patch(f'{_HANDLE_TARGET}.Project')
    def test_boundary_jobs_correct_arithmetic(
        self, mock_project, mock_get_accounting, mock_job
    ):
        """deduction = max(U - (E - A) - previous_allowance, 0).

        Example:
          U = 364075
          E = 15000  (estimated at submission)
          A = 12000  (actual after completion)
          previous_allowance = 300000

          true_consumption = 364075 - (15000 - 12000) = 361075
          deduction = 361075 - 300000 = 61075
        """
        job_start = CUTOFF - timedelta(hours=2)
        diff_date = job_start + timedelta(seconds=10)  # within threshold

        # History: value goes 349075 → 364075 (diff = +15000)
        entry0 = _make_entry(349075, CUTOFF - timedelta(hours=3))
        entry1 = _make_entry(364075, diff_date)
        pre_reset = entry1  # last before cutoff

        entries_ascending = [entry0, entry1]
        usage = _make_usage_mock(entries_ascending, pre_reset_entry=pre_reset)

        accounting = MagicMock()
        accounting.allocation_attribute.value = '450000'  # current allowance
        accounting.allocation_attribute_usage = Mock()
        accounting.allocation_attribute_usage.history = usage.history
        mock_get_accounting.return_value = accounting

        boundary_job = _make_job('12345', job_start, amount=12000.0)
        mock_job.objects.filter.return_value.order_by.return_value = [boundary_job]

        output = _run_command()

        # true_consumption = 364075 - (15000 - 12000) = 361075
        # deduction = 361075 - 300000 = 61075
        assert '364075' in output   # U
        assert '15000' in output    # E
        assert '12000' in output    # A
        assert '361075' in output   # true_consumption
        assert '61075' in output    # deduction
        assert '--amount -61075' in output

    # --- floor vs round ---

    @patch(f'{_HANDLE_TARGET}.Job')
    @patch(f'{_HANDLE_TARGET}.get_accounting_allocation_objects')
    @patch(f'{_HANDLE_TARGET}.Project')
    def test_deduction_is_floored_not_rounded(
        self, mock_project, mock_get_accounting, mock_job
    ):
        """Fractional deduction is truncated toward zero (floor), not rounded."""
        # U = 300000.9, previous_allowance = 300000
        # true_consumption = 300000.9, deduction = 0.9 → int = 0 (floor)
        pre_reset = _make_entry(300000.9, CUTOFF - timedelta(minutes=5))

        usage = _make_usage_mock([pre_reset])
        accounting = MagicMock()
        accounting.allocation_attribute.value = '300000'
        accounting.allocation_attribute_usage = Mock()
        accounting.allocation_attribute_usage.history = usage.history
        mock_get_accounting.return_value = accounting

        mock_job.objects.filter.return_value.order_by.return_value = []

        output = _run_command()

        assert '--amount -0' in output

    # --- output structure ---

    @patch(f'{_HANDLE_TARGET}.Job')
    @patch(f'{_HANDLE_TARGET}.get_accounting_allocation_objects')
    @patch(f'{_HANDLE_TARGET}.Project')
    def test_output_contains_project_name_and_add_su_command(
        self, mock_project, mock_get_accounting, mock_job
    ):
        pre_reset = _make_entry(350000, CUTOFF - timedelta(minutes=1))

        usage = _make_usage_mock([pre_reset])
        accounting = MagicMock()
        accounting.allocation_attribute.value = '300000'
        accounting.allocation_attribute_usage = Mock()
        accounting.allocation_attribute_usage.history = usage.history
        mock_get_accounting.return_value = accounting
        mock_job.objects.filter.return_value.order_by.return_value = []

        output = _run_command()

        assert 'fc_singlecell' in output
        assert 'add_service_units_to_project' in output
        assert '--project_name fc_singlecell' in output
        assert '--reason' in output
