from django.conf import settings
from django.conf.urls import url
from django.urls import include

from flags.urls import flagged_paths


urlpatterns = [
    url(r'^', include('coldfront.api.allocation.urls')),
    url(r'^', include('coldfront.api.billing.urls')),
    url(r'^', include('coldfront.api.statistics.urls')),
    url(r'^', include('coldfront.api.project.urls')),
    url(r'^', include('coldfront.api.user.urls')),
    url(r'^', include('coldfront.api.utils.urls')),
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
