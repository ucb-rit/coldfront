from django import forms
from django.core.validators import MinLengthValidator

from coldfront.core.allocation.models import \
    ClusterAccountDeactivationRequestReasonChoice, \
    ClusterAccountDeactivationRequestStatusChoice


class AccountDeactivationRequestSearchForm(forms.Form):
    username = forms.CharField(
        label='Username', max_length=100, required=False)
    first_name = forms.CharField(
        label='First Name', max_length=100, required=False)
    last_name = forms.CharField(
        label='Last Name', max_length=100, required=False)

    status = forms.ChoiceField(label='Status',
                               choices=(),
                               widget=forms.Select(),
                               required=True)

    reason = forms.ChoiceField(label='Reason',
                               choices=(),
                               widget=forms.Select(),
                               required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        reason_choices = [('', '-----',)] + \
                         [(reason.name, reason.description)
                          for reason in
                          ClusterAccountDeactivationRequestReasonChoice.objects.all()]

        status_choices = [('', '-----')] + \
                         [(status.name, status.name) for status in
                          ClusterAccountDeactivationRequestStatusChoice.objects.all()]

        self.fields['reason'].choices = reason_choices
        self.fields['status'].choices = status_choices


class AccountDeactivationCancelForm(forms.Form):

    justification = forms.CharField(
        help_text=(
            'Provide reasoning for your decision.'),
        label='Justification',
        validators=[MinLengthValidator(10)],
        required=True,
        widget=forms.Textarea(attrs={'rows': 3}))
