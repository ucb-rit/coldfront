from coldfront.core.project.models import Project
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface

from django import forms
from django.core.validators import MinLengthValidator
from django.core.validators import RegexValidator


# =============================================================================
# BRC: SAVIO
# =============================================================================


class SavioProjectReviewSetupForm(forms.Form):

    status = forms.ChoiceField(
        choices=(
            ('', 'Select one.'),
            ('Pending', 'Pending'),
            ('Complete', 'Complete'),
        ),
        help_text='If you are unsure, leave the status as "Pending".',
        label='Status',
        required=True)
    justification = forms.CharField(
        help_text=(
            'Provide reasoning for your decision. This field is only required '
            'when the name changes.'),
        label='Justification',
        validators=[MinLengthValidator(10)],
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, **kwargs):
        self.project_pk = kwargs.pop('project_pk')
        self.requested_name = kwargs.pop('requested_name')
        self.computing_allowance = kwargs.pop('computing_allowance')
        # get the pooling variable
        self.pooling = kwargs.pop('pooling')
        super().__init__(*args, **kwargs)
        pool_max = 1000
        # switch if pooling, otherweise max_length still 13
        max_length_value = pool_max if self.pooling else (3+12)
        self.fields['final_name'] = forms.CharField(
            help_text='Update the name of the project, in case it needed to be '
            'changed. It must begin with the correct prefix.',
        label='Final Name',
        max_length=max_length_value,
        required=True,
        validators=[
            MinLengthValidator(3 + 4),
            RegexValidator(
                r'^[0-9a-z_]+$',
                message=(
                    'Name must contain only lowercase letters, numbers, and '
                    'underscores.'))
        ],
        # Fix the widget in the form to make it dynamic length limit
        widget = forms.TextInput(attrs={'maxlength': str(max_length_value)}),
        )
        self.fields['final_name'].initial = self.requested_name


    def clean(self):
        cleaned_data = super().clean()
        final_name = cleaned_data.get('final_name', '').lower()
        # Require justification for name changes.
        if final_name != self.requested_name:
            justification = cleaned_data.get('justification', '')
            if not justification.strip():
                raise forms.ValidationError(
                    'Please provide a justification for the name change.')
        return cleaned_data

    def clean_final_name(self):
        cleaned_data = super().clean()
        final_name = cleaned_data.get('final_name', '').lower()
        expected_prefix = ComputingAllowanceInterface().code_from_name(
            self.computing_allowance.name)
        if not final_name.startswith(expected_prefix):
            raise forms.ValidationError(
                f'Final project name must begin with "{expected_prefix}".')
        matching_projects = Project.objects.exclude(
            pk=self.project_pk).filter(name=final_name)
        if matching_projects.exists():
            raise forms.ValidationError(
                f'A project with name {final_name} already exists.')
        return final_name


# =============================================================================
# BRC: VECTOR
# =============================================================================

class VectorProjectReviewSetupForm(forms.Form):

    status = forms.ChoiceField(
        choices=(
            ('', 'Select one.'),
            ('Pending', 'Pending'),
            ('Complete', 'Complete'),
        ),
        help_text='If you are unsure, leave the status as "Pending".',
        label='Status',
        required=True)
    final_name = forms.CharField(
        help_text=(
            'Update the name of the project, in case it needed to be '
            'changed. It must begin with the correct prefix.'),
        label='Final Name',
        max_length=len('vector_') + 12,
        required=True,
        validators=[
            MinLengthValidator(len('vector_') + 4),
            RegexValidator(
                r'^[0-9a-z_]+$',
                message=(
                    'Name must contain only lowercase letters, numbers, and '
                    'underscores.'))
        ])
    justification = forms.CharField(
        help_text=(
            'Provide reasoning for your decision. This field is only required '
            'when the name changes.'),
        label='Justification',
        validators=[MinLengthValidator(10)],
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, **kwargs):
        self.project_pk = kwargs.pop('project_pk')
        self.requested_name = kwargs.pop('requested_name')
        super().__init__(*args, **kwargs)
        self.fields['final_name'].initial = self.requested_name

    def clean(self):
        cleaned_data = super().clean()
        final_name = cleaned_data.get('final_name', '').lower()
        # Require justification for name changes.
        if final_name != self.requested_name:
            justification = cleaned_data.get('justification', '')
            if not justification.strip():
                raise forms.ValidationError(
                    'Please provide a justification for the name change.')
        return cleaned_data

    def clean_final_name(self):
        cleaned_data = super().clean()
        final_name = cleaned_data.get('final_name', '').lower()
        expected_prefix = 'vector_'
        if not final_name.startswith(expected_prefix):
            raise forms.ValidationError(
                f'Final project name must begin with "{expected_prefix}".')
        matching_projects = Project.objects.exclude(
            pk=self.project_pk).filter(name=final_name)
        if matching_projects.exists():
            raise forms.ValidationError(
                f'A project with name {final_name} already exists.')
        return final_name
