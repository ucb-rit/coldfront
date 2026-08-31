from django.urls import path

from .views import (
    CpuQueueWaitTimesView,
    GpuQueueWaitTimesView,
    MonthlyJobCountsView,
    TopUsageView,
)

app_name = "analytics"

urlpatterns = [
    path(
        "cpu-queue-wait-times/",
        CpuQueueWaitTimesView.as_view(),
        name="cpu-queue-wait-times",
    ),
    path(
        "gpu-queue-wait-times/",
        GpuQueueWaitTimesView.as_view(),
        name="gpu-queue-wait-times",
    ),
    path(
        "monthly-job-counts/", MonthlyJobCountsView.as_view(), name="monthly-job-counts"
    ),
    path("top-usage/", TopUsageView.as_view(), name="top-usage"),
]
