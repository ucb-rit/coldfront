from django import forms
from coldfront.core.department.models import Department

class DepartmentSelectionForm(forms.Form):
    '''Form prompting for the departments of a new PI if one is not found
    through LDAP. Has user select one or more from the dozens of departments
    present in Department.objects.all()'''

    departments = forms.ModelMultipleChoiceField(
        label='Departments',
        queryset=Department.objects.order_by('name').all(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.departments = kwargs.pop('departments', None)
        userprofile = kwargs.pop('user', None).userprofile
        super().__init__(*args, **kwargs)

        self.fields['departments'].initial = Department.objects \
            .filter(userprofile=userprofile)