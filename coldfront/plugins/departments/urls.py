from django.urls import path

from .views import UpdateDepartmentsView


urlpatterns = [
    path(
        'update-departments',
        UpdateDepartmentsView.as_view(),
        name='update-departments'),
]
