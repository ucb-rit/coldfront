from django import forms
from django.core.validators import MinLengthValidator


class AccountDeactivationRequestSearchForm(forms.Form):
    STATUS_CHOICES = (
        ('', '-----'),
        ('Queued', 'Queued'),
        ('Ready', 'Ready'),
        ('Processing', 'Processing'),
        ('Complete', 'Complete'),
        ('Cancelled', 'Cancelled')
    )

    REASON_CHOICES = (
        ('', '-----',),
        ('NO_VALID_USER_ACCOUNT_FEE_BILLING_ID',
         'User does not have a valid PID for the user account fee.'),
        ('NO_VALID_RECHARGE_USAGE_FEE_BILLING_ID',
         'User on a Recharge project does not have '
         'a valid PID for the recharge usage fee.'),
    )

    username = forms.CharField(
        label='Username', max_length=100, required=False)
    first_name = forms.CharField(
        label='First Name', max_length=100, required=False)
    last_name = forms.CharField(
        label='Last Name', max_length=100, required=False)

    status = forms.ChoiceField(label='Status',
                               choices=STATUS_CHOICES,
                               widget=forms.Select(),
                               required=False)

    reason = forms.ChoiceField(label='Reason',
                               choices=REASON_CHOICES,
                               widget=forms.Select(),
                               required=False)


class AccountDeactivationCancelForm(forms.Form):

    justification = forms.CharField(
        help_text=(
            'Provide reasoning for your decision.'),
        label='Justification',
        validators=[MinLengthValidator(10)],
        required=True,
        widget=forms.Textarea(attrs={'rows': 3}))
