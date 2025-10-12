from django.urls import path

from .views import StorageRequestDetailView
from .views import StorageRequestListView
from .views import StorageRequestReviewEligibilityView
from .views import StorageRequestReviewIntakeConsistencyView
from .views import StorageRequestReviewSetupView


urlpatterns = [
    path(
        '',
        StorageRequestListView.as_view(),
        name='storage-request-list'),
    path(
        '<int:pk>/',
        StorageRequestDetailView.as_view(),
        name='storage-request-detail'),
    path(
        '<int:pk>/eligibility/',
        StorageRequestReviewEligibilityView.as_view(),
        name='storage-request-review-eligibility'),
    path(
        '<int:pk>/intake-consistency/',
        StorageRequestReviewIntakeConsistencyView.as_view(),
        name='storage-request-review-intake-consistency'),
    path(
        '<int:pk>/setup/',
        StorageRequestReviewSetupView.as_view(),
        name='storage-request-review-setup'),
]
