from django.contrib.auth import get_user_model
from django.db import models

from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords


def faculty_scratch_storage_request_state_schema():
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
        related_name='faculty_scratch_storage_requester')
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
        default=faculty_scratch_storage_request_state_schema)

    history = HistoricalRecords()

    # TODO: Methods

    def __str__(self):
        return (
            f'{self.project.name} - {self.pi.first_name} {self.pi.last_name} - '
            f'{self.requested_amount_gb} GB')

    class Meta:
        verbose_name = 'Faculty Storage Allocation Request'
        verbose_name_plural = 'Faculty Storage Allocation Requests'
