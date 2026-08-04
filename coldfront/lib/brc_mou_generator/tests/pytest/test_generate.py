"""Unit tests for MouGenerator.generate().

These tests mock _render to avoid launching Playwright, so they run fast
and in any environment. The goal is to confirm the wiring in generate():
- the correct template name is forwarded to _render
- generate() returns whatever _render returns
- the context assembled from _common_context + _build_context reaches _render
  (spot-checked with one common key and one type-specific key per subclass)

Exhaustive context-key assertions live in test_build_context.py.
"""

import datetime
from unittest.mock import patch

import pytest

from coldfront.lib.brc_mou_generator import (
    InstructionalMouGenerator,
    RechargeMouGenerator,
    SecureDirMouGenerator,
)

DIRECTOR_KWARGS = {
    "director_name": "Test Director",
    "director_title": "Director of Testing",
    "director_signature_b64": "ZmFrZQ==",  # base64("fake")
}
FAKE_PDF = b"fake-pdf-bytes"


def _capture_render_call(gen, *args, **kwargs):
    """Call gen.generate() with _render mocked; return (result, template_name, context)."""
    captured = {}

    def _fake_render(context):
        captured["template_name"] = gen._template_name
        captured["context"] = dict(context)
        return FAKE_PDF

    with patch.object(gen, "_render", side_effect=_fake_render):
        result = gen.generate(*args, **kwargs)

    return result, captured["template_name"], captured["context"]


@pytest.mark.unit
class TestInstructionalGenerate:
    EXTRA_FIELDS = {
        "course_department": "EECS",
        "course_name": "CS 161",
        "point_of_contact": "Jane Smith",
        "num_students": 30,
    }

    def _run(self):
        gen = InstructionalMouGenerator(**DIRECTOR_KWARGS)
        return _capture_render_call(
            gen,
            "Jane",
            "Smith",
            "ic_test",
            service_units=50_000,
            extra_fields=self.EXTRA_FIELDS,
            allowance_end=datetime.date(2026, 12, 31),
        )

    def test_returns_render_output(self):
        result, _, _ = self._run()
        assert result == FAKE_PDF

    def test_correct_template(self):
        _, template_name, _ = self._run()
        assert template_name == "instructional.html"

    def test_context_has_common_key(self):
        _, _, ctx = self._run()
        assert ctx["pi_name"] == "Jane Smith"

    def test_context_has_type_specific_key(self):
        _, _, ctx = self._run()
        assert ctx["service_units"] == 50_000


@pytest.mark.unit
class TestRechargeGenerate:
    EXTRA_FIELDS = {"campus_chartstring": "13U00 - FSSF - 19900 - 0 - 0"}

    def _run(self):
        gen = RechargeMouGenerator(**DIRECTOR_KWARGS)
        return _capture_render_call(
            gen,
            "Bob",
            "Jones",
            "co_jones",
            service_units=100_000,
            extra_fields=self.EXTRA_FIELDS,
        )

    def test_returns_render_output(self):
        result, _, _ = self._run()
        assert result == FAKE_PDF

    def test_correct_template(self):
        _, template_name, _ = self._run()
        assert template_name == "recharge.html"

    def test_context_has_common_key(self):
        _, _, ctx = self._run()
        assert ctx["project"] == "co_jones"

    def test_context_has_type_specific_key(self):
        _, _, ctx = self._run()
        assert ctx["chartstring"] == self.EXTRA_FIELDS["campus_chartstring"]


@pytest.mark.unit
class TestSecureDirGenerate:
    def _run(self):
        gen = SecureDirMouGenerator(**DIRECTOR_KWARGS)
        return _capture_render_call(
            gen,
            "Alice",
            "Wu",
            "ac_wu",
            department="Sociology",
        )

    def test_returns_render_output(self):
        result, _, _ = self._run()
        assert result == FAKE_PDF

    def test_correct_template(self):
        _, template_name, _ = self._run()
        assert template_name == "secure_dir.html"

    def test_context_has_common_key(self):
        _, _, ctx = self._run()
        assert ctx["pi_name"] == "Alice Wu"

    def test_context_has_type_specific_key(self):
        _, _, ctx = self._run()
        assert "RTL / Research IT" in ctx["between"]
