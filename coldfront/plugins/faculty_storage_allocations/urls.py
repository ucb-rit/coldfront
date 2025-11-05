from django.urls import path

from .views import StorageRequestDetailView
from .views import StorageRequestEditView
from .views import StorageRequestListView
from .views import StorageRequestReviewDenyView
from .views import StorageRequestReviewEligibilityView
from .views import StorageRequestReviewIntakeConsistencyView
from .views import StorageRequestReviewSetupView
from .views import StorageRequestUndenyView


urlpatterns = [
    path(
        '',
        StorageRequestListView.as_view(),
        name='faculty-storage-allocation-request-list'),
    path(
        '<int:pk>/',
        StorageRequestDetailView.as_view(),
        name='faculty-storage-allocation-request-detail'),
    path(
        '<int:pk>/edit/',
        StorageRequestEditView.as_view(),
        name='faculty-storage-allocation-request-edit'),
    path(
        '<int:pk>/eligibility/',
        StorageRequestReviewEligibilityView.as_view(),
        name='faculty-storage-allocation-request-review-eligibility'),
    path(
        '<int:pk>/intake-consistency/',
        StorageRequestReviewIntakeConsistencyView.as_view(),
        name='faculty-storage-allocation-request-review-intake-consistency'),
    path(
        '<int:pk>/setup/',
        StorageRequestReviewSetupView.as_view(),
        name='faculty-storage-allocation-request-review-setup'),
    path(
        '<int:pk>/deny/',
        StorageRequestReviewDenyView.as_view(),
        name='faculty-storage-allocation-request-deny'),
    path(
        '<int:pk>/undeny/',
        StorageRequestUndenyView.as_view(),
        name='faculty-storage-allocation-request-undeny'),
]
