from django import forms
from django.contrib.auth.models import User
from django.db.models import Q

from coldfront.core.project.models import Project
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface

from .form_utils import PIUserChoiceField
from .form_utils import ReviewStatusForm as StorageRequestReviewStatusForm
from .form_utils import StorageAmountChoiceField


class StorageRequestSearchForm(forms.Form):
    """A form for searching for storage requests based on various
    criteria."""

    # TODO: Read these from the database using ModelChoiceField.
    STATUS_CHOICES = (
        ('', '-----'),
        ('Approved - Complete', 'Approved - Complete'),
        ('Approved - Processing', 'Approved - Processing'),
        ('Denied', 'Denied'),
        ('Under Review', 'Under Review'),
    )

    project = forms.ModelChoiceField(
        label='Project',
        queryset=Project.objects.none(),
        required=False,
        widget=forms.Select())

    pi = PIUserChoiceField(
        label='Principal Investigator',
        queryset=User.objects.all(),
        required=False,
        widget=forms.Select())

    status = forms.ChoiceField(
        label='Status',
        choices=STATUS_CHOICES,
        widget=forms.Select(),
        required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        computing_allowance_interface = ComputingAllowanceInterface()
        prefix = computing_allowance_interface.code_from_name(BRCAllowances.FCA)

        self.fields['project'].queryset = Project.objects.filter(
            name__startswith=prefix)

        self._exclude_pi_choices()

    def _exclude_pi_choices(self):
        """Exclude certain Users from being displayed as PI options."""
        # Exclude any user that does not have an email address.
        exclude_q = (
            Q(email__isnull=True) | Q(email__exact=''))
        self.fields['pi'].queryset = User.objects.exclude(exclude_q)


class StorageRequestEditForm(forms.Form):

    storage_amount = StorageAmountChoiceField(
        required=True,
        label='Updated Storage Amount',
        help_text='Select the updated amount of storage.')


# TODO
class StorageRequestReviewSetupForm(forms.Form):

    status = forms.ChoiceField(
        choices=(
            ('', 'Select one.'),
            ('Pending', 'Pending'),
            ('Complete', 'Complete'),
        ),
        help_text='If you are unsure, leave the status as "Pending".',
        label='Status',
        required=True)
    directory_name = forms.CharField()


__all__ = [
    'StorageRequestEditForm',
    'StorageRequestReviewSetupForm',
    'StorageRequestReviewStatusForm',
    'StorageRequestSearchForm',
]
