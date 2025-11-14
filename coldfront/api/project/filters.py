import django_filters.filters

from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRemovalRequestStatusChoice
from coldfront.core.project.models import ProjectUserRemovalRequest
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice


class ProjectUserFilter(django_filters.FilterSet):
    """A FilterSet for the ProjectUser model."""

    status = django_filters.filters.ModelMultipleChoiceFilter(
        field_name='status__name', to_field_name='name',
        queryset=ProjectUserStatusChoice.objects.all())
    role = django_filters.filters.ModelMultipleChoiceFilter(
        field_name='role__name', to_field_name='name',
        queryset=ProjectUserRoleChoice.objects.all())

    class Meta:
        model = ProjectUser
        fields = ('status', 'role')


class ProjectUserRemovalRequestFilter(django_filters.FilterSet):
    """A FilterSet for the ProjectUserRemovalRequest model."""

    status = django_filters.filters.ModelMultipleChoiceFilter(
        field_name='status__name', to_field_name='name',
        queryset=ProjectUserRemovalRequestStatusChoice.objects.all())

    class Meta:
        model = ProjectUserRemovalRequest
        fields = ('status',)
