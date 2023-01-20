import django_filters

from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectUserRemovalRequestStatusChoice
from coldfront.core.project.models import ProjectUserRemovalRequest
from coldfront.core.project.models import SavioProjectAllocationRequest


class NewProjectRequestFilter(django_filters.FilterSet):
    """A FilterSet for the SavioProjectAllocationRequest model."""

    status = django_filters.filters.ModelMultipleChoiceFilter(
        field_name='status__name', to_field_name='name',
        queryset=ProjectAllocationRequestStatusChoice.objects.all())

    class Meta:
        model = SavioProjectAllocationRequest
        fields = ('status',)


class ProjectUserRemovalRequestFilter(django_filters.FilterSet):
    """A FilterSet for the ProjectUserRemovalRequest model."""

    status = django_filters.filters.ModelMultipleChoiceFilter(
        field_name='status__name', to_field_name='name',
        queryset=ProjectUserRemovalRequestStatusChoice.objects.all())

    class Meta:
        model = ProjectUserRemovalRequest
        fields = ('status',)
