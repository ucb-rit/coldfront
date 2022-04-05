from coldfront.core.billing.models import BillingActivity

from django import forms
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
                regex=r'^\d{6}-\d{3}$',
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
