from django.urls import include
from django.urls import re_path


urlpatterns = [
    re_path(r'^', include('coldfront.api.allocation.urls')),
    re_path(r'^', include('coldfront.api.billing.urls')),
    re_path(r'^', include('coldfront.api.statistics.urls')),
    re_path(r'^', include('coldfront.api.project.urls')),
    re_path(r'^', include('coldfront.api.user.urls')),
    re_path(r'^', include('coldfront.api.utils.urls')),
]
