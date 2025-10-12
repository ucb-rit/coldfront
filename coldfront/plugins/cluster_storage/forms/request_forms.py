from django import forms

from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser

from .form_utils import DisabledChoicesSelectWidget
from .form_utils import PIProjectUserChoiceField


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


__all__ = [
    'StorageRequestForm',
]
