from coldfront.api.user.views import IdentityLinkingRequestViewSet
from coldfront.api.user.views import ObtainActiveUserExpiringAuthToken
from coldfront.api.user.views import UserViewSet
from django.urls import re_path
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register(
    r'identity_linking_requests', IdentityLinkingRequestViewSet,
    basename='identity_linking_requests')
router.register(r'users', UserViewSet, basename='users')
urlpatterns = router.urls

urlpatterns.append(
    re_path(
        r'^api_token_auth/', ObtainActiveUserExpiringAuthToken.as_view(),
        name='api_token_auth')
)
