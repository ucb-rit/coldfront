"""Unit tests for the project-request chooser URL redirect."""

import pytest
from django.test import RequestFactory
from django.urls import reverse
from django.views.generic import RedirectView


@pytest.mark.unit
class TestProjectRequestViewRedirect:
    """Test that project-request redirects to the primary cluster landing
    now that Vector has been retired."""

    def test_redirects_to_primary_cluster_landing(self):
        """GET project-request should return a 302 to project-request-landing."""
        factory = RequestFactory()
        request = factory.get('/project/project-request/')
        view = RedirectView.as_view(pattern_name='project-request-landing')
        response = view(request)
        assert response.status_code == 302
        assert response['Location'] == reverse('project-request-landing')
