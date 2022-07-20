from django import forms


class ClusterAccountDeletionSelfRequestForm(forms.Form):
    confirm_checkbox = \
        forms.BooleanField(required=True,
                           label='I wish to delete my cluster account.')
    understand_checkbox = \
        forms.BooleanField(required=True,
                           label='I understand the implications of deleting'
                                 ' my cluster account.')

    password = forms.CharField(widget=forms.PasswordInput(),
                               required=True,
                               help_text='Please enter your password to delete '
                                         'your cluster account.')

    def __init__(self, *args, **kwargs):
        self.user_obj = kwargs.pop('user_obj', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        confirm_checkbox = cleaned_data.get('confirm_checkbox')
        understand_checkbox = cleaned_data.get('understand_checkbox')
        password = cleaned_data.get('password')

        if not confirm_checkbox:
            raise forms.ValidationError(
                'You must confirm you wish to delete your cluster account.')

        if not understand_checkbox:
            raise forms.ValidationError(
                'You must confirm you understand '
                'the implications of deleting your cluster account.')

        if not self.user_obj.check_password(password):
            raise forms.ValidationError(
                'Entered password is incorrect.')
