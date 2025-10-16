from django import forms
from django.core.validators import MinLengthValidator


# TODO: These classes were intentionally copied instead of imported. Place them
#  in a shared library.


class DisabledChoicesSelectWidget(forms.Select):

    def __init__(self, *args, **kwargs):
        self.disabled_choices = kwargs.pop('disabled_choices', set())
        super().__init__(*args, **kwargs)

    def create_option(self, name, value, label, selected, index, subindex=None,
                      attrs=None):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex,
            attrs=attrs)
        try:
            if int(str(value)) in self.disabled_choices:
                option['attrs']['disabled'] = True
        except Exception:
            pass
        return option


class PIProjectUserChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):
        user = obj.user
        return f'{user.first_name} {user.last_name} ({user.username})'


class PIUserChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):
        return f'{obj.first_name} {obj.last_name} ({obj.username})'


class ReviewStatusForm(forms.Form):

    status = forms.ChoiceField(
        choices=(
            ('', 'Select one.'),
            ('Pending', 'Pending'),
            ('Approved', 'Approved'),
            ('Denied', 'Denied'),
        ),
        help_text='If you are unsure, leave the status as "Pending".',
        label='Status',
        required=True)
    justification = forms.CharField(
        help_text=(
            'Provide reasoning for your decision. This field is only required '
            'for denials, since it will be included in the notification '
            'email.'),
        label='Justification',
        validators=[MinLengthValidator(10)],
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}))

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status', 'Pending')
        # Require justification for denials.
        if status == 'Denied':
            justification = cleaned_data.get('justification', '')
            if not justification.strip():
                raise forms.ValidationError(
                    'Please provide a justification for your decision.')
        return cleaned_data


class StorageAmountChoiceField(forms.ChoiceField):
    """Reusable form field for selecting storage amounts."""
    STORAGE_CHOICES = [
        (1, '1 TB'),
        (2, '2 TB'),
        (3, '3 TB'),
        (4, '4 TB'),
        (5, '5 TB'),
    ]

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('choices', self.STORAGE_CHOICES)
        kwargs.setdefault('label', 'Requested Storage Amount')
        kwargs.setdefault(
            'help_text', 'Select the amount of storage you need (1 - 5 TB).')
        super().__init__(*args, **kwargs)
