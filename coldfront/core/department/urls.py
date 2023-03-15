import coldfront.core.department.views as department_views
from django.urls import path
from flags.urls import flagged_paths

with flagged_paths('USER_DEPARTMENTS_ENABLED') as f_path:
    urlpatterns = [
        f_path('update-departments',
            department_views.UpdateDepartmentsView.as_view(),
            name='update-departments'),
    ]