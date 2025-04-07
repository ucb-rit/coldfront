from django import forms
from django.contrib.auth.models import User
from django.db.models import Q


class UserChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):
        return f'{obj.first_name} {obj.last_name} ({obj.email})'


class HardwareProcurementSearchForm(forms.Form):
    """A form for searching for hardware procurements based on various
    criteria."""

    HARDWARE_TYPE_CHOICES = (
        ('', '-----'),
        ('CPU', 'CPU'),
        ('GPU', 'GPU'),
        ('Storage', 'Storage'),
    )

    STATUS_CHOICES = (
        ('', '-----'),
        ('complete', 'Complete'),
        ('inactive', 'Inactive'),
        ('pending', 'Pending'),
    )

    pi = UserChoiceField(
        label='Principal Investigator',
        queryset=User.objects.all(),
        required=False)

    hardware_type = forms.ChoiceField(
        label='Hardware Type',
        choices=HARDWARE_TYPE_CHOICES,
        widget=forms.Select(),
        required=False)

    status = forms.ChoiceField(
        label='Status',
        choices=STATUS_CHOICES,
        widget=forms.Select(),
        required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._exclude_pi_choices()

    def _exclude_pi_choices(self):
        """Exclude certain Users from being displayed as PI options."""
        # Exclude any user that does not have an email address or is inactive.
        exclude_q = (
            Q(email__isnull=True) | Q(email__exact='') | Q(is_active=False))
        self.fields['pi'].queryset = User.objects.exclude(exclude_q)
