from django import forms
from coldfront.core.department.models import Department
from coldfront.core.department.models import UserDepartment
from coldfront.core.department.utils.ldap import fetch_and_set_user_departments

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
        self.fields['departments'].initial = Department.objects.filter(
           userprofile=self.userprofile, userdepartment__is_authoritative=False)

    def exclude_department_choices(self):
        # exclude departments with userdepartment associations that are authoritative
        self.fields['departments'].queryset = Department.objects.exclude(
            userprofile=self.userprofile, userdepartment__is_authoritative=True)