from django.urls import path

from .views import (
    FSARequestDetailView,
    FSARequestEditView,
    FSARequestListView,
    FSARequestReviewDenyView,
    FSARequestReviewEligibilityView,
    FSARequestReviewIntakeConsistencyView,
    FSARequestReviewSetupView,
    FSARequestUndenyView,
)

urlpatterns = [
    path(
        "", FSARequestListView.as_view(), name="faculty-storage-allocation-request-list"
    ),
    path(
        "<int:pk>/",
        FSARequestDetailView.as_view(),
        name="faculty-storage-allocation-request-detail",
    ),
    path(
        "<int:pk>/edit/",
        FSARequestEditView.as_view(),
        name="faculty-storage-allocation-request-edit",
    ),
    path(
        "<int:pk>/eligibility/",
        FSARequestReviewEligibilityView.as_view(),
        name="faculty-storage-allocation-request-review-eligibility",
    ),
    path(
        "<int:pk>/intake-consistency/",
        FSARequestReviewIntakeConsistencyView.as_view(),
        name="faculty-storage-allocation-request-review-intake-consistency",
    ),
    path(
        "<int:pk>/setup/",
        FSARequestReviewSetupView.as_view(),
        name="faculty-storage-allocation-request-review-setup",
    ),
    path(
        "<int:pk>/deny/",
        FSARequestReviewDenyView.as_view(),
        name="faculty-storage-allocation-request-deny",
    ),
    path(
        "<int:pk>/undeny/",
        FSARequestUndenyView.as_view(),
        name="faculty-storage-allocation-request-undeny",
    ),
]
