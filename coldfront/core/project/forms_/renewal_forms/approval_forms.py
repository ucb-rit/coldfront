from django import forms

class AllocationRenewalRequestForm(forms.Form):
    pi_username = forms.CharField(
        label='PI',
        max_length=100,
        required=False  
    )
    request_time = forms.CharField(
        label='Request Time',
        max_length=100,
        required=False  
    )
    requester = forms.CharField(
        label='Requester',
        max_length=100,
        required=False 
    )
    project = forms.CharField(
        label='Project',
        max_length=100,
        required=False  
    )
    show_all_requests = forms.BooleanField(initial=True, required=False)
