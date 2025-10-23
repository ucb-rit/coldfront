"""URL configuration for cluster storage API."""
from django.urls import path

from coldfront.plugins.cluster_storage.api import views


urlpatterns = [
    path(
        'requests/next/claim/',
        views.claim_next_storage_request,
        name='storage-request-claim-next'),
    path(
        'requests/<int:pk>/complete/',
        views.complete_storage_request,
        name='storage-request-complete'),
]
