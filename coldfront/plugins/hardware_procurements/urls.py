from django.urls import path

from .views import HardwareProcurementDetailView
from .views import HardwareProcurementListView


urlpatterns = [
    path(
        '',
        HardwareProcurementListView.as_view(),
        name='hardware-procurement-list'),
    path(
        '<str:procurement_id>/',
        HardwareProcurementDetailView.as_view(),
        name='hardware-procurement-detail'),
]
