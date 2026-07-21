from django import forms
from django.contrib.auth.models import User

from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.project.models import Project


class AllocationRenewalRequestSearchForm(forms.Form):
    project = forms.ModelChoiceField(
        queryset=Project.objects.none(),
        label="Project",
        required=False,
    )
    pi = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label="PI",
        required=False,
    )
    allocation_period = forms.ModelChoiceField(
        queryset=AllocationPeriod.objects.none(),
        label="Allocation Period",
        required=False,
    )

    def __init__(self, *args, request_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        if request_queryset is not None:
            self.fields["project"].queryset = Project.objects.filter(
                pk__in=request_queryset.values("post_project")
            ).order_by("name")
            self.fields["pi"].queryset = User.objects.filter(
                pk__in=request_queryset.values("pi")
            ).order_by("username")
            self.fields["allocation_period"].queryset = AllocationPeriod.objects.filter(
                pk__in=request_queryset.values("allocation_period")
            ).order_by("start_date")
