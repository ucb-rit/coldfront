import django_filters.filters

from django.db.models import Q

from coldfront.core.project.models import Project, ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRemovalRequestStatusChoice
from coldfront.core.project.models import ProjectUserRemovalRequest
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface


class ProjectFilter(django_filters.FilterSet):
    """A FilterSet for the Project model."""

    status = django_filters.filters.ModelMultipleChoiceFilter(
        field_name='status__name', to_field_name='name',
        queryset=ProjectStatusChoice.objects.all())
    allowance_type = django_filters.filters.MultipleChoiceFilter(
        method='filter_by_allowance_type')

    class Meta:
        model = Project
        fields = ('status', 'name', 'allowance_type')

    def __init__(self, *args, **kwargs):
        """Initialize the filter and dynamically set allowance_type
        choices."""
        super().__init__(*args, **kwargs)
        self.filters['allowance_type'].extra['choices'] = (
            self._get_allowance_type_choices())

    def _get_allowance_type_choices(self):
        """Get allowance type choices."""
        interface = ComputingAllowanceInterface()
        allowances = interface.allowances()
        type_choices = []
        for allowance in allowances:
            try:
                code = interface._object_to_code.get(allowance)
                if code:
                    type_choices.append((code, code))
            except (KeyError, AttributeError):
                pass
        return type_choices

    def filter_by_allowance_type(self, queryset, name, value):
        """Filter projects by allowance type prefix(es)."""
        if not value:
            return queryset
        q_objects = Q()
        for code in value:
            q_objects |= Q(name__startswith=code)
        return queryset.filter(q_objects)


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
