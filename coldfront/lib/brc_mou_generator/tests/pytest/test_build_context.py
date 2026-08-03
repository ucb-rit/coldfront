"""Unit tests for each MouGenerator._build_context() method.

These tests call _build_context() directly and assert on the resulting context
dict. No Playwright, no Django, no DB — pure Python. The generator classes are
imported at module level, which triggers the module-level logo loading (reads
coldfront/static/core/portal/imgs/brc_logo.png), but no network access or
browser is involved.
"""

import datetime

import pytest

from coldfront.lib.brc_mou_generator import (
    InstructionalMouGenerator,
    RechargeMouGenerator,
    SecureDirMouGenerator,
)

DIRECTOR_NAME = "Test Director"
DIRECTOR_KWARGS = {
    "director_name": DIRECTOR_NAME,
    "director_title": "Director of Testing",
    "director_signature_b64": "ZmFrZQ==",  # base64("fake")
}


def _base_context(pi_name="Jane Smith", project="ic_test"):
    """Minimal context dict equivalent to what _common_context() produces."""
    return {"pi_name": pi_name, "project": project}


@pytest.mark.unit
class TestInstructionalBuildContext:
    PI_NAME = "Jane Smith"
    PROJECT = "ic_test"
    COURSE_DEPT = "EECS"
    SERVICE_UNITS = 50_000
    ALLOWANCE_END = datetime.date(2026, 12, 31)
    EXTRA_FIELDS = {
        "course_department": COURSE_DEPT,
        "course_name": "CS 161",
        "point_of_contact": "Jane Smith",
        "num_students": 30,
    }

    @pytest.fixture
    def ctx(self):
        context = _base_context(pi_name=self.PI_NAME, project=self.PROJECT)
        InstructionalMouGenerator(**DIRECTOR_KWARGS)._build_context(
            context,
            service_units=self.SERVICE_UNITS,
            extra_fields=self.EXTRA_FIELDS,
            allowance_end=self.ALLOWANCE_END,
        )
        return context

    def test_service_units(self, ctx):
        assert ctx["service_units"] == self.SERVICE_UNITS

    def test_course_dept(self, ctx):
        assert ctx["course_dept"] == self.COURSE_DEPT

    def test_dept_and_pi(self, ctx):
        assert ctx["dept_and_pi"] == f"{self.COURSE_DEPT}/{self.PI_NAME}"

    def test_between(self, ctx):
        assert ctx["between"] == f"{DIRECTOR_NAME} (BRC) and {self.PI_NAME}"

    def test_re(self, ctx):
        assert ctx["re"] == f"{self.COURSE_DEPT}/{self.PI_NAME} ICA Agreement"

    def test_course_name(self, ctx):
        assert ctx["course_name"] == self.EXTRA_FIELDS["course_name"]

    def test_point_of_contact(self, ctx):
        assert ctx["point_of_contact"] == self.EXTRA_FIELDS["point_of_contact"]

    def test_num_students(self, ctx):
        assert ctx["num_students"] == 30

    def test_num_students_coerced_to_int(self):
        """num_students may arrive as a string from extra_fields JSON."""
        context = _base_context(pi_name=self.PI_NAME, project=self.PROJECT)
        extra = {**self.EXTRA_FIELDS, "num_students": "25"}
        InstructionalMouGenerator(**DIRECTOR_KWARGS)._build_context(
            context,
            service_units=self.SERVICE_UNITS,
            extra_fields=extra,
            allowance_end=self.ALLOWANCE_END,
        )
        assert context["num_students"] == 25
        assert isinstance(context["num_students"], int)

    def test_allowance_last_month(self, ctx):
        assert ctx["allowance_last_month"] == "December 2026"

    def test_signature(self, ctx):
        assert ctx["signature"] == f"{self.PI_NAME}<br>{self.COURSE_DEPT}"


@pytest.mark.unit
class TestRechargeBuildContext:
    PI_NAME = "Bob Jones"
    PROJECT = "co_jones"
    SERVICE_UNITS = 100_000
    EXTRA_FIELDS = {"campus_chartstring": "13U00 - FSSF - 19900 - 0 - 0"}

    @pytest.fixture
    def ctx(self):
        context = _base_context(pi_name=self.PI_NAME, project=self.PROJECT)
        RechargeMouGenerator(**DIRECTOR_KWARGS)._build_context(
            context,
            service_units=self.SERVICE_UNITS,
            extra_fields=self.EXTRA_FIELDS,
        )
        return context

    def test_service_units(self, ctx):
        assert ctx["service_units"] == self.SERVICE_UNITS

    def test_between(self, ctx):
        assert ctx["between"] == f"{DIRECTOR_NAME} (BRC) and {self.PI_NAME}"

    def test_re(self, ctx):
        assert ctx["re"] == f"{self.PROJECT} Savio Allowance Purchase Agreement"

    def test_chartstring(self, ctx):
        assert ctx["chartstring"] == self.EXTRA_FIELDS["campus_chartstring"]

    def test_cost_formatted(self, ctx):
        expected = f"${0.01 * self.SERVICE_UNITS:.2f} ($0.01/SU)"
        assert ctx["cost"] == expected

    def test_signature(self, ctx):
        assert ctx["signature"] == f"{self.PI_NAME}<br>{self.PROJECT}"


@pytest.mark.unit
class TestSecureDirBuildContext:
    PI_NAME = "Alice Wu"
    PROJECT = "ac_wu"
    DEPARTMENT = "Sociology"

    @pytest.fixture
    def ctx(self):
        context = _base_context(pi_name=self.PI_NAME, project=self.PROJECT)
        SecureDirMouGenerator(**DIRECTOR_KWARGS)._build_context(
            context,
            department=self.DEPARTMENT,
        )
        return context

    def test_between(self, ctx):
        assert (
            ctx["between"] == f"RTL / Research IT and {self.DEPARTMENT}/{self.PI_NAME}"
        )

    def test_re(self, ctx):
        assert ctx["re"] == "P2/P3 Savio project Researcher Use Agreement"

    def test_signature(self, ctx):
        assert ctx["signature"] == f"{self.PI_NAME}<br>{self.PROJECT}"
