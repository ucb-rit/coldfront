from django import forms

from coldfront.plugins.ucb_departments.models import Department
from coldfront.plugins.ucb_departments.models import UserDepartment


class NonAuthoritativeDepartmentSelectionForm(forms.Form):
    """A form that allows the user to select the departments that they
    are non-authoritatively associated with."""

    departments = forms.ModelMultipleChoiceField(
        label='Departments',
        queryset=Department.objects.order_by('name').all(),
        required=True)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        if user is None:
            raise ValueError('No user provided.')
        self.user_profile = user.userprofile

        super().__init__(*args, **kwargs)

        self._disable_department_choices()
        self._set_initial_departments()

    def _disable_department_choices(self):
        """Prevent certain Departments, which should be displayed, from
        being selected."""
        disable_department_pks = set()

        # Disable any Department that the User is authoritatively associated
        # with.
        authoritative_user_departments = UserDepartment.objects.filter(
            userprofile=self.user_profile,
            is_authoritative=True)
        authoritative_department_pks = set(
            authoritative_user_departments.values_list(
                'department__pk', flat=True))
        disable_department_pks.update(authoritative_department_pks)

        self.fields['departments'].widget.disabled_choices = \
            disable_department_pks

    def _set_initial_departments(self):
        """Pre-select the Departments that the user is non-
        authoritatively associated with."""
        non_authoritative_user_departments = UserDepartment.objects.filter(
            userprofile=self.user_profile,
            is_authoritative=False)
        non_authoritative_department_pks = list(
            non_authoritative_user_departments.values_list(
                'department__pk', flat=True))
        self.fields['departments'].initial = Department.objects.filter(
            pk__in=non_authoritative_department_pks)
