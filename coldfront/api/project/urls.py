from rest_framework.routers import DefaultRouter

from coldfront.api.project.views import NewProjectRequestViewSet
from coldfront.api.project.views import ProjectViewSet
from coldfront.api.project.views import ProjectUserRemovalRequestViewSet


router = DefaultRouter()
router.register(
    r'new_project_requests',
    NewProjectRequestViewSet,
    basename='new_project_requests')
router.register(r'projects', ProjectViewSet, basename='projects')
router.register(
    r'project_user_removal_requests',
    ProjectUserRemovalRequestViewSet,
    basename='project_user_removal_requests')
urlpatterns = router.urls
