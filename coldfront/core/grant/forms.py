from django import forms
from django.forms import ModelForm

from coldfront.core.grant.models import Grant
from coldfront.core.utils.common import import_from_settings

CENTER_NAME = import_from_settings("CENTER_NAME")


class GrantForm(ModelForm):
    class Meta:
        model = Grant
        exclude = [
            "project",
        ]
        labels = {
            "percent_credit": f"Percent credit to {CENTER_NAME}",
            "direct_funding": f"Direct funding to {CENTER_NAME}",
        }
        help_texts = {
            "percent_credit": "Percent credit as entered in the sponsored projects form for grant submission as financial credit to the department/unit in the credit distribution section",
            "direct_funding": f"Funds budgeted specifically for {CENTER_NAME} services, hardware, software, and/or personnel",
        }


class GrantDeleteForm(forms.Form):
    title = forms.CharField(max_length=255, disabled=True)
    grant_number = forms.CharField(max_length=30, required=False, disabled=True)
    grant_end = forms.CharField(max_length=150, required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)
