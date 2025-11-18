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

from coldfront.plugins.faculty_storage_allocations.forms import FSARequestEditForm
from coldfront.plugins.faculty_storage_allocations.forms import FSARequestReviewDenyForm
from coldfront.plugins.faculty_storage_allocations.forms import FSARequestReviewSetupForm
from coldfront.plugins.faculty_storage_allocations.forms import FSARequestReviewStatusForm
from coldfront.plugins.faculty_storage_allocations.forms import FSARequestSearchForm
from coldfront.plugins.faculty_storage_allocations.models import FacultyStorageAllocationRequest
from coldfront.plugins.faculty_storage_allocations.models import FacultyStorageAllocationRequestStatusChoice
from coldfront.plugins.faculty_storage_allocations.services import FacultyStorageAllocationRequestService

logger = logging.getLogger(__name__)


class FSARequestReadOnlyAccessMixin(UserPassesTestMixin):
    """Mixin for read-only access to FSA request views.

    Allows access to:
    - Superusers
    - Users with 'can_view_all_fsa_requests' or
      'can_manage_fsa_requests' permission
    - The requester of the FSA request
    - The PI of the FSA request

    Requires that the view has a `fsa_request` attribute set before
    test_func is called (typically in dispatch).
    """

    def test_func(self):
        """Check if user has permission to view FSA requests."""
        user = self.request.user

        # Superusers have full access
        if user.is_superuser:
            return True

        # Users with view or manage permissions can access
        if (user.has_perm('faculty_storage_allocations.can_view_all_fsa_requests') or
            user.has_perm('faculty_storage_allocations.can_manage_fsa_requests')):
            return True

        # Allow the requester and PI to view their own request
        if hasattr(self, 'fsa_request'):
            if (user == self.fsa_request.requester or
                user == self.fsa_request.pi):
                return True

        message = 'You do not have permission to view this FSA request.'
        messages.error(self.request, message)
        return False


class FSARequestAdminAccessMixin(UserPassesTestMixin):
    """Mixin for admin-only access to FSA request management views.

    Allows access to:
    - Superusers
    - Users with 'can_manage_fsa_requests' permission
    """

    def test_func(self):
        """Check if user has permission to manage FSA requests."""
        user = self.request.user

        # Superusers have full access
        if user.is_superuser:
            return True

        # Users with the specific permission can manage
        if user.has_perm('faculty_storage_allocations.can_manage_fsa_requests'):
            return True

        message = 'You do not have permission to manage FSA requests.'
        messages.error(self.request, message)
        return False


class FSARequestViewAllAccessMixin(UserPassesTestMixin):
    """Mixin for viewing all FSA requests (list view).

    Allows access to:
    - Superusers
    - Users with 'can_view_all_fsa_requests' or
      'can_manage_fsa_requests' permission

    This is used for the list view where users can see all requests,
    not just their own.
    """

    def test_func(self):
        """Check if user has permission to view all FSA requests."""
        user = self.request.user

        # Superusers have full access
        if user.is_superuser:
            return True

        # Users with view or manage permissions can access
        if (user.has_perm('faculty_storage_allocations.can_view_all_fsa_requests') or
            user.has_perm('faculty_storage_allocations.can_manage_fsa_requests')):
            return True

        message = 'You do not have permission to view all FSA requests.'
        messages.error(self.request, message)
        return False


class FSARequestAmountMixin:
    """Mixin to add requested and approved amount in TB to context."""

    def add_amount_context(self, context):
        """Add requested_amount_tb and approved_amount_tb to context."""
        if hasattr(self, 'fsa_request'):
            context['requested_amount_tb'] = (
                self.fsa_request.requested_amount_gb // 1000)
            context['approved_amount_tb'] = (
                self.fsa_request.approved_amount_gb // 1000
                if self.fsa_request.approved_amount_gb else None
            )
        return context


class FSARequestViewMixin(FSARequestAmountMixin):
    """Base mixin for FSA request views with common functionality.

    Note: This mixin does NOT include permission checks. Views should
    inherit from either FSARequestReadOnlyAccessMixin or
    FSARequestAdminAccessMixin as appropriate.
    """

    def dispatch(self, request, *args, **kwargs):
        """Retrieve and cache the FSA request object."""
        pk = self.kwargs.get('pk')
        self.fsa_request = get_object_or_404(
            FacultyStorageAllocationRequest, pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add common context variables."""
        context = super().get_context_data(**kwargs)
        context['fsa_request'] = self.fsa_request
        # Determine if user can manage based on permission
        user = self.request.user
        context['is_allowed_to_manage_request'] = (
            user.is_superuser or
            user.has_perm('faculty_storage_allocations.can_manage_fsa_requests')
        )
        context = self.add_amount_context(context)
        return context

    def get_success_url(self):
        """Return to the FSA request detail page."""
        pk = self.kwargs.get('pk')
        return reverse('faculty-storage-allocation-request-detail', kwargs={'pk': pk})

    def update_request_status_from_reviews(self):
        """Update the overall request status based on review step statuses.

        - If either review is denied: Call deny_request to update overall status
        - If both eligibility and intake consistency are approved:
          Move to "Approved - Queued" status (waiting for agent to process)
        - If either review is pending and request is in an approved state:
          Move back to "Under Review" status

        Returns True if status was changed, False otherwise.
        """
        state = self.fsa_request.state
        eligibility_status = state['eligibility']['status']
        intake_status = state['intake_consistency']['status']
        current_status = self.fsa_request.status.name

        try:
            # If either review is denied, deny the request
            if eligibility_status == 'Denied' or intake_status == 'Denied':
                FacultyStorageAllocationRequestService.deny_request(
                    self.fsa_request
                )
                messages.success(self.request, 'The request has been denied.')
                return True

            # If both reviews are approved, move to Approved - Processing
            elif (eligibility_status == 'Approved' and
                      intake_status == 'Approved'):
                FacultyStorageAllocationRequestService.approve_request(
                    self.fsa_request
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
                    self.fsa_request.status = under_review_status
                    self.fsa_request.save()
                    messages.info(self.request, 'The request is under review.')
                    return True

        except Exception as e:
            messages.error(
                self.request,
                'Unexpected failure. Please contact an administrator.'
            )
            logger.exception(
                f'Error updating request status for {self.fsa_request.pk}: '
                f'{e}')
            return False

        return False


class FSARequestDetailView(LoginRequiredMixin,
                               FSARequestViewMixin,
                               FSARequestReadOnlyAccessMixin,
                               TemplateView):
    template_name = 'faculty_storage_allocations/approval/fsa_request_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Only allow editing if user is admin AND status is "Under Review"
        user = self.request.user
        context['allow_editing'] = (
            (user.is_superuser or
             user.has_perm('faculty_storage_allocations.can_manage_fsa_requests')) and
            self.fsa_request.status.name == 'Under Review'
        )

        if self.fsa_request.status.name == 'Denied':
            context['denial_reason'] = self.fsa_request.denial_reason()

        # Add proposed directory path
        from coldfront.plugins.faculty_storage_allocations.services import DirectoryService
        context['proposed_directory_path'] = \
            DirectoryService.get_directory_path_for_project(
                self.fsa_request.project,
                fsa_request=self.fsa_request
            )

        context['support_email'] = settings.CENTER_HELP_EMAIL

        try:
            latest_update_timestamp = \
                self.fsa_request.latest_update_timestamp()
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
        """Complete the FSA request if all checklist items are approved.

        Only superusers and users with 'can_manage_fsa_requests'
        permission can POST.
        """
        user = request.user

        # Check admin permissions for POST
        if not (user.is_superuser or
                user.has_perm('faculty_storage_allocations.can_manage_fsa_requests')):
            messages.error(
                request,
                'You do not have permission to complete FSA requests.'
            )
            return self.get(request, *args, **kwargs)

        fsa_request = self.fsa_request

        # Validate that all checklist items are approved
        state = fsa_request.state
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
                fsa_request,
                directory_name
            )
            messages.success(
                request,
                f'FSA request #{fsa_request.pk} has been completed successfully.'
            )
            return self.get(request, *args, **kwargs)
        except Exception as e:
            messages.error(
                request,
                'Unexpected failure. Please contact an administrator.'
            )
            logger.exception(
                f'Error completing FSA request {fsa_request.pk}: {e}')
            return self.get(request, *args, **kwargs)

    def _get_checklist(self):
        """Return a nested list, where each row contains the details of
        one item on the checklist.

        Each row is of the form: [task text, status name, latest update
        timestamp, is "Manage" button available, URL of "Manage" button].
        """
        pk = self.fsa_request.pk
        fsa_request = self.fsa_request

        checklist = []

        eligibility = fsa_request.state['eligibility']
        checklist.append([
            'Confirm that the PI is eligible for a Faculty Storage Allocation.',
            eligibility['status'],
            eligibility['timestamp'],
            True,
            reverse('faculty-storage-allocation-request-review-eligibility', kwargs={'pk': pk}),
        ])
        is_eligible = eligibility['status'] == 'Approved'

        intake_consistency = fsa_request.state['intake_consistency']
        checklist.append([
            ('Confirm that the PI has completed the external intake form and '
             'that the storage amount requested here matches the amount '
             'specified there.'),
            intake_consistency['status'],
            intake_consistency['timestamp'],
            True,
            reverse(
                'faculty-storage-allocation-request-review-intake-consistency', kwargs={'pk': pk}),
        ])
        is_instake_consistent = intake_consistency['status'] == 'Approved'

        setup = fsa_request.state['setup']
        checklist.append([
            'Perform storage setup on the cluster.',
            self._get_setup_status(),
            setup['timestamp'],
            is_eligible and is_instake_consistent,
            reverse('faculty-storage-allocation-request-review-setup', kwargs={'pk': pk})
        ])

        return checklist

    def _get_setup_status(self):
        """Return one of the following statuses for the 'setup' step of
        the request: 'N/A', 'Pending', 'Complete'."""
        state = self.fsa_request.state

        if (state['eligibility']['status'] == 'Denied' or
                state['intake_consistency']['status'] == 'Denied'):
            return 'N/A'
        return state['setup']['status']

    def _is_checklist_complete(self):
        """Return True if all checklist items are complete."""
        state = self.fsa_request.state
        return (
            state['eligibility']['status'] == 'Approved' and
            state['intake_consistency']['status'] == 'Approved' and
            state['setup']['status'] == 'Complete')


class FSARequestListView(LoginRequiredMixin, FSARequestViewAllAccessMixin,
                             TemplateView):
    template_name = 'faculty_storage_allocations/approval/fsa_request_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fsa_requests = FacultyStorageAllocationRequest.objects.all().order_by('-request_time')

        search_form = FSARequestSearchForm(self.request.GET)
        if search_form.is_valid():
            context['search_form'] = search_form
            data = search_form.cleaned_data

            # Apply filters based on form data
            if data.get('project'):
                fsa_requests = fsa_requests.filter(
                    project=data['project'])
            if data.get('pi'):
                fsa_requests = fsa_requests.filter(pi=data['pi'])
            if data.get('status'):
                fsa_requests = fsa_requests.filter(
                    status__name=data['status'])

            filter_parameters = urlencode(
                {key: value for key, value in data.items() if value})
        else:
            context['search_form'] = FSARequestSearchForm()
            filter_parameters = ''

        # Pagination expects the following context variable.
        context['filter_parameters_with_order_by'] = filter_parameters

        page = self.request.GET.get('page', 1)
        paginator = Paginator(fsa_requests, 30)
        try:
            fsa_requests = paginator.page(page)
        except PageNotAnInteger:
            fsa_requests = paginator.page(1)
        except EmptyPage:
            fsa_requests = paginator.page(paginator.num_pages)
        context['fsa_requests']  = fsa_requests

        # Add requested and approved amount in TB to each request
        for request in context['fsa_requests']:
            request.requested_amount_tb = request.requested_amount_gb // 1000
            request.approved_amount_tb = (
                request.approved_amount_gb // 1000 if request.approved_amount_gb else None
            )

        list_url = reverse('faculty-storage-allocation-request-list')

        for status in FSARequestSearchForm.STATUS_CHOICES:
            if status[0]:  # Ignore the blank choice.
                context[f'{status}_url'] = (
                    f'{list_url}?{urlencode({"status": status[1]})}')

        return context


class FSARequestEditView(LoginRequiredMixin,
                             FSARequestAdminAccessMixin,
                             FSARequestViewMixin,
                             FormView):
    form_class = FSARequestEditForm
    template_name = 'faculty_storage_allocations/approval/fsa_request_review.html'

    def dispatch(self, request, *args, **kwargs):
        """Check if the request can be edited."""
        # Call parent dispatch first to set self.fsa_request
        response = super().dispatch(request, *args, **kwargs)

        # Only allow editing if request is "Under Review"
        if self.fsa_request.status.name != 'Under Review':
            messages.error(
                request,
                f'Cannot edit storage amount: request is in status '
                f'"{self.fsa_request.status.name}". '
                f'Amount can only be edited while Under Review.'
            )
            return HttpResponseRedirect(
                reverse('faculty-storage-allocation-request-detail',
                       kwargs={'pk': self.fsa_request.pk})
            )

        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['explanatory_paragraph'] = (
            'If necessary, update the amount of FSA requested by the user.')
        context['page_title'] = 'Update Storage Amount'
        return context

    def get_initial(self):
        initial = super().get_initial()
        old_amount = (
            self.fsa_request.approved_amount_gb or
            self.fsa_request.requested_amount_gb)
        initial['storage_amount'] = old_amount // 1000  # Convert GB to TB
        return initial

    def form_valid(self, form):
        """Update the approved storage amount."""
        storage_amount_tb = int(form.cleaned_data['storage_amount'])
        storage_amount_gb = storage_amount_tb * 1000

        # Update the approved amount
        old_amount = (
            self.fsa_request.approved_amount_gb or
            self.fsa_request.requested_amount_gb)
        self.fsa_request.approved_amount_gb = storage_amount_gb
        self.fsa_request.save()

        messages.success(
            self.request,
            (f'Storage amount updated from {old_amount} GB to '
             f'{storage_amount_gb} GB.')
        )

        return super().form_valid(form)


class FSARequestReviewEligibilityView(LoginRequiredMixin,
                                          FSARequestAdminAccessMixin,
                                          FSARequestViewMixin,
                                          FormView):
    form_class = FSARequestReviewStatusForm
    template_name = 'faculty_storage_allocations/approval/fsa_request_review.html'

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
        eligibility = self.fsa_request.state['eligibility']
        initial['status'] = eligibility['status']
        initial['justification'] = eligibility['justification']
        return initial

    def form_valid(self, form):
        """Update eligibility status and optionally deny the request."""
        status = form.cleaned_data['status']
        justification = form.cleaned_data['justification']

        # Use service to update state
        FacultyStorageAllocationRequestService.update_eligibility_state(
            self.fsa_request, status, justification)

        # Update overall request status based on review statuses
        # (handles approval, denial, or reversion to Under Review)
        self.update_request_status_from_reviews()

        return super().form_valid(form)


class FSARequestReviewIntakeConsistencyView(LoginRequiredMixin,
                                                FSARequestAdminAccessMixin,
                                                FSARequestViewMixin,
                                                FormView):
    form_class = FSARequestReviewStatusForm
    template_name = 'faculty_storage_allocations/approval/fsa_request_review.html'

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
        intake_consistency = self.fsa_request.state['intake_consistency']
        initial['status'] = intake_consistency['status']
        initial['justification'] = intake_consistency['justification']
        return initial

    def form_valid(self, form):
        """Update intake consistency status and optionally deny the request."""
        status = form.cleaned_data['status']
        justification = form.cleaned_data['justification']

        # Use service to update state
        FacultyStorageAllocationRequestService.update_intake_consistency_state(
            self.fsa_request, status, justification)

        # Update overall request status based on review statuses
        # (handles approval, denial, or reversion to Under Review)
        self.update_request_status_from_reviews()

        return super().form_valid(form)


class FSARequestReviewSetupView(LoginRequiredMixin,
                                    FSARequestAdminAccessMixin,
                                    FSARequestViewMixin,
                                    FormView):
    form_class = FSARequestReviewSetupForm
    template_name = 'faculty_storage_allocations/approval/fsa_request_review.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['explanatory_paragraph'] = (
            'Please perform directory setup on the cluster.')
        context['page_title'] = 'Setup'
        return context

    def get_initial(self):
        initial = super().get_initial()
        setup = self.fsa_request.state['setup']
        initial['status'] = setup['status']
        # Pre-populate with project name as default
        initial['directory_name'] = (
            setup.get('directory_name', '') or
            self.fsa_request.project.name)
        return initial

    def form_valid(self, form):
        """Update setup status and directory name."""
        status = form.cleaned_data['status']
        # Set the directory name to the project name.
        directory_name = self.fsa_request.project.name

        # Use the service to update setup state
        if status == 'Complete':
            FacultyStorageAllocationRequestService.update_setup_state(
                self.fsa_request,
                directory_name=directory_name,
                status='Complete'
            )
            messages.success(
                self.request,
                f'Setup marked as complete with directory: {directory_name}'
            )
        else:
            FacultyStorageAllocationRequestService.update_setup_state(
                self.fsa_request,
                status=status
            )
            messages.success(
                self.request,
                f'Setup status updated to {status}.'
            )

        return super().form_valid(form)


class FSARequestReviewDenyView(LoginRequiredMixin,
                                   FSARequestAdminAccessMixin,
                                   FSARequestViewMixin,
                                   FormView):
    form_class = FSARequestReviewDenyForm
    template_name = 'faculty_storage_allocations/approval/fsa_request_review.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['explanatory_paragraph'] = (
            'Deny the request for some other reason. A notification email will '
            'be sent to the requester and PI.')
        context['page_title'] = 'Deny'
        return context

    def get_initial(self):
        initial = super().get_initial()
        other = self.fsa_request.state['other']
        initial['justification'] = other.get('justification', '')
        return initial

    def form_valid(self, form):
        """Deny the request with the provided justification."""
        justification = form.cleaned_data['justification']

        # Use service to update state
        FacultyStorageAllocationRequestService.update_other_state(
            self.fsa_request, justification)

        FacultyStorageAllocationRequestService.deny_request(
            self.fsa_request
        )

        messages.success(
            self.request,
            'The request has been denied.'
        )

        return super().form_valid(form)


class FSARequestUndenyView(LoginRequiredMixin,
                               FSARequestAdminAccessMixin,
                               FSARequestViewMixin,
                               View):

    def dispatch(self, request, *args, **kwargs):
        """Check if the request can be undenied."""
        # Get the pk before calling super().dispatch()
        pk = self.kwargs.get('pk')

        # FSARequestViewMixin.dispatch() sets self.fsa_request
        # This calls the mixin's dispatch which retrieves the object
        # We need to manually get it first to check status before proceeding
        self.fsa_request = get_object_or_404(
            FacultyStorageAllocationRequest, pk=pk)

        # Only allow undenying if the request is currently denied
        if self.fsa_request.status.name != 'Denied':
            message = (
                f'Request {pk} cannot be undenied because it has status '
                f'{self.fsa_request.status.name}.')
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('faculty-storage-allocation-request-detail', kwargs={'pk': pk}))

        # Now proceed with the rest of the dispatch chain
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Undeny the request by calling the service method."""
        pk = self.fsa_request.pk

        try:
            FacultyStorageAllocationRequestService.undeny_request(
                self.fsa_request
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
            reverse('faculty-storage-allocation-request-detail', kwargs={'pk': pk}))


__all__ = [
    'FSARequestDetailView',
    'FSARequestEditView',
    'FSARequestListView',
    'FSARequestReviewDenyView',
    'FSARequestReviewEligibilityView',
    'FSARequestReviewIntakeConsistencyView',
    'FSARequestReviewSetupView',
    'FSARequestUndenyView',
]

