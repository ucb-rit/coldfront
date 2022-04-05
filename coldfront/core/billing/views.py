from coldfront.core.allocation.models import Allocation
from coldfront.core.billing.forms import BillingIDValidationForm
from coldfront.core.billing.models import BillingActivity

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic.edit import FormView

import logging

# TODO: Replace this module with a directory as needed.


logger = logging.getLogger(__name__)


class UpdateAllocationBillingIDView(LoginRequiredMixin, UserPassesTestMixin,
                                    FormView):

    form_class = BillingIDValidationForm
    template_name = 'billing/update_allocation_billing_id.html'
    login_url = '/'

    error_message = 'Unexpected failure. Please contact an administrator.'

    update_view_name = 'allocation-update-billing-id'

    allocation_attribute_obj = None
    allocation_obj = None
    current_billing_id = '000000-000'

    def dispatch(self, request, *args, **kwargs):
        """TODO"""
        pk = self.kwargs.get('pk')
        self.allocation_obj = get_object_or_404(
            Allocation.objects.prefetch_related('allocationattribute_set'),
            pk=pk)

        update_view_redirect = HttpResponseRedirect(
            reverse(self.update_view_name, kwargs={'pk': pk}))

        billing_activity_attributes = \
            self.allocation_obj.allocationattribute_set.filter(
                allocation_attribute_type__name='Billing Activity')
        num_billing_activity_attributes = billing_activity_attributes.count()
        if num_billing_activity_attributes == 0:
            pass
        elif num_billing_activity_attributes == 1:
            attribute = billing_activity_attributes.first()
            billing_activity_pk = int(attribute.value)
            try:
                billing_activity = BillingActivity.objects.get(
                    pk=billing_activity_pk)
            except BillingActivity.DoesNotExist:
                log_message = (
                    f'AllocationAttribute {attribute.pk} stores a '
                    f'BillingActivity primary key {billing_activity_pk} that '
                    f'does not exist.')
                logger.error(log_message)
                messages.error(request, self.error_message)
                return update_view_redirect
            self.allocation_attribute_obj = attribute
            self.current_billing_id = billing_activity.full_id()
        else:
            log_message = (
                f'Unexpectedly found multiple AllocationAttributes with '
                f'unique type "Billing Activity" for Allocation '
                f'{self.allocation_obj.pk}.')
            logger.error(log_message)
            messages.error(request, self.error_message)
            return update_view_redirect
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """TODO"""
        form_data = form.cleaned_data
        billing_id = form_data['billing_id']
        project_identifier, activity_identifier = billing_id.split('-')
        billing_activity = BillingActivity.objects.get(
            billing_project__identifier=project_identifier,
            identifier=activity_identifier,
            is_valid=True)
        self.allocation_attribute_obj.refresh_from_db()
        self.allocation_attribute_obj.value = billing_activity.pk
        self.allocation_attribute_obj.save()

        if self.current_billing_id != '000000-000':
            message = (
                f'Updated Project ID from {self.current_billing_id} to '
                f'{billing_id}.')
        else:
            message = f'Set Project ID to {billing_id}.'
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """TODO"""
        context = super().get_context_data(**kwargs)
        context['allocation'] = self.allocation_obj
        choices = []
        if self.current_billing_id != '000000-000':
            choices.append(self.current_billing_id)
        user_billing_activity_attribute_pks = set(
            self.allocation_obj.allocationuserattribute_set.filter(
                allocation_attribute_type__name='Billing Activity'
            ).values_list('pk', flat=True))
        user_billing_activities = BillingActivity.objects.filter(
            pk__in=user_billing_activity_attribute_pks)
        for user_billing_activity in user_billing_activities:
            choices.append(user_billing_activity.full_id())
        context['choices'] = choices
        return context

    def get_initial(self):
        """TODO"""
        initial = super().get_initial()
        initial['billing_id'] = self.current_billing_id
        return initial

    def get_success_url(self):
        """TODO"""
        return reverse(
            'allocation-detail', kwargs={'pk': self.allocation_obj.pk})

    def test_func(self):
        # TODO
        return True
