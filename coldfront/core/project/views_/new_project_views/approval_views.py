from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.utils import annotate_queryset_with_allocation_period_not_started_bool
from coldfront.core.allocation.utils import calculate_service_units_to_allocate
from coldfront.core.project.forms import MemorandumSignedForm
from coldfront.core.project.forms import ReviewDenyForm
from coldfront.core.project.forms import ReviewStatusForm
from coldfront.core.project.forms_.new_project_forms.request_forms import NewProjectExtraFieldsFormFactory
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectSurveyForm
from coldfront.core.project.forms_.new_project_forms.approval_forms import SavioProjectReviewSetupForm
from coldfront.core.project.forms_.new_project_forms.approval_forms import VectorProjectReviewSetupForm
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.models import VectorProjectAllocationRequest
from coldfront.core.project.utils_.new_project_utils import ProjectDenialRunner
from coldfront.core.project.utils_.new_project_utils import SavioProjectApprovalRunner
from coldfront.core.project.utils_.new_project_utils import SavioProjectProcessingRunner
from coldfront.core.project.utils_.new_project_utils import savio_request_state_status
from coldfront.core.project.utils_.new_project_utils import send_project_request_pooling_email
from coldfront.core.project.utils_.new_project_utils import VectorProjectProcessingRunner
from coldfront.core.project.utils_.new_project_utils import vector_request_state_status
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.common import display_time_zone_current_date
from coldfront.core.utils.common import format_date_month_name_day_year
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.email.email_strategy import DropEmailStrategy
from coldfront.core.utils.email.email_strategy import EnqueueEmailStrategy

from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DetailView
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from coldfront.core.utils.views.mou_views import MOURequestNotifyPIViewMixIn
from flags.state import flag_enabled

import iso8601
import logging


# =============================================================================
# BRC: SAVIO
# =============================================================================


class SavioProjectRequestListView(LoginRequiredMixin, TemplateView):
    template_name = 'project/project_request/savio/project_request_list.html'
    # Show completed requests if True; else, show pending requests.
    completed = False

    def get_queryset(self):
        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            if direction == 'asc':
                direction = ''
            else:
                direction = '-'
            order_by = direction + order_by
        else:
            order_by = '-request_time'

        return annotate_queryset_with_allocation_period_not_started_bool(
            SavioProjectAllocationRequest.objects.order_by(order_by))

    def get_context_data(self, **kwargs):
        """Include either pending or completed requests. If the user is
        a superuser, show all such requests. Otherwise, show only those
        for which the user is a requester or PI."""
        context = super().get_context_data(**kwargs)
        args, kwargs = [], {}

        request_list = self.get_queryset()
        user = self.request.user
        permission = 'project.view_savioprojectallocationrequest'
        if not (user.is_superuser or user.has_perm(permission)):
            args.append(Q(requester=user) | Q(pi=user))
        if self.completed:
            status__name__in = [
                'Approved - Complete', 'Approved - Scheduled', 'Denied']
        else:
            status__name__in = ['Under Review', 'Approved - Processing']
        kwargs['status__name__in'] = status__name__in
        context['savio_project_request_list'] = request_list.filter(
            *args, **kwargs)
        context['request_filter'] = (
            'completed' if self.completed else 'pending')

        return context


class SavioProjectRequestMixin(object):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.interface = ComputingAllowanceInterface()
        self.request_obj = None
        self.computing_allowance_obj = None

    def assert_attributes_set(self):
        """Assert that the attributes have been set."""
        assert isinstance(self.request_obj, SavioProjectAllocationRequest)
        assert isinstance(self.computing_allowance_obj, ComputingAllowance)

    def get_extra_fields_form(self, disable_fields=True):
        """Return a form of extra fields for the request, based on its
        computing allowance, and populated with initial data."""
        self.assert_attributes_set()
        computing_allowance = self.computing_allowance_obj
        extra_fields = self.request_obj.extra_fields
        kwargs = {
            'initial': extra_fields,
            'disable_fields': disable_fields,
        }
        factory = NewProjectExtraFieldsFormFactory()
        return factory.get_form(computing_allowance, **kwargs)

    def get_service_units_to_allocate(self):
        """Return the possibly-prorated number of service units to
        allocate to the project.

        If the request was created as part of an allocation renewal, it
        may be associated with at most one AllocationRenewalRequest. If
        so, service units will be allocated when the latter request is
        approved."""
        if AllocationRenewalRequest.objects.filter(
                new_project_request=self.request_obj).exists():
            return settings.ALLOCATION_MIN
        if self.computing_allowance_obj.are_service_units_user_specified():
            num_service_units_int = self.request_obj.extra_fields[
                'num_service_units']
            num_service_units = Decimal(f'{num_service_units_int:.2f}')
        else:
            kwargs = {}
            allocation_period = self.request_obj.allocation_period
            if allocation_period:
                kwargs['allocation_period'] = allocation_period
            num_service_units = calculate_service_units_to_allocate(
                self.computing_allowance_obj, self.request_obj.request_time,
                **kwargs)
        return num_service_units

    def get_survey_form(self):
        """Return a disabled form containing the survey answers for the
        request."""
        self.assert_attributes_set()
        survey_answers = self.request_obj.survey_answers
        kwargs = {
            'initial': survey_answers,
            'disable_fields': True,
        }
        # TODO
        return SavioProjectSurveyForm(**kwargs)

    def redirect_if_disallowed_status(self, http_request,
                                      disallowed_status_names=(
            'Approved - Scheduled', 'Approved - Complete', 'Denied')):
        """Return a redirect response to the detail view for this
        project request if its status has one of the given disallowed
        names, after sending a message to the user. Otherwise, return
        None."""
        self.assert_attributes_set()
        status_name = self.request_obj.status.name
        if status_name in disallowed_status_names:
            message = (
                f'You cannot perform this action on a request with status '
                f'{status_name}.')
            messages.error(http_request, message)
            return HttpResponseRedirect(
                self.request_detail_url(self.request_obj.pk))
        return None

    @staticmethod
    def request_detail_url(pk):
        """Return the URL to the detail view for the request with the
        given primary key."""
        return reverse('new-project-request-detail', kwargs={'pk': pk})

    def set_attributes(self, pk):
        """Set this instance's request_obj to be the
        SavioProjectAllocationRequest with the given primary key."""
        self.request_obj = get_object_or_404(
            SavioProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)
        self.computing_allowance_obj = ComputingAllowance(
            self.request_obj.computing_allowance)

    def set_common_context_data(self, context):
        """Given a dictionary of context variables to include in the
        template, add additional, commonly-used variables."""
        self.assert_attributes_set()
        context['savio_request'] = self.request_obj
        context['computing_allowance_name'] = \
            self.computing_allowance_obj.get_name()
        context['allowance_has_extra_fields'] = \
            self.computing_allowance_obj.requires_extra_information()
        if context['allowance_has_extra_fields']:
            context['extra_fields_form'] = self.get_extra_fields_form()
        context['allowance_requires_mou'] = \
            self.computing_allowance_obj.requires_memorandum_of_understanding()
        context['allowance_requires_funds_transfer'] = (
            self.computing_allowance_obj.is_recharge() and
            context['allowance_has_extra_fields'])
        try:
            context['allocation_amount'] = self.get_service_units_to_allocate()
        except Exception as e:
            context['allocation_amount'] = 'Failed to compute.'
        context['survey_form'] = SavioProjectSurveyForm(
            initial=self.request_obj.survey_answers, disable_fields=True)

class SavioProjectRequestEditExtraFieldsView(LoginRequiredMixin,
                                             UserPassesTestMixin,
                                             SavioProjectRequestMixin,
                                             TemplateView):
    template_name = 'project/project_request/savio/project_request_edit_extra_fields.html'

    logger = logging.getLogger(__name__)

    error_message = 'Unexpected failure. Please contact an administrator.'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_attributes(pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = {}
        context['form'] = self.get_extra_fields_form(disable_fields=False)
        context['savio_request'] = self.request_obj
        context['notify_pi'] = False
        return context

    def post(self, request, *args, **kwargs):
        form = NewProjectExtraFieldsFormFactory() \
                        .get_form(self.computing_allowance_obj, request.POST)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        """Save the form."""
        self.request_obj.extra_fields = form.cleaned_data
        self.request_obj.save()
        message = 'The request has been updated.'
        messages.success(self.request, message)
        return HttpResponseRedirect(reverse('new-project-request-detail',
                                            kwargs={'pk':self.request_obj.pk}))

    def form_invalid(self, form):
        """Handle invalid forms."""
        message = 'Please correct the errors below.'
        messages.error(self.request, message)
        return self.render_to_response(
            self.get_context_data(form=form))
                                      
class SavioProjectRequestNotifyPIView(MOURequestNotifyPIViewMixIn,
                                    SavioProjectRequestEditExtraFieldsView):
    def email_pi(self):
        super()._email_pi('Savio Project Request Ready To Be Signed',
                         self.request_obj.pi.get_full_name(),
                         reverse('new-project-request-detail',
                                 kwargs={'pk': self.request_obj.pk}),
                         'Memorandum of Understanding',
                         f'{self.request_obj.project.name} project request',
                         self.request_obj.pi.email)

class SavioProjectRequestDetailView(LoginRequiredMixin, UserPassesTestMixin,
                                    SavioProjectRequestMixin, DetailView):
    model = SavioProjectAllocationRequest
    template_name = 'project/project_request/savio/project_request_detail.html'

    logger = logging.getLogger(__name__)

    error_message = 'Unexpected failure. Please contact an administrator.'

    redirect = reverse_lazy('new-project-pending-request-list')

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm(
                'project.view_savioprojectallocationrequest'):
            return True

        if (self.request.user == self.request_obj.requester or
                self.request.user == self.request_obj.pi):
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_attributes(pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.set_common_context_data(context)

        try:
            context['allocation_amount'] = self.get_service_units_to_allocate()
        except Exception as e:
            self.logger.exception(e)
            messages.error(self.request, self.error_message)
            context['allocation_amount'] = 'Failed to compute.'

        try:
            latest_update_timestamp = \
                self.request_obj.latest_update_timestamp()
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
            messages.error(self.request, self.error_message)
            latest_update_timestamp = 'Failed to determine timestamp.'
        context['latest_update_timestamp'] = latest_update_timestamp

        if self.request_obj.status.name == 'Denied':
            try:
                denial_reason = self.request_obj.denial_reason()
                category = denial_reason.category
                justification = denial_reason.justification
                timestamp = denial_reason.timestamp
            except Exception as e:
                self.logger.exception(e)
                messages.error(self.request, self.error_message)
                category = 'Unknown Category'
                justification = (
                    'Failed to determine denial reason. Please contact an '
                    'administrator.')
                timestamp = 'Unknown Timestamp'
            context['denial_reason'] = {
                'category': category,
                'justification': justification,
                'timestamp': timestamp,
            }
            context['support_email'] = settings.CENTER_HELP_EMAIL

        context['has_allocation_period_started'] = \
            self.has_request_allocation_period_started()
        context['setup_status'] = self.get_setup_status()
        context['checklist'] = self.get_checklist()
        context['is_checklist_complete'] = self.is_checklist_complete()
        context['is_allowed_to_manage_request'] = \
            self.request.user.is_superuser

        context['mou_required'] = \
            ComputingAllowance(self.request_obj.computing_allowance) \
                .requires_memorandum_of_understanding()
        if context['mou_required']:
            context['can_download_mou'] = self.request_obj \
                                        .state['notified']['status'] == 'Complete'
            context['can_upload_mou'] = \
                self.request_obj.status.name == 'Under Review'
            context['mou_uploaded'] = bool(self.request_obj.mou_file)

            context['unsigned_download_url'] = reverse('new-project-request-download-unsigned-mou',
                                                        kwargs={'pk': self.request_obj.pk,
                                                                'request_type': 'new-project'})
            context['signed_download_url'] = reverse('new-project-request-download-mou',
                                                        kwargs={'pk': self.request_obj.pk,
                                                                'request_type': 'new-project'})
            context['signed_upload_url'] = reverse('new-project-request-upload-mou',
                                                        kwargs={'pk': self.request_obj.pk,
                                                                'request_type': 'new-project'})
            context['mou_type'] = 'Memorandum of Understanding'

        context['is_recharge'] = \
            ComputingAllowance(self.request_obj.computing_allowance) \
                .is_recharge()

        return context

    def post(self, request, *args, **kwargs):
        """Approve the request. Process it if its AllocationPeriod has
        already started."""
        if not self.request.user.is_superuser:
            message = 'You do not have permission to access this page.'
            messages.error(request, message)
            pk = self.request_obj.pk

            return HttpResponseRedirect(
                reverse('new-project-request-detail', kwargs={'pk': pk}))

        if not self.is_checklist_complete():
            message = 'Please complete the checklist before final activation.'
            messages.error(request, message)
            pk = self.request_obj.pk
            return HttpResponseRedirect(
                reverse('new-project-request-detail', kwargs={'pk': pk}))

        email_strategy = EnqueueEmailStrategy()
        project = self.request_obj.project
        try:
            should_process_request = \
                self.has_request_allocation_period_started()
            num_service_units = self.get_service_units_to_allocate()

            with transaction.atomic():
                # Approve the request. If the request will be processed
                # immediately after, avoid sending an approval email.
                if should_process_request:
                    approval_email_strategy = DropEmailStrategy()
                else:
                    approval_email_strategy = email_strategy
                approval_runner = SavioProjectApprovalRunner(
                    self.request_obj, num_service_units,
                    email_strategy=approval_email_strategy)
                approval_runner.run()

                # Process the request if applicable.
                if should_process_request:
                    self.request_obj.refresh_from_db()
                    processing_runner = SavioProjectProcessingRunner(
                        self.request_obj, num_service_units,
                        email_strategy=email_strategy)
                    project, _ = processing_runner.run()
        except Exception as e:
            self.logger.exception(e)
            messages.error(self.request, self.error_message)
        else:
            if not should_process_request:
                formatted_start_date = format_date_month_name_day_year(
                    self.request_obj.allocation_period.start_date)
                phrase = (
                    f'are scheduled for activation on {formatted_start_date}. '
                    f'A cluster access request will automatically be made for '
                    f'the requester then.')
            else:
                phrase = (
                    'have been activated. A cluster access request has '
                    'automatically been made for the requester.')
            message = f'Project {project.name} and its Allocation {phrase}'
            messages.success(self.request, message)
            self.logger.info(message)

        try:
            email_strategy.send_queued_emails()
        except Exception as e:
            pass

        return HttpResponseRedirect(self.redirect)

    def get_checklist(self):
        """Return a nested list, where each row contains the details of
        one item on the checklist.

        Each row is of the form: [task text, status name, latest update
        timestamp, is "Manage" button available, URL of "Manage"
        button.]"""
        pk = self.request_obj.pk
        state = self.request_obj.state
        checklist = []

        eligibility = state['eligibility']
        checklist.append([
            (f'Confirm that the requested PI is eligible for a new '
             f'{self.computing_allowance_obj.get_name()}.'),
            eligibility['status'],
            eligibility['timestamp'],
            True,
            reverse(
                'new-project-request-review-eligibility', kwargs={'pk': pk})
        ])
        is_eligible = eligibility['status'] == 'Approved'

        readiness = state['readiness']
        checklist.append([
            ('Confirm that the project satisfies the readiness status '
             'criteria.'),
            readiness['status'],
            readiness['timestamp'],
            True,
            reverse(
                'new-project-request-review-readiness', kwargs={'pk': pk})
        ])
        is_ready = readiness['status'] == 'Approved'

        mou_required = \
            self.computing_allowance_obj.requires_memorandum_of_understanding()
        if mou_required:
            notified = state['notified']
            task_text = (
                'Confirm or edit allowance details, and '
                'enable/notify the PI to sign the Memorandum of Understanding.')
            checklist.append([
                task_text,
                notified['status'],
                notified['timestamp'],
                is_eligible and is_ready,
                reverse('new-project-request-notify-pi',
                        kwargs={'pk': pk})
            ])
            is_notified = notified['status'] == 'Complete'

            memorandum_signed = state['memorandum_signed']
            task_text = (
                'Confirm that the Memorandum of Understanding has been '
                'signed.')
            if (self.computing_allowance_obj.is_recharge() and
                    self.computing_allowance_obj.requires_extra_information()):
                task_text += (
                    ' Additionally, confirm that funds have been transferred.')
            checklist.append([
                task_text,
                memorandum_signed['status'],
                memorandum_signed['timestamp'],
                is_eligible and is_ready and is_notified,
                reverse(
                    'new-project-request-review-memorandum-signed',
                    kwargs={'pk': pk})
            ])
        is_notified = not mou_required or (state['notified']['status'] == 'Complete')
        is_memorandum_signed = (
            not mou_required or
            state['memorandum_signed']['status'] == 'Complete')

        setup = state['setup']
        checklist.append([
            'Perform project setup on the cluster.',
            self.get_setup_status(),
            setup['timestamp'],
            is_eligible and is_ready and is_notified and is_memorandum_signed,
            reverse('new-project-request-review-setup', kwargs={'pk': pk})
        ])

        return checklist

    def get_setup_status(self):
        """Return one of the following statuses for the 'setup' step of
        the request: 'N/A', 'Pending', 'Complete'."""
        state = self.request_obj.state
        if (state['eligibility']['status'] == 'Denied' or
                state['readiness']['status'] == 'Denied'):
            return 'N/A'
        else:
            pending = 'Pending'
            if self.computing_allowance_obj.\
                    requires_memorandum_of_understanding():
                if state['memorandum_signed']['status'] == pending:
                    return pending
        return state['setup']['status']

    def has_request_allocation_period_started(self):
        """Return whether the request's AllocationPeriod has started. If
        the request has no period, return True."""
        allocation_period = self.request_obj.allocation_period
        if not allocation_period:
            return True
        return allocation_period.start_date <= display_time_zone_current_date()

    def is_checklist_complete(self):
        status_choice = savio_request_state_status(self.request_obj)
        return (status_choice.name == 'Approved - Processing' and
                self.request_obj.state['setup']['status'] == 'Complete')


class SavioProjectReviewEligibilityView(LoginRequiredMixin,
                                        UserPassesTestMixin,
                                        SavioProjectRequestMixin, FormView):
    form_class = ReviewStatusForm
    template_name = (
        'project/project_request/savio/project_review_eligibility.html')

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_attributes(pk)
        redirect = self.redirect_if_disallowed_status(request)
        if redirect is not None:
            return redirect
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data['status']
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state['eligibility'] = {
            'status': status,
            'justification': justification,
            'timestamp': timestamp,
        }
        self.request_obj.status = savio_request_state_status(self.request_obj)

        if status == 'Denied':
            runner = ProjectDenialRunner(self.request_obj)
            runner.run()

        self.request_obj.save()

        message = (
            f'Eligibility status for request {self.request_obj.pk} has been '
            f'set to {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.set_common_context_data(context)
        context['is_allowance_one_per_pi'] = \
            self.computing_allowance_obj.is_one_per_pi()
        return context

    def get_initial(self):
        initial = super().get_initial()
        eligibility = self.request_obj.state['eligibility']
        initial['status'] = eligibility['status']
        initial['justification'] = eligibility['justification']
        return initial

    def get_success_url(self):
        return reverse(
            'new-project-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class SavioProjectReviewReadinessView(LoginRequiredMixin, UserPassesTestMixin,
                                      SavioProjectRequestMixin, FormView):
    form_class = ReviewStatusForm
    template_name = (
        'project/project_request/savio/project_review_readiness.html')

    logger = logging.getLogger(__name__)

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_attributes(pk)
        redirect = self.redirect_if_disallowed_status(request)
        if redirect is not None:
            return redirect
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data['status']
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state['readiness'] = {
            'status': status,
            'justification': justification,
            'timestamp': timestamp,
        }
        self.request_obj.status = savio_request_state_status(self.request_obj)

        if status == 'Approved':
            if self.request_obj.pool:
                try:
                    send_project_request_pooling_email(self.request_obj)
                except Exception as e:
                    self.logger.error(
                        'Failed to send notification email. Details:\n')
                    self.logger.exception(e)
        elif status == 'Denied':
            runner = ProjectDenialRunner(self.request_obj)
            runner.run()

        self.request_obj.save()

        message = (
            f'Readiness status for request {self.request_obj.pk} has been set '
            f'to {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.set_common_context_data(context)
        return context

    def get_initial(self):
        initial = super().get_initial()
        readiness = self.request_obj.state['readiness']
        initial['status'] = readiness['status']
        initial['justification'] = readiness['justification']
        return initial

    def get_success_url(self):
        return reverse(
            'new-project-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class SavioProjectReviewMemorandumSignedView(LoginRequiredMixin,
                                             UserPassesTestMixin,
                                             SavioProjectRequestMixin,
                                             FormView):
    form_class = MemorandumSignedForm
    template_name = (
        'project/project_request/savio/project_review_memorandum_signed.html')

    logger = logging.getLogger(__name__)

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_attributes(pk)
        if not self.computing_allowance_obj.\
                requires_memorandum_of_understanding():
            message = (
                'A memorandum of understanding does not need to be signed for '
                'this request.')
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('new-project-request-detail', kwargs={'pk': pk}))
        redirect = self.redirect_if_disallowed_status(request)
        if redirect is not None:
            return redirect
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data['status']
        timestamp = utc_now_offset_aware().isoformat()

        self.request_obj.state['memorandum_signed'] = {
            'status': status,
            'timestamp': timestamp,
        }

        self.request_obj.status = savio_request_state_status(self.request_obj)
        self.request_obj.save()

        message = (
            f'Memorandum Signed status for request {self.request_obj.pk} has '
            f'been set to {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.set_common_context_data(context)
        return context

    def get_initial(self):
        initial = super().get_initial()
        memorandum_signed = self.request_obj.state['memorandum_signed']
        initial['status'] = memorandum_signed['status']
        return initial

    def get_success_url(self):
        return reverse(
            'new-project-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class SavioProjectReviewSetupView(LoginRequiredMixin, UserPassesTestMixin,
                                  SavioProjectRequestMixin, FormView):
    form_class = SavioProjectReviewSetupForm
    template_name = 'project/project_request/savio/project_review_setup.html'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_attributes(pk)
        redirect = self.redirect_if_disallowed_status(request)
        if redirect is not None:
            return redirect
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data['status']
        requested_name = (
            self.request_obj.state['setup']['name_change']['requested_name'])
        final_name = form_data['final_name']
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()

        name_change = {
            'requested_name': requested_name,
            'final_name': final_name,
            'justification': justification,
        }
        self.request_obj.state['setup'] = {
            'status': status,
            'name_change': name_change,
            'timestamp': timestamp,
        }

        # Set the Project's name. This is the only modification performed prior
        # to the final submission because the name must be unique.
        self.request_obj.project.name = final_name
        self.request_obj.project.save()

        self.request_obj.status = savio_request_state_status(self.request_obj)

        self.request_obj.save()

        message = (
            f'Setup status for request {self.request_obj.pk} has been set to '
            f'{status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.set_common_context_data(context)
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project_pk'] = self.request_obj.project.pk
        kwargs['requested_name'] = (
            self.request_obj.state['setup']['name_change']['requested_name'])
        kwargs['computing_allowance'] = self.request_obj.computing_allowance
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        setup = self.request_obj.state['setup']
        initial['status'] = setup['status']
        initial['final_name'] = setup['name_change']['final_name']
        initial['justification'] = setup['name_change']['justification']
        return initial

    def get_success_url(self):
        return reverse(
            'new-project-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class SavioProjectReviewDenyView(LoginRequiredMixin, UserPassesTestMixin,
                                 SavioProjectRequestMixin, FormView):
    form_class = ReviewDenyForm
    template_name = (
        'project/project_request/savio/project_review_deny.html')

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_attributes(pk)
        redirect = self.redirect_if_disallowed_status(request)
        if redirect is not None:
            return redirect
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state['other'] = {
            'justification': justification,
            'timestamp': timestamp,
        }
        self.request_obj.status = savio_request_state_status(self.request_obj)

        runner = ProjectDenialRunner(self.request_obj)
        runner.run()

        self.request_obj.save()

        message = (
            f'Status for {self.request_obj.pk} has been set to '
            f'{self.request_obj.status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.set_common_context_data(context)
        return context

    def get_initial(self):
        initial = super().get_initial()
        other = self.request_obj.state['other']
        initial['justification'] = other['justification']
        return initial

    def get_success_url(self):
        return reverse(
            'new-project-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class SavioProjectUndenyRequestView(LoginRequiredMixin, UserPassesTestMixin,
                                    SavioProjectRequestMixin, View):

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        message = (
            'You do not have permission to undeny a project request.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_attributes(pk)

        disallowed_status_names = list(
            ProjectAllocationRequestStatusChoice.objects.filter(
                ~Q(name='Denied')).values_list('name', flat=True))
        redirect = self.redirect_if_disallowed_status(
            request, disallowed_status_names=disallowed_status_names)
        if redirect is not None:
            return redirect

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        state = self.request_obj.state

        eligibility = state['eligibility']
        if eligibility['status'] == 'Denied':
            eligibility['status'] = 'Pending'

        readiness = state['readiness']
        if readiness['status'] == 'Denied':
            readiness['status'] = 'Pending'

        other = state['other']
        if other['timestamp']:
            other['justification'] = ''
            other['timestamp'] = ''

        self.request_obj.status = savio_request_state_status(self.request_obj)
        self.request_obj.save()

        message = (
            f'Project request {self.request_obj.project.name} has been '
            f'un-denied and will need to be reviewed again.')
        messages.success(request, message)

        return HttpResponseRedirect(
            reverse(
                'new-project-request-detail',
                kwargs={'pk': kwargs.get('pk')}))


# =============================================================================
# BRC: VECTOR
# =============================================================================

class VectorProjectRequestListView(LoginRequiredMixin, TemplateView):
    template_name = 'project/project_request/vector/project_request_list.html'
    # Show completed requests if True; else, show pending requests.
    completed = False

    def get_queryset(self):
        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            if direction == 'asc':
                direction = ''
            else:
                direction = '-'
            order_by = direction + order_by
        else:
            order_by = '-modified'
        return VectorProjectAllocationRequest.objects.order_by(order_by)

    def get_context_data(self, **kwargs):
        """Include either pending or completed requests. If the user is
        a superuser, show all such requests. Otherwise, show only those
        for which the user is a requester or PI."""
        context = super().get_context_data(**kwargs)

        args, kwargs = [], {}

        user = self.request.user

        request_list = self.get_queryset()
        permission = 'project.view_vectorprojectallocationrequest'
        if not (user.is_superuser or user.has_perm(permission)):
            args.append(Q(requester=user) | Q(pi=user))
        if self.completed:
            status__name__in = ['Approved - Complete', 'Denied']
        else:
            status__name__in = ['Under Review', 'Approved - Processing']
        kwargs['status__name__in'] = status__name__in
        context['vector_project_request_list'] = request_list.filter(
            *args, **kwargs)
        context['request_filter'] = (
            'completed' if self.completed else 'pending')

        return context


class VectorProjectRequestMixin(object):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_obj = None

    def redirect_if_disallowed_status(self, http_request,
                                      disallowed_status_names=(
            'Approved - Complete', 'Denied')):
        """Return a redirect response to the detail view for this
        project request if its status has one of the given disallowed
        names, after sending a message to the user. Otherwise, return
        None."""
        if not isinstance(self.request_obj, VectorProjectAllocationRequest):
            raise TypeError(
                f'Request object has unexpected type '
                f'{type(self.request_obj)}.')
        status_name = self.request_obj.status.name
        if status_name in disallowed_status_names:
            message = (
                f'You cannot perform this action on a request with status '
                f'{status_name}.')
            messages.error(http_request, message)
            return HttpResponseRedirect(
                self.request_detail_url(self.request_obj.pk))
        return None

    @staticmethod
    def request_detail_url(pk):
        """Return the URL to the detail view for the request with the
        given primary key."""
        return reverse('vector-project-request-detail', kwargs={'pk': pk})

    def set_attributes(self, pk):
        """Set this instance's request_obj to be the
        VectorProjectAllocationRequest with the given primary key."""
        self.request_obj = get_object_or_404(
            VectorProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)


class VectorProjectRequestDetailView(LoginRequiredMixin, UserPassesTestMixin,
                                     VectorProjectRequestMixin, DetailView):
    model = VectorProjectAllocationRequest
    template_name = (
        'project/project_request/vector/project_request_detail.html')
    context_object_name = 'vector_request'

    logger = logging.getLogger(__name__)

    error_message = 'Unexpected failure. Please contact an administrator.'

    redirect = reverse_lazy('vector-project-pending-request-list')

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        permission = 'project.view_vectorprojectallocationrequest'
        if self.request.user.has_perm(permission):
            return True

        if (self.request.user == self.request_obj.requester or
                self.request.user == self.request_obj.pi):
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_attributes(pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            latest_update_timestamp = \
                self.request_obj.latest_update_timestamp()
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
            messages.error(self.request, self.error_message)
            latest_update_timestamp = 'Failed to determine timestamp.'
        context['latest_update_timestamp'] = latest_update_timestamp

        if self.request_obj.status.name == 'Denied':
            try:
                denial_reason = self.request_obj.denial_reason()
                category = denial_reason.category
                justification = denial_reason.justification
                timestamp = denial_reason.timestamp
            except Exception as e:
                self.logger.exception(e)
                messages.error(self.request, self.error_message)
                category = 'Unknown Category'
                justification = (
                    'Failed to determine denial reason. Please contact an '
                    'administrator.')
                timestamp = 'Unknown Timestamp'
            context['denial_reason'] = {
                'category': category,
                'justification': justification,
                'timestamp': timestamp,
            }
            context['support_email'] = settings.CENTER_HELP_EMAIL

        context['is_checklist_complete'] = self.is_checklist_complete()

        context['is_allowed_to_manage_request'] = (
            self.request.user.is_superuser)

        return context

    def post(self, request, *args, **kwargs):
        if not self.request.user.is_superuser:
            message = 'You do not have permission to view the this page.'
            messages.error(request, message)
            pk = self.request_obj.pk

            return HttpResponseRedirect(
                reverse('vector-project-request-detail', kwargs={'pk': pk}))

        if not self.is_checklist_complete():
            message = 'Please complete the checklist before final activation.'
            messages.error(request, message)
            pk = self.request_obj.pk
            return HttpResponseRedirect(
                reverse('vector-project-request-detail', kwargs={'pk': pk}))

        runner = None
        try:
            runner = VectorProjectProcessingRunner(self.request_obj)
            project, allocation = runner.run()
        except Exception as e:
            self.logger.exception(e)
            messages.error(self.request, self.error_message)
        else:
            message = (
                f'Project {project.name} and Allocation {allocation.pk} have '
                f'been activated. A cluster access request has automatically '
                f'been made for the requester.')
            messages.success(self.request, message)

        # Send any messages from the runner back to the user.
        if isinstance(runner, VectorProjectProcessingRunner):
            try:
                for message in runner.get_user_messages():
                    messages.info(self.request, message)
            except NameError:
                pass

        return HttpResponseRedirect(self.redirect)

    def is_checklist_complete(self):
        status_choice = vector_request_state_status(self.request_obj)
        return (status_choice.name == 'Approved - Processing' and
                self.request_obj.state['setup']['status'] == 'Complete')


class VectorProjectReviewEligibilityView(LoginRequiredMixin,
                                         UserPassesTestMixin,
                                         VectorProjectRequestMixin, FormView):
    form_class = ReviewStatusForm
    template_name = (
        'project/project_request/vector/project_review_eligibility.html')

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_attributes(pk)
        redirect = self.redirect_if_disallowed_status(request)
        if redirect is not None:
            return redirect
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data['status']
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state['eligibility'] = {
            'status': status,
            'justification': justification,
            'timestamp': timestamp,
        }
        self.request_obj.status = vector_request_state_status(self.request_obj)

        if status == 'Denied':
            runner = ProjectDenialRunner(self.request_obj)
            runner.run()

        self.request_obj.save()

        message = (
            f'Eligibility status for request {self.request_obj.pk} has been '
            f'set to {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vector_request'] = self.request_obj
        return context

    def get_initial(self):
        initial = super().get_initial()
        eligibility = self.request_obj.state['eligibility']
        initial['status'] = eligibility['status']
        initial['justification'] = eligibility['justification']
        return initial

    def get_success_url(self):
        return reverse(
            'vector-project-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class VectorProjectReviewSetupView(LoginRequiredMixin, UserPassesTestMixin,
                                   VectorProjectRequestMixin, FormView):
    form_class = VectorProjectReviewSetupForm
    template_name = 'project/project_request/vector/project_review_setup.html'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_attributes(pk)
        redirect = self.redirect_if_disallowed_status(request)
        if redirect is not None:
            return redirect
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data['status']
        requested_name = (
            self.request_obj.state['setup']['name_change']['requested_name'])
        final_name = form_data['final_name']
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()

        name_change = {
            'requested_name': requested_name,
            'final_name': final_name,
            'justification': justification,
        }
        self.request_obj.state['setup'] = {
            'status': status,
            'name_change': name_change,
            'timestamp': timestamp,
        }

        # Set the Project's name. This is the only modification performed prior
        # to the final submission because the name must be unique.
        self.request_obj.project.name = final_name
        self.request_obj.project.save()

        self.request_obj.status = vector_request_state_status(self.request_obj)

        self.request_obj.save()

        message = (
            f'Setup status for request {self.request_obj.pk} has been set to '
            f'{status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vector_request'] = self.request_obj
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project_pk'] = self.request_obj.project.pk
        kwargs['requested_name'] = (
            self.request_obj.state['setup']['name_change']['requested_name'])
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        setup = self.request_obj.state['setup']
        initial['status'] = setup['status']
        initial['final_name'] = setup['name_change']['final_name']
        initial['justification'] = setup['name_change']['justification']
        return initial

    def get_success_url(self):
        return reverse(
            'vector-project-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class VectorProjectUndenyRequestView(LoginRequiredMixin, UserPassesTestMixin,
                                     VectorProjectRequestMixin, View):

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        message = (
            'You do not have permission to undeny a project request.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_attributes(pk)

        disallowed_status_names = list(
            ProjectAllocationRequestStatusChoice.objects.filter(
                ~Q(name='Denied')).values_list('name', flat=True))
        redirect = self.redirect_if_disallowed_status(
            request, disallowed_status_names=disallowed_status_names)
        if redirect is not None:
            return redirect

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        state = self.request_obj.state

        eligibility = state['eligibility']
        if eligibility['status'] == 'Denied':
            eligibility['status'] = 'Pending'

        self.request_obj.status = vector_request_state_status(self.request_obj)
        self.request_obj.save()

        message = (
            f'Project request {self.request_obj.project.name} has been '
            f'un-denied and will need to be reviewed again.')
        messages.success(request, message)

        return HttpResponseRedirect(
            reverse(
                'vector-project-request-detail',
                kwargs={'pk': kwargs.get('pk')}))
