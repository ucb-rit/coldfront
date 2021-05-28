from coldfront.api.user.authentication import is_token_expired
from coldfront.core.user.models import ExpiringToken
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response


class ObtainActiveUserExpiringAuthToken(ObtainAuthToken):
    """A view for an active user to retrieve an expiring API token."""

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        username = serializer.initial_data['username'].strip()
        password = serializer.initial_data['password']
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({'error': f'User {username} does not exist.'})
        if user.check_password(password) and not user.is_active:
            return Response({'error': f'User {user.email} is inactive.'})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = ExpiringToken.objects.get_or_create(user=user)
        expiration_hours = settings.TOKEN_EXPIRATION_HOURS
        if created:
            now = datetime.now(timezone.utc)
            token.expiration = now + timedelta(hours=expiration_hours)
            token.save()
        elif is_token_expired(token):
            token.delete()
            token = ExpiringToken.objects.create(user=user)
            now = datetime.now(timezone.utc)
            token.created = now
            token.expiration = now + timedelta(hours=expiration_hours)
            token.save()
        return Response({'token': token.key})
