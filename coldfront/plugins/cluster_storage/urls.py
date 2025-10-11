from django.urls import path

from .views import StorageRequestDetailView


urlpatterns = [
    path(
        '<int:pk>/',
        StorageRequestDetailView.as_view(),
        name='storage-request-detail'),
]
