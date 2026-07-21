"""Custom Django test runner that reports per-test timing.

Usage:
    python manage.py test --testrunner=coldfront.tests.timing_runner.TimingTestRunner

Pair with Django's built-in --timing flag for full breakdown:
    python manage.py test --timing --testrunner=coldfront.tests.timing_runner.TimingTestRunner
"""

import time
import unittest

from django.test.runner import DiscoverRunner


class TimingTestRunner(DiscoverRunner):
    """A DiscoverRunner that prints a sorted report of the N slowest tests."""

    TOP_N = 50

    def get_resultclass(self):
        base = super().get_resultclass() or unittest.TextTestResult
        runner = self

        class TimedResult(base):
            def startTest(self, test):
                self._test_start_time = time.monotonic()
                super().startTest(test)

            def stopTest(self, test):
                elapsed = time.monotonic() - getattr(
                    self, "_test_start_time", time.monotonic()
                )
                runner._timings.append((elapsed, str(test)))
                super().stopTest(test)

        return TimedResult

    def run_tests(self, test_labels, **kwargs):
        self._timings = []
        failures = super().run_tests(test_labels, **kwargs)
        self._print_timing_report()
        return failures

    def _print_timing_report(self):
        if not self._timings:
            return
        timings = sorted(self._timings, reverse=True)
        n = min(self.TOP_N, len(timings))
        total = sum(elapsed for elapsed, _ in timings)
        sep = "=" * 72
        print(f"\n{sep}")
        print(f"SLOWEST {n} TESTS (of {len(timings)} total, {total:.1f}s combined)")
        print(sep)
        for elapsed, test_id in timings[:n]:
            print(f"  {elapsed:7.3f}s  {test_id}")
        print(sep)
