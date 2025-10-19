from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from coldfront.core.project.models import Project
from coldfront.core.project.utils_.permissions_utils import is_user_manager_or_pi_of_project
from coldfront.core.user.utils import access_agreement_signed

from coldfront.plugins.cluster_storage.forms import StorageRequestForm
from coldfront.plugins.cluster_storage.services import FacultyStorageAllocationRequestService
from coldfront.plugins.cluster_storage.services import StorageRequestEligibilityService


class StorageRequestAccessMixin(UserPassesTestMixin):
    """Mixin to check access permissions for storage requests.

    Requires that the view has a `_project_obj` attribute set before
    test_func is called (typically in dispatch).
    """

    def test_func(self):
        """Check if the user has permission to access storage
        requests."""
        user = self.request.user
        if user.is_superuser:
            return True

        # TODO: Allow certain staff in a particular group?

        if not access_agreement_signed(user):
            url = reverse('user-access-agreement')
            message = mark_safe(
                f'You must sign the <a href="{url}">User Access Agreement</a>.'
            )
            messages.error(self.request, message)
            return False

        if not is_user_manager_or_pi_of_project(user, self._project_obj):
            message = (
                'You must be an active Manager or Principal Investigator of '
                'the project.')
            messages.error(self.request, message)
            return False

        return True


class StorageRequestLandingView(LoginRequiredMixin, StorageRequestAccessMixin,
                                TemplateView):
    """A view for the landing page for storage requests."""

    template_name = 'cluster_storage/request/storage_request_landing.html'

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


class StorageRequestView(LoginRequiredMixin, StorageRequestAccessMixin,
                         FormView):
    """A view for requesting storage under a particular project."""

    form_class = StorageRequestForm
    template_name = 'cluster_storage/request/storage_request_form.html'

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
            messages.error(
                self.request, f'Request cannot be submitted: {reason}')
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
