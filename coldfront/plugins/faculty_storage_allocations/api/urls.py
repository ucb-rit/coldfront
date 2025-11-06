"""URL configuration for Faculty Storage Allocations API."""
from django.urls import path

from coldfront.plugins.faculty_storage_allocations.api import views


urlpatterns = [
    path(
        'requests/next/claim/',
        views.claim_next_fsa_request,
        name='faculty-storage-allocation-request-claim-next'),
    path(
        'requests/<int:pk>/complete/',
        views.complete_fsa_request,
        name='faculty-storage-allocation-request-complete'),
]
