import logging

from django.db import transaction
from django.http import Http404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import APIException
from rest_framework.generics import get_object_or_404

from coldfront.api.permissions import IsAdminUserOrReadOnly
from coldfront.api.permissions import IsSuperuserOrStaff
from coldfront.api.user.authentication import is_token_expired
from coldfront.api.user.filters import IdentityLinkingRequestFilter, \
    ClusterAccountDeactivationRequestFilter
from coldfront.api.user.serializers import IdentityLinkingRequestSerializer, \
    ClusterAccountDeactivationRequestSerializer
from coldfront.api.user.serializers import UserSerializer
from coldfront.core.allocation.models import \
    ClusterAccountDeactivationRequest, \
    ClusterAccountDeactivationRequestReasonChoice
from coldfront.core.project.models import Project
from coldfront.core.user.models import ExpiringToken
from coldfront.core.user.models import IdentityLinkingRequest
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import mixins, status
from rest_framework import viewsets
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response

from coldfront.core.user.utils import get_compute_resources_for_user
from coldfront.core.utils.common import utc_now_offset_aware, \
    import_from_settings

logger = logging.getLogger(__name__)

authorization_parameter = openapi.Parameter(
    'Authorization',
    openapi.IN_HEADER,
    description=(
        'The authorization token for the requester. The token should be '
        'preceded by "Token " (no quotes).'),
    type=openapi.TYPE_STRING)


class IdentityLinkingRequestViewSet(mixins.ListModelMixin,
                                    mixins.RetrieveModelMixin,
                                    mixins.UpdateModelMixin,
                                    viewsets.GenericViewSet):
    """A ViewSet for the IdentityLinkingRequest model."""

    filterset_class = IdentityLinkingRequestFilter
    http_method_names = ['get', 'patch']
    permission_classes = [IsSuperuserOrStaff]
    serializer_class = IdentityLinkingRequestSerializer

    def get_queryset(self):
        return IdentityLinkingRequest.objects.order_by('id')


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


class UserViewSet(mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  viewsets.GenericViewSet):
    """A ViewSet for the User model."""

    permission_class = [IsAdminUserOrReadOnly]
    serializer_class = UserSerializer

    def get_queryset(self):
        return User.objects.order_by('id')


class AccountDeactivationViewSet(mixins.ListModelMixin,
                                 mixins.RetrieveModelMixin,
                                 mixins.UpdateModelMixin,
                                 mixins.CreateModelMixin,
                                 viewsets.GenericViewSet):
    """A ViewSet for the ClusterAccountDeactivationRequest model."""

    filterset_class = ClusterAccountDeactivationRequestFilter
    http_method_names = ['get', 'patch']
    permission_classes = [IsSuperuserOrStaff]
    serializer_class = ClusterAccountDeactivationRequestSerializer

    def update_data_dict(self, data):
        """Updates the returned data to include the correct reason
        and compute resource strings."""
        request_obj = ClusterAccountDeactivationRequest.objects.get(id=data['id'])
        compute_resources = get_compute_resources_for_user(request_obj.user)
        data['compute_resources'] = \
            ','.join([resource.name for resource in compute_resources])
        data['recharge_project'] = request_obj.state['recharge_project_pk']

    @swagger_auto_schema(
        manual_parameters=[authorization_parameter],
        operation_description=(
                'Retrieves the ClusterAccountDeactivationRequest identified '
                'by the given ID.'))
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data_copy = serializer.data.copy()
        self.update_data_dict(data_copy)

        return Response(data_copy)

    def get_queryset(self):
        return ClusterAccountDeactivationRequest.objects.order_by('id')

    @swagger_auto_schema(
        manual_parameters=[authorization_parameter],
        operation_description=(
                'Lists all ClusterAccountDeactivationRequests identified '
                'by the given reason or status.'))
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        data_copy = {'results': serializer.data.copy(),
                     'next': None,
                     'previous': None}
        for item in data_copy['results']:
            self.update_data_dict(item)

        data_copy.update({'count': len(data_copy['results'])})

        return Response(data_copy)

    @swagger_auto_schema(
        manual_parameters=[authorization_parameter],
        operation_description=(
                'Updates one or more fields of the '
                'ClusterAccountDeactivationRequest identified '
                'by the given ID.'))
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance,
                                         data=request.data,
                                         partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        data_copy = serializer.data.copy()
        self.update_data_dict(data_copy)

        return Response(data_copy)

    def perform_update(self, serializer):
        try:
            with transaction.atomic():
                justification = \
                    serializer.validated_data.pop('justification', '')

                # Popping read only fields.
                serializer.validated_data.pop('reason', None)
                serializer.validated_data.pop('user', None)
                serializer.validated_data.pop('recharge_project', None)

                instance = serializer.save()
                instance.state['cancellation_justification'] = justification
                instance.save()

                if serializer.validated_data.get('status').name == 'Complete':
                    instance.user.userprofile.is_deactivated = True
                    instance.user.userprofile.save()

        except Exception as e:
            message = f'Rolling back failed transaction. Details:\n{e}'
            logger.exception(message)
            raise APIException('Internal server error.')

    @swagger_auto_schema(
        manual_parameters=[authorization_parameter],
        operation_description=(
                'Creates a new ClusterAccountDeactivationRequest with the '
                'given fields.'))
    def create(self, request, *args, **kwargs):
        """The method for POST (create) requests."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data_copy = serializer.validated_data.copy()

        validated_data_copy.pop('justification', None)
        # Must provide a reason to create a new request.
        reason = validated_data_copy.get('reason', None)
        if not reason:
            message = {'error': 'You must provide a valid reason.'}
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        # Throw an exception if the provided recharge project name is invalid.
        recharge_project = validated_data_copy.pop('recharge_project', None)
        if reason.name == 'NO_VALID_RECHARGE_USAGE_FEE_BILLING_ID':
            if not recharge_project:
                message = {'error': f'If the reason is \"NO_VALID_RECHARGE_'
                                    f'USAGE_FEE_BILLING_ID\", you must provide '
                                    f'a recharge project.'}
                return Response(message, status=status.HTTP_400_BAD_REQUEST)

        # Only queued requests can be created.
        if validated_data_copy['status'].name != 'Queued':
            message = {'error': f'POST requests only allow requests to be '
                                f'created with a \"Queued\" status.'}
            return Response(message, status=status.HTTP_400_BAD_REQUEST)

        expiration_days = \
            import_from_settings('ACCOUNT_DEACTIVATION_AUTO_QUEUE_DAYS')
        expiration = utc_now_offset_aware() + timedelta(days=expiration_days)

        exists = False
        query = \
            ClusterAccountDeactivationRequest.objects.filter(**validated_data_copy)
        if query.exists():
            if recharge_project:
                for request in query:
                    if request.state['recharge_project_pk'] == recharge_project.pk:
                        exists = True
                        break
            else:
                exists = True

        if not exists:
            instance = ClusterAccountDeactivationRequest.objects.create(
                **validated_data_copy)

            instance.expiration = expiration
            if reason.name == 'NO_VALID_RECHARGE_USAGE_FEE_BILLING_ID':
                instance.state['recharge_project_pk'] = recharge_project.pk
            instance.save()
        else:
            # Request already exists.
            message = {'error': f'ClusterAccountDeactivationRequest with '
                                f'given args already exists.'}
            return Response(message,
                            status=status.HTTP_400_BAD_REQUEST)

        headers = self.get_success_headers(serializer.data)

        data_copy = serializer.data.copy()
        data_copy.update({'id': instance.id})
        self.update_data_dict(data_copy)

        return Response(data_copy,
                        status=status.HTTP_201_CREATED,
                        headers=headers)
