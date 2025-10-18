from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from coldfront.core.project.models import Project

from coldfront.plugins.cluster_storage.forms import StorageRequestForm
from coldfront.plugins.cluster_storage.services import FacultyStorageAllocationRequestService
from coldfront.plugins.cluster_storage.services import StorageRequestEligibilityService


class StorageRequestLandingView(LoginRequiredMixin, TemplateView):
    """A view for the landing page for storage requests."""

    template_name = 'cluster_storage/request/storage_request_landing.html'

    # TODO: UserPassesTestMixin + test_func

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._project_obj = None

    def dispatch(self, request, *args, **kwargs):
        self._project_obj = get_object_or_404(Project, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self._project_obj
        return context


class StorageRequestView(LoginRequiredMixin, FormView):
    """A view for requesting storage under a particular project."""

    form_class = StorageRequestForm
    template_name = 'cluster_storage/request/storage_request_form.html'

    # TODO: UserPassesTestMixin + test_func

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._project_obj = None

    def dispatch(self, request, *args, **kwargs):
        self._project_obj = get_object_or_404(Project, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self._project_obj
        return context

    def form_valid(self, form):
        pi = form.cleaned_data['pi'].user
        storage_amount_tb = int(form.cleaned_data['storage_amount'])
        storage_amount_gb = 1000 * storage_amount_tb

        # Check eligibility before creating request
        is_eligible, reason = \
            StorageRequestEligibilityService.is_eligible_for_request(pi)
        if not is_eligible:
            messages.error(self.request, f'Request cannot be submitted: {reason}')
            return self.form_invalid(form)

        try:
            request_data = {
                'status': 'Under Review',
                'project': self._project_obj,
                'requester': self.request.user,
                'pi': pi,
                'requested_amount_gb': storage_amount_gb,
            }
            FacultyStorageAllocationRequestService.create_request(request_data)

            message = (
                'Thank you for your submission. It will be reviewed and '
                'processed by administrators.')
            messages.success(self.request, message)

            return super().form_valid(form)
        except Exception as e:
            messages.error(
                self.request,
                'Unexpected failure. Please contact an administrator.'
            )
            # Log the actual error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.exception(f'Error creating storage request: {e}')
            return self.form_invalid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project_pk'] = self._project_obj.pk
        return kwargs

    def get_success_url(self):
        return reverse('project-detail', kwargs={'pk': self._project_obj.pk})


__all__ = [
    'StorageRequestLandingView',
    'StorageRequestView',
]
