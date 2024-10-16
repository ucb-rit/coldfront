from django import forms
from coldfront.plugins.ucb_departments.models import Department
from coldfront.plugins.ucb_departments.models import UserDepartment
from coldfront.plugins.ucb_departments.utils.queries import fetch_and_set_user_departments

class DepartmentSelectionForm(forms.Form):
    """Form prompting for the departments of a new PI if one is not found
    through LDAP. Has user select one or more from the dozens of departments
    present in Department.objects.all()"""

    departments = forms.ModelMultipleChoiceField(
        label='Departments',
        queryset=Department.objects.order_by('name').all(),
        required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.userprofile = self.user.userprofile
        super().__init__(*args, **kwargs)

        fetch_and_set_user_departments(self.user, self.userprofile)
        self.exclude_department_choices()

        # TODO: Double check logic.
        user_department_pks = list(
            UserDepartment.objects.filter(
                userprofile=self.userprofile).values_list(
                'department__pk', flat=True))
        self.fields['departments'].initial = Department.objects.filter(
            pk__in=user_department_pks)
        # self.fields['departments'].initial = Department.objects.filter(
        #                                         userprofile=self.userprofile)

    def exclude_department_choices(self):
        department_pks = UserDepartment.objects.filter(
                userprofile=self.userprofile,
                is_authoritative=True).values_list('department__pk', flat=True)

        self.fields['departments'].queryset = Department.objects.exclude( \
            pk__in=department_pks)
