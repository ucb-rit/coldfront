"""Component tests for analytics view access control.

All four analytics views share the same AnalyticsAccessMixin, so a single
parametrized class covers them all.
"""

from django.urls import reverse
import pytest

_ALL_VIEWS = [
    "analytics:cpu-queue-wait-times",
    "analytics:gpu-queue-wait-times",
    "analytics:monthly-job-counts",
    "analytics:top-usage",
]


@pytest.mark.component
@pytest.mark.usefixtures("brc_infra")
class TestAnalyticsAccessControl:
    @pytest.mark.parametrize("view_name", _ALL_VIEWS)
    def test_anonymous_redirected_to_login(self, anon_client, view_name):
        response = anon_client.get(reverse(view_name))
        assert response.status_code == 302
        assert "login" in response.url.lower()

    @pytest.mark.parametrize("view_name", _ALL_VIEWS)
    def test_regular_user_gets_403(self, regular_client, view_name):
        response = regular_client.get(reverse(view_name))
        assert response.status_code == 403

    @pytest.mark.parametrize("view_name", _ALL_VIEWS)
    def test_analytics_viewer_gets_200(self, viewer_client, view_name):
        response = viewer_client.get(reverse(view_name))
        assert response.status_code == 200

    @pytest.mark.parametrize("view_name", _ALL_VIEWS)
    def test_staff_gets_200(self, staff_client, view_name):
        response = staff_client.get(reverse(view_name))
        assert response.status_code == 200

    @pytest.mark.parametrize("view_name", _ALL_VIEWS)
    def test_superuser_gets_200(self, superuser_client, view_name):
        response = superuser_client.get(reverse(view_name))
        assert response.status_code == 200
