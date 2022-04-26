from coldfront.core.billing.models import BillingActivity

from django import forms
from django.conf import settings
from django.core.validators import MinLengthValidator
from django.core.validators import RegexValidator


# TODO: Replace this module with a directory as needed.


class BillingIDValidationForm(forms.Form):

    billing_id = forms.CharField(
        label='Project ID',
        max_length=10,
        required=True,
        validators=[
            MinLengthValidator(10),
            RegexValidator(
                regex=settings.LBL_BILLING_ID_REGEX,
                message=(
                    'Project ID must have six digits, then a hyphen, then '
                    'three digits (e.g., 123456-789).')),
        ])

    def clean_billing_id(self):
        billing_id = self.cleaned_data['billing_id']
        project_identifier, activity_identifier = billing_id.split('-')
        if not BillingActivity.objects.filter(
                billing_project__identifier=project_identifier,
                identifier=activity_identifier,
                is_valid=True).exists():
            raise forms.ValidationError(
                f'Project ID {billing_id} is not currently valid.')
        return billing_id


class BillingIDUpdateForm(BillingIDValidationForm):

    selected = forms.BooleanField(initial=False, required=False)

    name = forms.CharField(max_length=300, disabled=True, required=False)
    email = forms.EmailField(max_length=100, disabled=True, required=False)
    username = forms.CharField(max_length=150, disabled=True, required=False)

    current_billing_id = forms.CharField(
        disabled=True,
        label='Current Project ID',
        max_length=10,
        required=False)

    updated_billing_id = forms.CharField(
        label='New Project ID',
        max_length=10,
        required=True,
        validators=[
            MinLengthValidator(10),
            RegexValidator(
                regex=settings.LBL_BILLING_ID_REGEX,
                message=(
                    'Project ID must have six digits, then a hyphen, then '
                    'three digits (e.g., 123456-789).')),
        ])

    def clean_updated_billing_id(self):
        billing_id = self.cleaned_data['updated_billing_id']
        project_identifier, activity_identifier = billing_id.split('-')
        if not BillingActivity.objects.filter(
                billing_project__identifier=project_identifier,
                identifier=activity_identifier,
                is_valid=True).exists():
            raise forms.ValidationError(
                f'Project ID {billing_id} is not currently valid.')
        return billing_id

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['updated_billing_id'].widget.attrs.update(
            {'class': 'form-control'})
