from django import forms
from django.core.validators import MinLengthValidator

from coldfront.core.allocation.models import \
    AccountDeletionRequestStatusChoice, \
    AccountDeletionRequestReasonChoice


class AccountDeletionRequestForm(forms.Form):
    confirm_checkbox = \
        forms.BooleanField(required=True)
    understand_checkbox = \
        forms.BooleanField(required=True)

    password = forms.CharField(widget=forms.PasswordInput(),
                               required=True,
                               help_text='Please enter your portal password to '
                                         'delete the cluster account.')

    def __init__(self, *args, **kwargs):
        self.requester = kwargs.pop('requester', None)
        self.user_obj = kwargs.pop('user_obj', None)
        super().__init__(*args, **kwargs)

        user_str = f'{self.user_obj.first_name} ' \
                   f'{self.user_obj.last_name}'
        self.fields['confirm_checkbox'].label = \
            f'I wish to delete {user_str}\'s cluster account.'
        self.fields['understand_checkbox'].label = \
            f'I understand the implications of deleting {user_str}\'s ' \
            f'cluster account.'

    def clean(self):
        cleaned_data = super().clean()
        confirm_checkbox = cleaned_data.get('confirm_checkbox')
        understand_checkbox = cleaned_data.get('understand_checkbox')
        password = cleaned_data.get('password')

        if not confirm_checkbox:
            raise forms.ValidationError(
                'You must confirm you wish to delete this cluster account.')

        if not understand_checkbox:
            raise forms.ValidationError(
                'You must confirm you understand '
                'the implications of deleting this cluster account.')

        if not self.requester.check_password(password):
            raise forms.ValidationError(
                'Entered password is incorrect.')


class AccountDeletionEligibleUsersSearchForm(forms.Form):
    project = forms.CharField(label='Project Name',
                              max_length=100, required=False)
    username = forms.CharField(
        label='Username', max_length=100, required=False)
    first_name = forms.CharField(
        label='First Name', max_length=100, required=False)
    last_name = forms.CharField(
        label='Last Name', max_length=100, required=False)


class AccountDeletionRequestSearchForm(forms.Form):
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
                          AccountDeletionRequestReasonChoice.objects.all()]

        status_choices = [('', '-----')] + \
                         [(status.name, status.name) for status in
                          AccountDeletionRequestStatusChoice.objects.all()]

        self.fields['reason'].choices = reason_choices
        self.fields['status'].choices = status_choices


class AccountDeletionProjectRemovalForm(forms.Form):
    project_name = forms.CharField(max_length=150, required=False,
                                   disabled=True)
    pis = forms.CharField(max_length=200, required=False, disabled=True)
    role = forms.CharField(max_length=150, required=False, disabled=True)
    status = forms.CharField(max_length=30, required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)


class UpdateStatusForm(forms.Form):
    status = forms.ChoiceField(
        choices=(
            ('', 'Select one.'),
            ('Pending', 'Pending'),
            ('Complete', 'Complete')
        ),
        help_text='If you are unsure, leave the status as "Pending".',
        label='Status',
        required=True)


class AccountDeletionUserDataDeletionConfirmation(forms.Form):
    confirm = forms.CharField(max_length=100,
                              required=True,
                              help_text='Type \"CONFIRM\" to confirm that you '
                                        'deleted/moved your data from the '
                                        'cluster.')

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get('confirm') != 'CONFIRM':
            raise forms.ValidationError('You must type \"CONFIRM\" to confirm '
                                        'that it is safe to delete your data '
                                        'from the cluster.')


class AccountDeletionCancelRequestForm(forms.Form):
    justification = forms.CharField(
        help_text='Provide reasoning for your decision.',
        label='Justification',
        validators=[MinLengthValidator(10)],
        required=True,
        widget=forms.Textarea(attrs={'rows': 3}))
