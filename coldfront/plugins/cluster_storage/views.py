from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from coldfront.core.project.models import Project

from .forms import StorageRequestForm


class StorageRequestLandingView(LoginRequiredMixin, TemplateView):
    """A view for the landing page for storage requests."""

    template_name = 'cluster_storage/storage_request_landing.html'

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
    template_name = 'cluster_storage/storage_request_form.html'

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
        pi = form.cleaned_data['pi']
        storage_amount = form.cleaned_data['storage_amount']
        confirm_external_intake = form.cleaned_data['confirm_external_intake']

        # Example: Log or process the data
        print(f"PI: {pi}, Storage Amount: {storage_amount}, Confirmed Intake: {confirm_external_intake}")

        # TODO: Consider sending a confirmation email.

        message = (
            'Thank you for your submission. It will be reviewed and '
            'processed by administrators.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project_pk'] = self._project_obj.pk
        return kwargs

    def get_success_url(self):
        return reverse('project-detail', kwargs={'pk': self._project_obj.pk})
