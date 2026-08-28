"""Unit tests for analytics helper functions."""

from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
import pytest

from coldfront.plugins.analytics.views import (
    _BRC_GPU_PARTITIONS,
    _LRC_GPU_PARTITIONS,
    _cluster_tag,
    _cpu_partition_clause,
    _cpu_qos_clause,
    _fmt,
    _gpu_partition_clause,
    _gpu_qos_clause,
)


def _brc(flag_name, **kwargs):
    return flag_name == "BRC_ONLY"


def _lrc(flag_name, **kwargs):
    return flag_name == "LRC_ONLY"


def _neither(flag_name, **kwargs):
    return False


# ── _fmt ─────────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestFmt:
    def test_none_returns_na(self):
        assert _fmt(None) == "N/A"

    def test_zero_returns_zero_seconds(self):
        assert _fmt(0) == "~0s"

    def test_sub_minute_rounds_to_seconds(self):
        assert _fmt(0.5) == "30s"

    def test_sub_minute_zero_seconds(self):
        assert _fmt(0.001) == "~0s"

    def test_minutes_only(self):
        assert _fmt(45) == "45m"

    def test_hours_with_remainder(self):
        assert _fmt(90) == "1h 30m"

    def test_hours_exact(self):
        assert _fmt(120) == "2h"

    def test_days_with_hours(self):
        assert _fmt(25 * 60) == "1d 1h"

    def test_days_exact(self):
        assert _fmt(48 * 60) == "2d"


# ── _cluster_tag ──────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestClusterTag:
    def test_brc_flag_returns_brc(self):
        with patch("coldfront.plugins.analytics.views.flag_enabled", side_effect=_brc):
            assert _cluster_tag() == "brc"

    def test_lrc_flag_returns_lrc(self):
        with patch("coldfront.plugins.analytics.views.flag_enabled", side_effect=_lrc):
            assert _cluster_tag() == "lrc"

    def test_neither_flag_raises(self):
        with patch(
            "coldfront.plugins.analytics.views.flag_enabled", side_effect=_neither
        ):
            with pytest.raises(ImproperlyConfigured):
                _cluster_tag()


# ── _cpu_partition_clause ─────────────────────────────────────────────────────


@pytest.mark.unit
class TestCpuPartitionClause:
    def test_brc_uses_savio_prefix(self):
        with patch("coldfront.plugins.analytics.views.flag_enabled", side_effect=_brc):
            sql, params = _cpu_partition_clause()
        assert "LIKE %s" in sql
        assert params == ["savio%"]

    def test_lrc_uses_lr_prefix(self):
        with patch("coldfront.plugins.analytics.views.flag_enabled", side_effect=_lrc):
            _, params = _cpu_partition_clause()
        assert params == ["lr%"]

    def test_neither_raises(self):
        with patch(
            "coldfront.plugins.analytics.views.flag_enabled", side_effect=_neither
        ):
            with pytest.raises(ImproperlyConfigured):
                _cpu_partition_clause()


# ── _gpu_partition_clause ─────────────────────────────────────────────────────


@pytest.mark.unit
class TestGpuPartitionClause:
    def test_brc_uses_brc_gpu_partitions(self):
        with patch("coldfront.plugins.analytics.views.flag_enabled", side_effect=_brc):
            sql, params = _gpu_partition_clause()
        assert "IN" in sql
        assert set(params) == set(_BRC_GPU_PARTITIONS)

    def test_lrc_uses_lrc_gpu_partitions(self):
        with patch("coldfront.plugins.analytics.views.flag_enabled", side_effect=_lrc):
            _, params = _gpu_partition_clause()
        assert set(params) == set(_LRC_GPU_PARTITIONS)

    def test_neither_raises(self):
        with patch(
            "coldfront.plugins.analytics.views.flag_enabled", side_effect=_neither
        ):
            with pytest.raises(ImproperlyConfigured):
                _gpu_partition_clause()


# ── _cpu_qos_clause ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCpuQosClause:
    def test_brc_uses_savio_prefix(self):
        with patch("coldfront.plugins.analytics.views.flag_enabled", side_effect=_brc):
            _, params = _cpu_qos_clause()
        assert params == ["savio%"]

    def test_lrc_uses_lr_prefix(self):
        with patch("coldfront.plugins.analytics.views.flag_enabled", side_effect=_lrc):
            _, params = _cpu_qos_clause()
        assert params == ["lr%"]

    def test_neither_raises(self):
        with patch(
            "coldfront.plugins.analytics.views.flag_enabled", side_effect=_neither
        ):
            with pytest.raises(ImproperlyConfigured):
                _cpu_qos_clause()


# ── _gpu_qos_clause ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGpuQosClause:
    def test_brc_uses_savio_prefix(self):
        with patch("coldfront.plugins.analytics.views.flag_enabled", side_effect=_brc):
            _, params = _gpu_qos_clause()
        assert params == ["savio%"]

    def test_lrc_uses_es_prefix(self):
        with patch("coldfront.plugins.analytics.views.flag_enabled", side_effect=_lrc):
            _, params = _gpu_qos_clause()
        assert params == ["es%"]

    def test_neither_raises(self):
        with patch(
            "coldfront.plugins.analytics.views.flag_enabled", side_effect=_neither
        ):
            with pytest.raises(ImproperlyConfigured):
                _gpu_qos_clause()
