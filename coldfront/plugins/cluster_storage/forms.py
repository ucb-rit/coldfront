from django import forms
from django.contrib.auth.models import User
from django.db.models import Q

from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface


# TODO: This was intentionally copied instead of imported. Place it in a shared
#  library.
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


class StorageRequestForm(forms.Form):

    pi = PIProjectUserChoiceField(
        help_text=(
            'Select a PI to request storage under. A PI may not be selectable '
            'if they already have storage.'),
        label='Principal Investigator',
        queryset=ProjectUser.objects.none(),
        required=True,
        widget=DisabledChoicesSelectWidget())

    STORAGE_CHOICES = [
        ('1', '1 TB'),
        ('2', '2 TB'),
        ('3', '3 TB'),
        ('4', '4 TB'),
        ('5', '5 TB'),
    ]

    storage_amount = forms.ChoiceField(
        choices=STORAGE_CHOICES,
        required=True,
        label='Requested Storage Amount',
        help_text='Select the amount of storage you need (1–5 TB).')

    confirm_external_intake = forms.BooleanField(
        required=True,
        label='I have filled out the external intake form.',
        help_text=(
            'Your request will be denied if you have not filled out the '
            'external intake form, or the storage amount requested does not '
            'match what was specified there.'))

    def __init__(self, *args, **kwargs):
        self._project_pk = kwargs.pop('project_pk', None)
        super().__init__(*args, **kwargs)

        if not self._project_pk:
            return

        self._project = Project.objects.get(pk=self._project_pk)

        pi_project_users = ProjectUser.objects.prefetch_related('user').filter(
            project=self._project,
            role__name='Principal Investigator',
            status__name='Active')

        self.fields['pi'].queryset = pi_project_users
        self._disable_pi_choices(pi_project_users)

    def _disable_pi_choices(self, pi_project_users):
        """Prevent certain of the given ProjectUsers, who should be
        displayed, from being selected."""
        # TODO: Check for existing storage or a pending request.
        self.fields['pi'].widget.disabled_choices = {}


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
