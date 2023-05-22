from django import forms
from coldfront.core.department.models import Department
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
        user = kwargs.pop('user', None)
        userprofile = user.userprofile
        super().__init__(*args, **kwargs)

        fetch_and_set_user_departments(user, userprofile)
        self.fields['departments'].initial = Department.objects.filter(
            userprofile=userprofile)
