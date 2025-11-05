from django.urls import path

from .views import FSARequestDetailView
from .views import FSARequestEditView
from .views import FSARequestListView
from .views import FSARequestReviewDenyView
from .views import FSARequestReviewEligibilityView
from .views import FSARequestReviewIntakeConsistencyView
from .views import FSARequestReviewSetupView
from .views import FSARequestUndenyView


urlpatterns = [
    path(
        '',
        FSARequestListView.as_view(),
        name='faculty-storage-allocation-request-list'),
    path(
        '<int:pk>/',
        FSARequestDetailView.as_view(),
        name='faculty-storage-allocation-request-detail'),
    path(
        '<int:pk>/edit/',
        FSARequestEditView.as_view(),
        name='faculty-storage-allocation-request-edit'),
    path(
        '<int:pk>/eligibility/',
        FSARequestReviewEligibilityView.as_view(),
        name='faculty-storage-allocation-request-review-eligibility'),
    path(
        '<int:pk>/intake-consistency/',
        FSARequestReviewIntakeConsistencyView.as_view(),
        name='faculty-storage-allocation-request-review-intake-consistency'),
    path(
        '<int:pk>/setup/',
        FSARequestReviewSetupView.as_view(),
        name='faculty-storage-allocation-request-review-setup'),
    path(
        '<int:pk>/deny/',
        FSARequestReviewDenyView.as_view(),
        name='faculty-storage-allocation-request-deny'),
    path(
        '<int:pk>/undeny/',
        FSARequestUndenyView.as_view(),
        name='faculty-storage-allocation-request-undeny'),
]
