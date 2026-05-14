from django import forms
from django.contrib.auth.models import User

from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.project.models import Project


class AllocationRenewalRequestSearchForm(forms.Form):
    project = forms.ModelChoiceField(
        queryset=Project.objects.filter(
            pk__in=AllocationRenewalRequest.objects.values('post_project')
        ).order_by('name'),
        label='Project',
        required=False,
    )
    pi = forms.ModelChoiceField(
        queryset=User.objects.filter(
            pk__in=AllocationRenewalRequest.objects.values('pi')
        ).order_by('username'),
        label='PI',
        required=False,
    )
    allocation_period = forms.ModelChoiceField(
        queryset=AllocationPeriod.objects.order_by('start_date'),
        label='Allocation Period',
        required=False,
    )
