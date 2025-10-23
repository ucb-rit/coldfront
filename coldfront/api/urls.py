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

# Cluster storage API
# Note: The feature flag generally abstracts away the check for whether the app
# is installed. However, the app module is still resolved, which may be
# problematic if it is not installed, so the check is manually done here.
if 'coldfront.plugins.cluster_storage' in settings.INSTALLED_APPS:
    with flagged_paths('CLUSTER_STORAGE_ENABLED') as path:
        urlpatterns += [
            path('storage/', include('coldfront.plugins.cluster_storage.api.urls')),
        ]
