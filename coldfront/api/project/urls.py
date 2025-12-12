from coldfront.api.project.views import ProjectViewSet, \
    ProjectUserRemovalRequestViewSet, ProjectUserViewSet
from django.urls import include
from django.urls import re_path
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedSimpleRouter

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='projects')
projects_router = NestedSimpleRouter(
    router, r'projects', lookup='project')
projects_router.register(
    r'users', ProjectUserViewSet, basename='users')

router.register(r'project_user_removal_requests',
                ProjectUserRemovalRequestViewSet,
                basename='project_user_removal_requests')

urlpatterns = router.urls

urlpatterns.extend([
    re_path('^', include(projects_router.urls)),
])
