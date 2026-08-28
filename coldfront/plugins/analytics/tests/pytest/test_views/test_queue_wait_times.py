"""Component tests for CPU and GPU queue wait times views."""

from django.db import OperationalError
from django.urls import reverse
import pytest


@pytest.mark.component
class TestCpuQueueWaitTimesView:
    URL = "analytics:cpu-queue-wait-times"

    # ── context variables ─────────────────────────────────────────────────────

    def test_page_title_is_cpu(self, viewer_client, brc_infra):
        response = viewer_client.get(reverse(self.URL))
        assert response.context["page_title"] == "CPU Queue Wait Times"

    def test_valid_days_list_in_context(self, viewer_client, brc_infra):
        response = viewer_client.get(reverse(self.URL))
        assert response.context["valid_days"] == [30, 90, 180, 365]

    # ── days parameter ────────────────────────────────────────────────────────

    def test_default_days_is_30(self, viewer_client, brc_infra):
        response = viewer_client.get(reverse(self.URL))
        assert response.context["days"] == 30

    def test_valid_days_param_respected(self, viewer_client, brc_infra):
        for days in (30, 90, 180, 365):
            response = viewer_client.get(reverse(self.URL), {"days": str(days)})
            assert response.context["days"] == days

    def test_out_of_range_days_falls_back_to_default(self, viewer_client, brc_infra):
        response = viewer_client.get(reverse(self.URL), {"days": "999"})
        assert response.context["days"] == 30

    def test_nonnumeric_days_falls_back_to_default(self, viewer_client, brc_infra):
        response = viewer_client.get(reverse(self.URL), {"days": "banana"})
        assert response.context["days"] == 30

    # ── show_all_qos parameter ────────────────────────────────────────────────

    def test_show_all_qos_false_by_default(self, viewer_client, brc_infra):
        response = viewer_client.get(reverse(self.URL))
        assert response.context["show_all_qos"] is False

    def test_show_all_qos_true_when_param_is_1(self, viewer_client, brc_infra):
        response = viewer_client.get(reverse(self.URL), {"show_all_qos": "1"})
        assert response.context["show_all_qos"] is True

    def test_show_all_qos_false_when_param_is_not_1(self, viewer_client, brc_infra):
        response = viewer_client.get(reverse(self.URL), {"show_all_qos": "0"})
        assert response.context["show_all_qos"] is False

    # ── caching behaviour ─────────────────────────────────────────────────────

    def test_cache_hit_skips_db(self, viewer_client, brc_infra):
        brc_infra["cache"].get.return_value = {
            "rows": [],
            "generated_at": "2025-01-01 00:00 UTC",
        }
        viewer_client.get(reverse(self.URL))
        brc_infra["conn"].cursor.assert_not_called()

    def test_result_stored_in_cache_on_miss(self, viewer_client, brc_infra):
        viewer_client.get(reverse(self.URL))
        assert brc_infra["cache"].set.called

    def test_show_all_qos_scopes_cache_key(self, viewer_client, brc_infra):
        # Collect the cache keys used for filtered vs. all-QoS requests.
        recorded_keys = []
        brc_infra["cache"].set.side_effect = lambda key, val, ttl: recorded_keys.append(
            key
        )

        viewer_client.get(reverse(self.URL))
        viewer_client.get(reverse(self.URL), {"show_all_qos": "1"})

        assert len(recorded_keys) == 2
        assert recorded_keys[0] != recorded_keys[1]
        assert "filtered" in recorded_keys[0]
        assert "all" in recorded_keys[1]

    # ── error handling ────────────────────────────────────────────────────────

    def test_db_error_sets_error_context(self, viewer_client, brc_infra):
        brc_infra["conn"].cursor.side_effect = OperationalError("db down")
        response = viewer_client.get(reverse(self.URL))
        assert response.status_code == 200
        assert "error" in response.context

    def test_db_error_does_not_set_rows(self, viewer_client, brc_infra):
        brc_infra["conn"].cursor.side_effect = OperationalError("db down")
        response = viewer_client.get(reverse(self.URL))
        assert "rows" not in response.context

    # ── row shape ─────────────────────────────────────────────────────────────

    def test_rows_have_expected_keys(self, viewer_client, brc_infra):
        brc_infra["cursor"].fetchall.return_value = [
            ("savio2", "savio_normal", 100, 5.0, 15.0)
        ]
        response = viewer_client.get(reverse(self.URL))
        rows = response.context["rows"]
        assert len(rows) == 1
        assert {"partition", "qos", "jobs", "p50_display", "p90_display"} <= rows[
            0
        ].keys()

    def test_none_wait_time_displayed_as_na(self, viewer_client, brc_infra):
        brc_infra["cursor"].fetchall.return_value = [
            ("savio2", "savio_normal", 5, None, None)
        ]
        response = viewer_client.get(reverse(self.URL))
        row = response.context["rows"][0]
        assert row["p50_display"] == "N/A"
        assert row["p90_display"] == "N/A"


@pytest.mark.component
class TestGpuQueueWaitTimesView:
    URL = "analytics:gpu-queue-wait-times"

    def test_page_title_is_gpu(self, viewer_client, brc_infra):
        response = viewer_client.get(reverse(self.URL))
        assert response.context["page_title"] == "GPU Queue Wait Times"

    def test_default_days_is_30(self, viewer_client, brc_infra):
        response = viewer_client.get(reverse(self.URL))
        assert response.context["days"] == 30

    def test_valid_days_param_respected(self, viewer_client, brc_infra):
        response = viewer_client.get(reverse(self.URL), {"days": "180"})
        assert response.context["days"] == 180

    def test_invalid_days_falls_back(self, viewer_client, brc_infra):
        response = viewer_client.get(reverse(self.URL), {"days": "7"})
        assert response.context["days"] == 30

    def test_show_all_qos_false_by_default(self, viewer_client, brc_infra):
        response = viewer_client.get(reverse(self.URL))
        assert response.context["show_all_qos"] is False

    def test_show_all_qos_true_when_param_is_1(self, viewer_client, brc_infra):
        response = viewer_client.get(reverse(self.URL), {"show_all_qos": "1"})
        assert response.context["show_all_qos"] is True

    def test_cache_hit_skips_db(self, viewer_client, brc_infra):
        brc_infra["cache"].get.return_value = {
            "rows": [],
            "generated_at": "2025-01-01 00:00 UTC",
        }
        viewer_client.get(reverse(self.URL))
        brc_infra["conn"].cursor.assert_not_called()

    def test_result_stored_in_cache_on_miss(self, viewer_client, brc_infra):
        viewer_client.get(reverse(self.URL))
        assert brc_infra["cache"].set.called

    def test_db_error_sets_error_context(self, viewer_client, brc_infra):
        brc_infra["conn"].cursor.side_effect = OperationalError("db down")
        response = viewer_client.get(reverse(self.URL))
        assert response.status_code == 200
        assert "error" in response.context

    def test_rows_have_expected_keys(self, viewer_client, brc_infra):
        brc_infra["cursor"].fetchall.return_value = [
            ("savio3_gpu", "savio_gpu", 50, 10.0, 30.0)
        ]
        response = viewer_client.get(reverse(self.URL))
        rows = response.context["rows"]
        assert len(rows) == 1
        assert {"partition", "qos", "jobs", "p50_display", "p90_display"} <= rows[
            0
        ].keys()
