from collections import namedtuple

from django.contrib.auth import get_user_model
from django.db import models

from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords


def faculty_storage_allocation_request_state_schema():
    """Return the schema for the FacultyStorageAllocationRequest.state
    field."""
    return {
        'eligibility': {
            'status': 'Pending',
            'justification': '',
            'timestamp': '',
        },
        'intake_consistency': {
            'status': 'Pending',
            'justification': '',
            'timestamp': '',
        },
        'setup': {
            'status': 'Pending',
            'directory_name': '',
            'timestamp': '',
        },
        'other': {
            'justification': '',
            'timestamp': '',
        },
    }


class FacultyStorageAllocationRequestStatusChoice(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class FacultyStorageAllocationRequest(TimeStampedModel):

    status = models.ForeignKey(
        FacultyStorageAllocationRequestStatusChoice,
        on_delete=models.PROTECT)

    project = models.ForeignKey(
        'project.Project',
        on_delete=models.CASCADE)

    requester = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name='faculty_scratch_fsa_requester')
    pi = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name='faculty_scratch_storage_pi')

    requested_amount_gb = models.PositiveIntegerField()
    approved_amount_gb = models.PositiveIntegerField(null=True, blank=True)

    request_time = models.DateTimeField(auto_now_add=True)
    approval_time = models.DateTimeField(null=True, blank=True)
    completion_time = models.DateTimeField(null=True, blank=True)

    state = models.JSONField(
        default=faculty_storage_allocation_request_state_schema)

    history = HistoricalRecords()

    # TODO: Methods

    def denial_reason(self):
        """Return the reason why the request was denied, based on its
        'state' field."""
        if self.status.name != 'Denied':
            raise ValueError(
                f'Provided request has unexpected status '
                f'{self.status.name}.')

        state = self.state
        eligibility = state['eligibility']
        intake_consistency = state['intake_consistency']
        other = state['other']

        DenialReason = namedtuple(
            'DenialReason', 'category justification timestamp')

        if other['timestamp']:
            category = 'Other'
            justification = other['justification']
            timestamp = other['timestamp']
        elif eligibility['status'] == 'Denied':
            category = 'Eligibility'
            justification = eligibility['justification']
            timestamp = eligibility['timestamp']
        elif intake_consistency['status'] == 'Denied':
            category = 'Intake Consistency'
            justification = intake_consistency['justification']
            timestamp = intake_consistency['timestamp']
        else:
            raise ValueError(
                'Provided request has an unexpected state.')

        return DenialReason(
            category=category,
            justification=justification,
            timestamp=timestamp
        )

    def latest_update_timestamp(self):
        """Return the latest timestamp stored in the request's 'state'
        field, or the empty string.

        The expected values are ISO 8601 strings, or the empty string,
        so taking the maximum should provide the correct output."""
        state = self.state
        max_timestamp = ''
        for field in state:
            max_timestamp = max(
                max_timestamp, state[field].get('timestamp', ''))
        return max_timestamp

    def __str__(self):
        return (
            f'{self.project.name} - {self.pi.first_name} {self.pi.last_name} - '
            f'{self.requested_amount_gb} GB')

    class Meta:
        verbose_name = 'Faculty Storage Allocation Request'
        verbose_name_plural = 'Faculty Storage Allocation Requests'
        permissions = [
            ('can_view_all_fsa_requests', 'Can view all FSA requests'),
            ('can_manage_fsa_requests', 'Can manage FSA requests'),
        ]
