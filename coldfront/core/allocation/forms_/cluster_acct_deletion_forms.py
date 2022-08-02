from django import forms

from coldfront.core.allocation.models import \
    ClusterAcctDeletionRequestStatusChoice, \
    ClusterAcctDeletionRequestRequesterChoice


class ClusterAcctDeletionRequestForm(forms.Form):
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


class ClusterAcctDeletionEligibleUsersSearchForm(forms.Form):
    project = forms.CharField(label='Project Name',
                              max_length=100, required=False)
    username = forms.CharField(
        label='Username', max_length=100, required=False)
    first_name = forms.CharField(
        label='First Name', max_length=100, required=False)
    last_name = forms.CharField(
        label='Last Name', max_length=100, required=False)


class ClusterAcctDeletionRequestSearchForm(forms.Form):
    STATUS_CHOICES = (
        ('', '-----'),
        ('Queued', 'Queued'),
        ('Ready', 'Ready'),
        ('Processing', 'Processing'),
        ('Complete', 'Complete'),
        ('Canceled', 'Canceled')
    )

    REQUESTER_CHOICES = (
        ('', '-----',),
        ('User', 'User'),
        ('PI', 'PI'),
        ('System', 'System')
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

    requester = forms.ChoiceField(label='Requester',
                                  choices=REQUESTER_CHOICES,
                                  widget=forms.Select(),
                                  required=False)
