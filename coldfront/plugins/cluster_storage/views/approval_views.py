import iso8601
import logging

from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.paginator import EmptyPage
from django.core.paginator import PageNotAnInteger
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.edit import FormView

from coldfront.core.utils.common import utc_now_offset_aware

from coldfront.plugins.cluster_storage.forms import StorageRequestEditForm
from coldfront.plugins.cluster_storage.forms import StorageRequestReviewDenyForm
from coldfront.plugins.cluster_storage.forms import StorageRequestReviewSetupForm
from coldfront.plugins.cluster_storage.forms import StorageRequestReviewStatusForm
from coldfront.plugins.cluster_storage.forms import StorageRequestSearchForm
from coldfront.plugins.cluster_storage.models import FacultyStorageAllocationRequest
from coldfront.plugins.cluster_storage.models import FacultyStorageAllocationRequestStatusChoice
from coldfront.plugins.cluster_storage.services import FacultyStorageAllocationRequestService

logger = logging.getLogger(__name__)


class StorageRequestReadOnlyAccessMixin(UserPassesTestMixin):
    """Mixin for read-only access to storage request views.

    Allows access to:
    - Superusers
    - Users with 'can_view_all_storage_requests' or
      'can_manage_storage_requests' permission
    - The requester of the storage request
    - The PI of the storage request

    Requires that the view has a `storage_request` attribute set before
    test_func is called (typically in dispatch).
    """

    def test_func(self):
        """Check if user has permission to view storage requests."""
        user = self.request.user

        # Superusers have full access
        if user.is_superuser:
            return True

        # Users with view or manage permissions can access
        if (user.has_perm('cluster_storage.can_view_all_storage_requests') or
            user.has_perm('cluster_storage.can_manage_storage_requests')):
            return True

        # Allow the requester and PI to view their own request
        if hasattr(self, 'storage_request'):
            if (user == self.storage_request.requester or
                user == self.storage_request.pi):
                return True

        message = 'You do not have permission to view this storage request.'
        messages.error(self.request, message)
        return False


class StorageRequestAdminAccessMixin(UserPassesTestMixin):
    """Mixin for admin-only access to storage request management views.

    Allows access to:
    - Superusers
    - Users with 'can_manage_storage_requests' permission
    """

    def test_func(self):
        """Check if user has permission to manage storage requests."""
        user = self.request.user

        # Superusers have full access
        if user.is_superuser:
            return True

        # Users with the specific permission can manage
        if user.has_perm('cluster_storage.can_manage_storage_requests'):
            return True

        message = 'You do not have permission to manage storage requests.'
        messages.error(self.request, message)
        return False


class StorageRequestViewAllAccessMixin(UserPassesTestMixin):
    """Mixin for viewing all storage requests (list view).

    Allows access to:
    - Superusers
    - Users with 'can_view_all_storage_requests' or
      'can_manage_storage_requests' permission

    This is used for the list view where users can see all requests,
    not just their own.
    """

    def test_func(self):
        """Check if user has permission to view all storage requests."""
        user = self.request.user

        # Superusers have full access
        if user.is_superuser:
            return True

        # Users with view or manage permissions can access
        if (user.has_perm('cluster_storage.can_view_all_storage_requests') or
            user.has_perm('cluster_storage.can_manage_storage_requests')):
            return True

        message = 'You do not have permission to view all storage requests.'
        messages.error(self.request, message)
        return False


class StorageRequestAmountMixin:
    """Mixin to add requested and approved amount in TB to context."""

    def add_amount_context(self, context):
        """Add requested_amount_tb and approved_amount_tb to context."""
        if hasattr(self, 'storage_request'):
            context['requested_amount_tb'] = (
                self.storage_request.requested_amount_gb // 1000)
            context['approved_amount_tb'] = (
                self.storage_request.approved_amount_gb // 1000
                if self.storage_request.approved_amount_gb else None
            )
        return context


class StorageRequestViewMixin(StorageRequestAmountMixin):
    """Base mixin for storage request views with common functionality.

    Note: This mixin does NOT include permission checks. Views should
    inherit from either StorageRequestReadOnlyAccessMixin or
    StorageRequestAdminAccessMixin as appropriate.
    """

    def dispatch(self, request, *args, **kwargs):
        """Retrieve and cache the storage request object."""
        pk = self.kwargs.get('pk')
        self.storage_request = get_object_or_404(
            FacultyStorageAllocationRequest, pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add common context variables."""
        context = super().get_context_data(**kwargs)
        context['storage_request'] = self.storage_request
        # Determine if user can manage based on permission
        user = self.request.user
        context['is_allowed_to_manage_request'] = (
            user.is_superuser or
            user.has_perm('cluster_storage.can_manage_storage_requests')
        )
        context = self.add_amount_context(context)
        return context

    def get_success_url(self):
        """Return to the storage request detail page."""
        pk = self.kwargs.get('pk')
        return reverse('storage-request-detail', kwargs={'pk': pk})

    def update_request_status_from_reviews(self):
        """Update the overall request status based on review step statuses.

        - If either review is denied: Call deny_request to update overall status
        - If both eligibility and intake consistency are approved:
          Move to "Approved - Processing" status
        - If either review is pending and request is in an approved state:
          Move back to "Under Review" status

        Returns True if status was changed, False otherwise.
        """
        state = self.storage_request.state
        eligibility_status = state['eligibility']['status']
        intake_status = state['intake_consistency']['status']
        current_status = self.storage_request.status.name

        try:
            # If either review is denied, deny the request
            if eligibility_status == 'Denied' or intake_status == 'Denied':
                FacultyStorageAllocationRequestService.deny_request(
                    self.storage_request
                )
                messages.success(self.request, 'The request has been denied.')
                return True

            # If both reviews are approved, move to Approved - Processing
            elif (eligibility_status == 'Approved' and
                      intake_status == 'Approved'):
                FacultyStorageAllocationRequestService.approve_request(
                    self.storage_request
                )
                messages.success(self.request, 'The request has been approved.')
                return True

            # If either review is pending and we're in an approved state, revert
            elif (eligibility_status == 'Pending' or
                      intake_status == 'Pending'):
                if current_status != 'Under Review':
                    under_review_status = \
                        FacultyStorageAllocationRequestStatusChoice.objects.get(
                            name='Under Review')
                    self.storage_request.status = under_review_status
                    self.storage_request.save()
                    messages.info(self.request, 'The request is under review.')
                    return True

        except Exception as e:
            messages.error(
                self.request,
                'Unexpected failure. Please contact an administrator.'
            )
            logger.exception(
                f'Error updating request status for {self.storage_request.pk}: '
                f'{e}')
            return False

        return False


class StorageRequestDetailView(LoginRequiredMixin,
                               StorageRequestReadOnlyAccessMixin,
                               StorageRequestViewMixin,
                               TemplateView):
    template_name = 'cluster_storage/approval/storage_request_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Only allow editing if user is admin
        user = self.request.user
        context['allow_editing'] = (
            user.is_superuser or
            user.has_perm('cluster_storage.can_manage_storage_requests')
        )

        if self.storage_request.status.name == 'Denied':
            context['denial_reason'] = self.storage_request.denial_reason()

        context['support_email'] = settings.CENTER_HELP_EMAIL

        try:
            latest_update_timestamp = \
                self.storage_request.latest_update_timestamp()
            if not latest_update_timestamp:
                latest_update_timestamp = 'No updates yet.'
            else:
                # TODO: Upgrade to Python 3.7+ to use this.
                # latest_update_timestamp = datetime.datetime.fromisoformat(
                #     latest_update_timestamp)
                latest_update_timestamp = iso8601.parse_date(
                    latest_update_timestamp)
        except Exception as e:
            self.logger.exception(e)
            messages.error(
                self.request,
                'Unexpected failure. Please contact an administrator.'
            )
            latest_update_timestamp = 'Failed to determine timestamp.'
        context['latest_update_timestamp'] = latest_update_timestamp

        context['checklist'] = self._get_checklist()
        context['is_checklist_complete'] = self._is_checklist_complete()
        return context

    def post(self, request, *args, **kwargs):
        """Complete the storage request if all checklist items are approved.

        Only superusers and users with 'can_manage_storage_requests'
        permission can POST.
        """
        user = request.user

        # Check admin permissions for POST
        if not (user.is_superuser or
                user.has_perm('cluster_storage.can_manage_storage_requests')):
            messages.error(
                request,
                'You do not have permission to complete storage requests.'
            )
            return self.get(request, *args, **kwargs)

        storage_request = self.storage_request

        # Validate that all checklist items are approved
        state = storage_request.state
        eligibility_approved = state['eligibility']['status'] == 'Approved'
        intake_approved = state['intake_consistency']['status'] == 'Approved'
        setup_complete = state['setup']['status'] == 'Complete'

        if not eligibility_approved:
            messages.error(
                request,
                'Cannot complete request: Eligibility has not been approved.'
            )
            return self.get(request, *args, **kwargs)

        if not intake_approved:
            messages.error(
                request,
                'Cannot complete request: Intake consistency has not been approved.'
            )
            return self.get(request, *args, **kwargs)

        if not setup_complete:
            messages.error(
                request,
                'Cannot complete request: Setup has not been completed.'
            )
            return self.get(request, *args, **kwargs)

        # Get directory name from state
        directory_name = state['setup'].get('directory_name', '')
        if not directory_name:
            messages.error(
                request,
                'Cannot complete request: Directory name is missing from setup.'
            )
            return self.get(request, *args, **kwargs)

        # Complete the request using the service
        try:
            FacultyStorageAllocationRequestService.complete_request(
                storage_request,
                directory_name
            )
            messages.success(
                request,
                f'Storage request #{storage_request.pk} has been completed successfully.'
            )
            return self.get(request, *args, **kwargs)
        except Exception as e:
            messages.error(
                request,
                'Unexpected failure. Please contact an administrator.'
            )
            logger.exception(
                f'Error completing storage request {storage_request.pk}: {e}')
            return self.get(request, *args, **kwargs)

    def _get_checklist(self):
        """Return a nested list, where each row contains the details of
        one item on the checklist.

        Each row is of the form: [task text, status name, latest update
        timestamp, is "Manage" button available, URL of "Manage" button].
        """
        pk = self.storage_request.pk
        storage_request = self.storage_request

        checklist = []

        eligibility = storage_request.state['eligibility']
        checklist.append([
            'Confirm that the PI is eligible for a Faculty Storage Allocation.',
            eligibility['status'],
            eligibility['timestamp'],
            True,
            reverse('storage-request-review-eligibility', kwargs={'pk': pk}),
        ])
        is_eligible = eligibility['status'] == 'Approved'

        intake_consistency = storage_request.state['intake_consistency']
        checklist.append([
            ('Confirm that the PI has completed the external intake form and '
             'that the storage amount requested here matches the amount '
             'specified there.'),
            intake_consistency['status'],
            intake_consistency['timestamp'],
            True,
            reverse(
                'storage-request-review-intake-consistency', kwargs={'pk': pk}),
        ])
        is_instake_consistent = intake_consistency['status'] == 'Approved'

        setup = storage_request.state['setup']
        checklist.append([
            'Perform storage setup on the cluster.',
            self._get_setup_status(),
            setup['timestamp'],
            is_eligible and is_instake_consistent,
            reverse('storage-request-review-setup', kwargs={'pk': pk})
        ])

        return checklist

    def _get_setup_status(self):
        """Return one of the following statuses for the 'setup' step of
        the request: 'N/A', 'Pending', 'Complete'."""
        state = self.storage_request.state

        if (state['eligibility']['status'] == 'Denied' or
                state['intake_consistency']['status'] == 'Denied'):
            return 'N/A'
        return state['setup']['status']

    def _is_checklist_complete(self):
        """Return True if all checklist items are complete."""
        state = self.storage_request.state
        return (
            state['eligibility']['status'] == 'Approved' and
            state['intake_consistency']['status'] == 'Approved' and
            state['setup']['status'] == 'Complete')


class StorageRequestListView(LoginRequiredMixin, StorageRequestViewAllAccessMixin,
                             TemplateView):
    template_name = 'cluster_storage/approval/storage_request_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        storage_requests = FacultyStorageAllocationRequest.objects.all().order_by('-request_time')

        search_form = StorageRequestSearchForm(self.request.GET)
        if search_form.is_valid():
            context['search_form'] = search_form
            data = search_form.cleaned_data

            # Apply filters based on form data
            if data.get('project'):
                storage_requests = storage_requests.filter(
                    project=data['project'])
            if data.get('pi'):
                storage_requests = storage_requests.filter(pi=data['pi'])
            if data.get('status'):
                storage_requests = storage_requests.filter(
                    status__name=data['status'])

            filter_parameters = urlencode(
                {key: value for key, value in data.items() if value})
        else:
            context['search_form'] = StorageRequestSearchForm()
            filter_parameters = ''

        # Pagination expects the following context variable.
        context['filter_parameters_with_order_by'] = filter_parameters

        page = self.request.GET.get('page', 1)
        paginator = Paginator(storage_requests, 30)
        try:
            storage_requests = paginator.page(page)
        except PageNotAnInteger:
            storage_requests = paginator.page(1)
        except EmptyPage:
            storage_requests = paginator.page(paginator.num_pages)
        context['storage_requests']  = storage_requests

        # Add requested and approved amount in TB to each request
        for request in context['storage_requests']:
            request.requested_amount_tb = request.requested_amount_gb // 1000
            request.approved_amount_tb = (
                request.approved_amount_gb // 1000 if request.approved_amount_gb else None
            )

        list_url = reverse('storage-request-list')

        for status in StorageRequestSearchForm.STATUS_CHOICES:
            if status[0]:  # Ignore the blank choice.
                context[f'{status}_url'] = (
                    f'{list_url}?{urlencode({"status": status[1]})}')

        # Include information about the PI.
        context['display_user_info'] = True

        return context


class StorageRequestEditView(LoginRequiredMixin,
                             StorageRequestAdminAccessMixin,
                             StorageRequestViewMixin,
                             FormView):
    form_class = StorageRequestEditForm
    template_name = 'cluster_storage/approval/storage_request_review.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['explanatory_paragraph'] = (
            'If necessary, update the amount of storage requested by the user.')
        context['page_title'] = 'Update Storage Amount'
        return context

    def get_initial(self):
        initial = super().get_initial()
        old_amount = (
            self.storage_request.approved_amount_gb or
            self.storage_request.requested_amount_gb)
        initial['storage_amount'] = old_amount // 1000  # Convert GB to TB
        return initial

    def form_valid(self, form):
        """Update the approved storage amount."""
        storage_amount_tb = int(form.cleaned_data['storage_amount'])
        storage_amount_gb = storage_amount_tb * 1000

        # Update the approved amount
        old_amount = (
            self.storage_request.approved_amount_gb or
            self.storage_request.requested_amount_gb)
        self.storage_request.approved_amount_gb = storage_amount_gb
        self.storage_request.save()

        messages.success(
            self.request,
            (f'Storage amount updated from {old_amount} GB to '
             f'{storage_amount_gb} GB.')
        )

        return super().form_valid(form)


class StorageRequestReviewEligibilityView(LoginRequiredMixin,
                                          StorageRequestAdminAccessMixin,
                                          StorageRequestViewMixin,
                                          FormView):
    form_class = StorageRequestReviewStatusForm
    template_name = 'cluster_storage/approval/storage_request_review.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['explanatory_paragraph'] = (
            'Please determine whether the request\'s PI is eligible for a '
            'Faculty Storage Allocation. <b>As part of this, confirm that the '
            'PI does not already have an existing allocation.</b>If the PI is '
            'ineligible, the request will be denied immediately, and a '
            'notification email will be sent to the requester and PI.')
        context['page_title'] = 'Review Eligibility'
        return context

    def get_initial(self):
        initial = super().get_initial()
        eligibility = self.storage_request.state['eligibility']
        initial['status'] = eligibility['status']
        initial['justification'] = eligibility['justification']
        return initial

    def form_valid(self, form):
        """Update eligibility status and optionally deny the request."""
        status = form.cleaned_data['status']
        justification = form.cleaned_data['justification']

        # Update state
        state = self.storage_request.state
        state['eligibility']['status'] = status
        state['eligibility']['justification'] = justification
        state['eligibility']['timestamp'] = utc_now_offset_aware().isoformat()
        self.storage_request.state = state
        self.storage_request.save()

        # Update overall request status based on review statuses
        # (handles approval, denial, or reversion to Under Review)
        self.update_request_status_from_reviews()

        return super().form_valid(form)


class StorageRequestReviewIntakeConsistencyView(LoginRequiredMixin,
                                                StorageRequestAdminAccessMixin,
                                                StorageRequestViewMixin,
                                                FormView):
    form_class = StorageRequestReviewStatusForm
    template_name = 'cluster_storage/approval/storage_request_review.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['explanatory_paragraph'] = (
            'Please confirm that the PI has completed the external intake form '
            'and that the storage amount requested matches the amount '
            'specified in the intake form.'
        )
        context['page_title'] = 'Review Intake Consistency'
        return context

    def get_initial(self):
        initial = super().get_initial()
        intake_consistency = self.storage_request.state['intake_consistency']
        initial['status'] = intake_consistency['status']
        initial['justification'] = intake_consistency['justification']
        return initial

    def form_valid(self, form):
        """Update intake consistency status and optionally deny the request."""
        status = form.cleaned_data['status']
        justification = form.cleaned_data['justification']

        # Update state
        state = self.storage_request.state
        state['intake_consistency']['status'] = status
        state['intake_consistency']['justification'] = justification
        state['intake_consistency']['timestamp'] = utc_now_offset_aware().isoformat()
        self.storage_request.state = state
        self.storage_request.save()

        # Update overall request status based on review statuses
        # (handles approval, denial, or reversion to Under Review)
        self.update_request_status_from_reviews()

        return super().form_valid(form)


class StorageRequestReviewSetupView(LoginRequiredMixin,
                                    StorageRequestAdminAccessMixin,
                                    StorageRequestViewMixin,
                                    FormView):
    form_class = StorageRequestReviewSetupForm
    template_name = 'cluster_storage/approval/storage_request_review.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['explanatory_paragraph'] = (
            'Please perform directory setup on the cluster.')
        context['page_title'] = 'Setup'
        return context

    def get_initial(self):
        initial = super().get_initial()
        setup = self.storage_request.state['setup']
        initial['status'] = setup['status']
        # Pre-populate with project name as default
        initial['directory_name'] = (
            setup.get('directory_name', '') or
            self.storage_request.project.name)
        return initial

    def form_valid(self, form):
        """Update setup status and directory name."""
        status = form.cleaned_data['status']
        # Set the directory name to the project name.
        directory_name = self.storage_request.project.name

        # Update state
        state = self.storage_request.state
        state['setup']['status'] = status
        state['setup']['directory_name'] = directory_name
        state['setup']['timestamp'] = utc_now_offset_aware().isoformat()
        self.storage_request.state = state
        self.storage_request.save()

        messages.success(
            self.request,
            f'Setup status updated to {status}.'
        )

        return super().form_valid(form)


class StorageRequestReviewDenyView(LoginRequiredMixin,
                                   StorageRequestAdminAccessMixin,
                                   StorageRequestViewMixin,
                                   FormView):
    form_class = StorageRequestReviewDenyForm
    template_name = 'cluster_storage/approval/storage_request_review.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['explanatory_paragraph'] = (
            'Deny the request for some other reason. A notification email will '
            'be sent to the requester and PI.')
        context['page_title'] = 'Deny'
        return context

    def get_initial(self):
        initial = super().get_initial()
        other = self.storage_request.state['other']
        initial['justification'] = other.get('justification', '')
        return initial

    def form_valid(self, form):
        """Deny the request with the provided justification."""
        justification = form.cleaned_data['justification']
        state = self.storage_request.state
        state['other'] = {
            'justification': justification,
            'timestamp': utc_now_offset_aware().isoformat(),
        }
        self.storage_request.state = state
        self.storage_request.save()

        FacultyStorageAllocationRequestService.deny_request(
            self.storage_request
        )

        messages.success(
            self.request,
            'The request has been denied.'
        )

        return super().form_valid(form)


class StorageRequestUndenyView(LoginRequiredMixin,
                               StorageRequestAdminAccessMixin,
                               StorageRequestViewMixin,
                               View):

    def dispatch(self, request, *args, **kwargs):
        """Check if the request can be undenied."""
        # Get the pk before calling super().dispatch()
        pk = self.kwargs.get('pk')

        # StorageRequestViewMixin.dispatch() sets self.storage_request
        # This calls the mixin's dispatch which retrieves the object
        # We need to manually get it first to check status before proceeding
        self.storage_request = get_object_or_404(
            FacultyStorageAllocationRequest, pk=pk)

        # Only allow undenying if the request is currently denied
        if self.storage_request.status.name != 'Denied':
            message = (
                f'Request {pk} cannot be undenied because it has status '
                f'{self.storage_request.status.name}.')
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('storage-request-detail', kwargs={'pk': pk}))

        # Now proceed with the rest of the dispatch chain
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Undeny the request by calling the service method."""
        pk = self.storage_request.pk

        try:
            FacultyStorageAllocationRequestService.undeny_request(
                self.storage_request
            )
            message = 'The request is under review.'
            messages.success(request, message)
            logger.info(
                f'FacultyStorageAllocationRequest {pk} was undenied by '
                f'{request.user.username}.')
        except Exception as e:
            message = f'Failed to undeny request {pk}.'
            messages.error(request, message)
            logger.exception(
                f'Error undenying FacultyStorageAllocationRequest {pk}: {e}')

        return HttpResponseRedirect(
            reverse('storage-request-detail', kwargs={'pk': pk}))


__all__ = [
    'StorageRequestDetailView',
    'StorageRequestEditView',
    'StorageRequestListView',
    'StorageRequestReviewDenyView',
    'StorageRequestReviewEligibilityView',
    'StorageRequestReviewIntakeConsistencyView',
    'StorageRequestReviewSetupView',
    'StorageRequestUndenyView',
]


# TODO: Should the state only be updated by the request service? We're exposing
#  the structure of the request.
