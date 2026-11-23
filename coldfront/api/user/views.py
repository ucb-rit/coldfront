from collections import defaultdict
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.contrib.auth.models import User
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins, status, viewsets
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action
from rest_framework.response import Response

from coldfront.api.permissions import (
    IsSuperuserOrHasPerm,
    IsSuperuserOrStaff,
)
from coldfront.api.user.authentication import is_token_expired
from coldfront.api.user.filters import IdentityLinkingRequestFilter
from coldfront.api.user.serializers import (
    IdentityLinkingRequestSerializer,
    UserSerializer,
)
from coldfront.core.project.models import (
    ProjectUser,
    ProjectUserRoleChoice,
    ProjectUserStatusChoice,
)
from coldfront.core.user.models import ExpiringToken, IdentityLinkingRequest

# ProjectUser status names behind each value of the membership and pis
# query parameters of the project_memberships endpoint. A user is still
# a member while a removal is pending.
CURRENT_MEMBER_STATUSES = ["Active", "Pending - Remove"]
PAST_MEMBER_STATUSES = ["Removed"]
MEMBERSHIP_STATUSES = {
    "current": CURRENT_MEMBER_STATUSES,
    "past": PAST_MEMBER_STATUSES,
    "all": CURRENT_MEMBER_STATUSES + PAST_MEMBER_STATUSES,
}
PI_STATUSES = {
    "current": CURRENT_MEMBER_STATUSES,
    "all": CURRENT_MEMBER_STATUSES + PAST_MEMBER_STATUSES,
}


class IdentityLinkingRequestViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """A ViewSet for the IdentityLinkingRequest model."""

    filterset_class = IdentityLinkingRequestFilter
    http_method_names = ["get", "patch"]
    permission_classes = [IsSuperuserOrStaff]
    serializer_class = IdentityLinkingRequestSerializer

    def get_queryset(self):
        return IdentityLinkingRequest.objects.order_by("id")


class ObtainActiveUserExpiringAuthToken(ObtainAuthToken):
    """A view for an active user to retrieve an expiring API token."""

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        username = serializer.initial_data["username"].strip()
        password = serializer.initial_data["password"]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"error": f"User {username} does not exist."})
        if user.check_password(password) and not user.is_active:
            return Response({"error": f"User {user.email} is inactive."})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
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
        return Response({"token": token.key})


class UserViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """A ViewSet for the User model."""

    permission_classes = [
        IsSuperuserOrStaff | IsSuperuserOrHasPerm("user.can_view_user_profiles")
    ]
    serializer_class = UserSerializer

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "username",
                openapi.IN_QUERY,
                description="Filter by username. May be repeated for multiple values.",
                type=openapi.TYPE_STRING,
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = User.objects.order_by("id")
        usernames = self.request.query_params.getlist("username")
        if usernames:
            queryset = queryset.filter(username__in=usernames)
        return queryset

    @swagger_auto_schema(
        methods=["post"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["users"],
            properties={
                "users": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING),
                    description="List of usernames to look up.",
                )
            },
        ),
        manual_parameters=[
            openapi.Parameter(
                "membership",
                openapi.IN_QUERY,
                description=(
                    "Which memberships to return: current (Active or "
                    "Pending - Remove), past (Removed), or all (both). "
                    "Default: current. Cannot be combined with status."
                ),
                type=openapi.TYPE_STRING,
                enum=["current", "past", "all"],
            ),
            openapi.Parameter(
                "status",
                openapi.IN_QUERY,
                description=(
                    "Filter memberships by ProjectUser status name. May be "
                    "repeated for multiple values. Prefer membership."
                ),
                type=openapi.TYPE_STRING,
                enum=[
                    "Active",
                    "Denied",
                    "Pending - Add",
                    "Pending - Remove",
                    "Removed",
                ],
            ),
            openapi.Parameter(
                "expand",
                openapi.IN_QUERY,
                description=(
                    "Use expand=project to expand project PKs into objects "
                    "including name, project_status, role, "
                    "membership_status, and pis."
                ),
                type=openapi.TYPE_STRING,
                enum=["project"],
            ),
            openapi.Parameter(
                "pis",
                openapi.IN_QUERY,
                description=(
                    "Which PIs to include with expand=project: current "
                    "(Active or Pending - Remove) or all (also Removed). "
                    "Default: current."
                ),
                type=openapi.TYPE_STRING,
                enum=["current", "all"],
            ),
        ],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "user": openapi.Schema(type=openapi.TYPE_STRING),
                        "projects": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description=(
                                "List of project PKs (default), or project "
                                "objects with id, name, project_status, "
                                "role, membership_status, and pis (each "
                                "with username, name, email, and status) "
                                "when ?expand=project is used."
                            ),
                            items=openapi.Schema(type=openapi.TYPE_INTEGER),
                        ),
                    },
                ),
            ),
        },
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="project_memberships",
        permission_classes=[
            IsSuperuserOrHasPerm("project.can_view_project_memberships")
        ],
    )
    def project_memberships(self, request):
        """Return project memberships for a batch of users.

        POST body: {"users": ["alice", "bob"]}
        Query params:
          ?membership=current|past|all (default: current)
          ?status=Active (repeatable; alternative to membership)
          ?expand=project (expand PKs to objects with statuses and pis)
          ?pis=current|all (default: current; used with expand=project)
        """
        membership = request.query_params.get("membership")
        requested_statuses = request.query_params.getlist("status")
        pis = request.query_params.get("pis", "current")
        if membership is not None and requested_statuses:
            return Response(
                {"membership": "Cannot be combined with status."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if membership is not None and membership not in MEMBERSHIP_STATUSES:
            return Response(
                {"membership": f"Expected one of {list(MEMBERSHIP_STATUSES)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if pis not in PI_STATUSES:
            return Response(
                {"pis": f"Expected one of {list(PI_STATUSES)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if requested_statuses:
            valid_statuses = set(
                ProjectUserStatusChoice.objects.values_list("name", flat=True)
            )
            invalid = [s for s in requested_statuses if s not in valid_statuses]
            if invalid:
                return Response(
                    {"unknown_statuses": invalid},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            statuses = requested_statuses
        else:
            statuses = MEMBERSHIP_STATUSES[membership or "current"]
        pi_statuses = PI_STATUSES[pis]
        expand_project = "project" in request.query_params.getlist("expand")

        raw_users = request.data.get("users", [])
        if not isinstance(raw_users, list) or not all(
            isinstance(u, str) for u in raw_users
        ):
            return Response(
                {"users": "Expected a list of usernames."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Strip whitespace and deduplicate, preserving input order.
        usernames = list(dict.fromkeys(u.strip() for u in raw_users))

        users = User.objects.filter(username__in=usernames)
        found = set(users.values_list("username", flat=True))
        unknown = [u for u in usernames if u not in found]
        if unknown:
            return Response(
                {"unknown_users": unknown}, status=status.HTTP_400_BAD_REQUEST
            )

        memberships = (
            ProjectUser.objects.filter(user__in=users, status__name__in=statuses)
            .select_related("user", "project__status", "role", "status")
            .order_by("user__username", "project_id")
        )

        by_user = defaultdict(list)
        for pu in memberships:
            by_user[pu.user.username].append(pu)

        pis_by_project = {}
        if expand_project:
            project_ids = {pu.project_id for pus in by_user.values() for pu in pus}
            if project_ids:
                pi_role = ProjectUserRoleChoice.objects.get(
                    name="Principal Investigator"
                )
                pi_qs = (
                    ProjectUser.objects.filter(
                        project_id__in=project_ids,
                        role=pi_role,
                        status__name__in=pi_statuses,
                    )
                    .select_related("user", "status")
                    .order_by("user__username")
                )
                pis_by_project = defaultdict(list)
                for pi_pu in pi_qs:
                    pis_by_project[pi_pu.project_id].append(
                        {
                            "username": pi_pu.user.username,
                            "name": pi_pu.user.get_full_name(),
                            "email": pi_pu.user.email,
                            "status": pi_pu.status.name,
                        }
                    )

        results = []
        for username in usernames:
            user_memberships = by_user.get(username, [])
            if expand_project:
                projects = [
                    {
                        "id": pu.project_id,
                        "name": pu.project.name,
                        "project_status": pu.project.status.name,
                        "role": pu.role.name,
                        "membership_status": pu.status.name,
                        "pis": pis_by_project.get(pu.project_id, []),
                    }
                    for pu in user_memberships
                ]
            else:
                projects = [pu.project_id for pu in user_memberships]
            results.append({"user": username, "projects": projects})

        return Response(results)
