from django.urls import path

from .views import (
    GpuQueueWaitTimesView,
    MonthlyJobCountsView,
    QueueWaitTimesView,
    TopUsageView,
)

app_name = "analytics"

urlpatterns = [
    path("queue-wait-times/", QueueWaitTimesView.as_view(), name="queue-wait-times"),
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
