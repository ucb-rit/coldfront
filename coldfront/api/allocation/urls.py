from coldfront.api.allocation.views import AllocationAttributeViewSet, \
    ClusterAccessRequestViewSet
from coldfront.api.allocation.views import AllocationViewSet
from coldfront.api.allocation.views import AllocationUserAttributeViewSet
from coldfront.api.allocation.views import AllocationUserViewSet
from coldfront.api.allocation.views import HistoricalAllocationAttributeViewSet
from coldfront.api.allocation.views import HistoricalAllocationUserAttributeViewSet
from django.urls import include
from django.urls import re_path
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedSimpleRouter


router = DefaultRouter()

router.register(r'allocations', AllocationViewSet, basename='allocations')
allocations_router = NestedSimpleRouter(
    router, r'allocations', lookup='allocation')
allocations_router.register(
    r'attributes', AllocationAttributeViewSet,
    basename='attributes')
allocation_attributes_router = NestedSimpleRouter(
    allocations_router, r'attributes', lookup='attribute')
allocation_attributes_router.register(
    r'history', HistoricalAllocationAttributeViewSet, basename='history')

router.register(
    r'allocation_users', AllocationUserViewSet, basename='allocation_users')
allocation_users_router = NestedSimpleRouter(
    router, r'allocation_users', lookup='allocation_user')
allocation_users_router.register(
    r'attributes', AllocationUserAttributeViewSet, basename='attributes')
allocation_user_attributes_router = NestedSimpleRouter(
    allocation_users_router, r'attributes', lookup='attribute')
allocation_user_attributes_router.register(
    r'history', HistoricalAllocationUserAttributeViewSet, basename='history')

router.register(r'cluster_access_requests',
                ClusterAccessRequestViewSet,
                basename='cluster_access_requests')

urlpatterns = router.urls

urlpatterns.extend([
    re_path('^', include(allocations_router.urls)),
    re_path('^', include(allocation_attributes_router.urls)),
    re_path('^', include(allocation_users_router.urls)),
    re_path('^', include(allocation_user_attributes_router.urls)),
])
