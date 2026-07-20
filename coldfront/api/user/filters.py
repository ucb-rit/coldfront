import django_filters.filters

from coldfront.core.user.models import (
    IdentityLinkingRequest,
    IdentityLinkingRequestStatusChoice,
)


class IdentityLinkingRequestFilter(django_filters.FilterSet):
    """A FilterSet for the IdentityLinkingRequest model."""

    status = django_filters.filters.ModelMultipleChoiceFilter(
        field_name="status__name",
        to_field_name="name",
        queryset=IdentityLinkingRequestStatusChoice.objects.all(),
    )

    class Meta:
        model = IdentityLinkingRequest
        fields = ("status",)
