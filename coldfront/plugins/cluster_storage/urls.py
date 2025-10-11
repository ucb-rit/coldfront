from django.urls import path

from .views import StorageRequestDetailView
from .views import StorageRequestListView


urlpatterns = [
    path(
        '',
        StorageRequestListView.as_view(),
        name='storage-request-list'),
    path(
        '<int:pk>/',
        StorageRequestDetailView.as_view(),
        name='storage-request-detail'),
]
