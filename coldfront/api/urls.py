from django.conf import settings
from django.urls import include
from django.urls import re_path

from flags.urls import flagged_paths


urlpatterns = [
    re_path(r'^', include('coldfront.api.allocation.urls')),
    re_path(r'^', include('coldfront.api.billing.urls')),
    re_path(r'^', include('coldfront.api.statistics.urls')),
    re_path(r'^', include('coldfront.api.project.urls')),
    re_path(r'^', include('coldfront.api.user.urls')),
    re_path(r'^', include('coldfront.api.utils.urls')),
]

# Faculty Storage Allocations API
# Note: The feature flag generally abstracts away the check for whether the app
# is installed. However, the app module is still resolved, which may be
# problematic if it is not installed, so the check is manually done here.
if 'coldfront.plugins.faculty_storage_allocations' in settings.INSTALLED_APPS:
    with flagged_paths('FACULTY_STORAGE_ALLOCATIONS_ENABLED') as path:
        urlpatterns += [
            path('faculty_storage_allocations/', include('coldfront.plugins.faculty_storage_allocations.api.urls')),
        ]
