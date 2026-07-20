import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, TemplateView
from django.views.generic.edit import FormView
from flags.state import flag_enabled
import iso8601

from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.utils import calculate_service_units_to_allocate
from coldfront.core.project.forms import ReviewDenyForm, ReviewStatusForm
from coldfront.core.project.forms_.renewal_forms.approval_forms import (
    AllocationRenewalRequestSearchForm,
)
from coldfront.core.project.models import Project, ProjectAllocationRequestStatusChoice
from coldfront.core.project.utils_.renewal_survey import get_renewal_survey_response
from coldfront.core.project.utils_.renewal_utils import (
    AllocationRenewalApprovalRunner,
    AllocationRenewalDenialRunner,
    AllocationRenewalProcessingRunner,
    allocation_renewal_request_denial_reason,
    allocation_renewal_request_latest_update_timestamp,
    allocation_renewal_request_state_status,
    set_allocation_renewal_request_eligibility,
)
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import (
    ComputingAllowance,
)
from coldfront.core.utils.common import (
    display_time_zone_current_date,
    format_date_month_name_day_year,
    utc_now_offset_aware,
)
from coldfront.core.utils.email.email_strategy import (
    DropEmailStrategy,
    EnqueueEmailStrategy,
)
from coldfront.core.utils.mixins.views import ListFilterMixin

logger = logging.getLogger(__name__)


class AllocationRenewalRequestListView(
    LoginRequiredMixin, ListFilterMixin, TemplateView
):
    template_name = "project/project_renewal/project_renewal_request_list.html"

    PENDING_STATUSES = ["Under Review"]
    COMPLETED_STATUSES = ["Approved", "Complete", "Denied"]

    def get_queryset(self):
        return AllocationRenewalRequest.objects.select_related(
            "pi",
            "post_project",
            "status",
            "allocation_period",
        ).order_by(self.get_order_by(default="-request_time"))

    def get_context_data(self, **kwargs):
        """Include pending, completed, or all requests depending on the
        status GET parameter. Superusers and users with the
        view_allocationrenewalrequest permission (e.g. staff) see all
        requests and have access to the search form. All other users see only
        requests for which they are the requester or PI, with search
        hidden."""
        context = super().get_context_data(**kwargs)

        filter_args, filter_kwargs = [], {}

        request_list = self.get_queryset()
        user = self.request.user
        permission = "allocation.view_allocationrenewalrequest"
        if not (user.is_superuser or user.has_perm(permission)):
            filter_args.append(Q(requester=user) | Q(pi=user))

        status = self.request.GET.get("status", "pending")
        if status == "pending":
            filter_kwargs["status__name__in"] = self.PENDING_STATUSES
        elif status == "completed":
            filter_kwargs["status__name__in"] = self.COMPLETED_STATUSES
        request_list = request_list.filter(*filter_args, **filter_kwargs)

        show_search = user.is_superuser or user.has_perm(permission)
        context["show_search"] = show_search

        form_filter_parameters = ""
        if show_search:
            search_form = AllocationRenewalRequestSearchForm(
                self.request.GET, request_queryset=request_list
            )
            if search_form.is_valid():
                data = search_form.cleaned_data
                if data.get("project"):
                    request_list = request_list.filter(post_project=data["project"])
                if data.get("pi"):
                    request_list = request_list.filter(pi=data["pi"])
                if data.get("allocation_period"):
                    request_list = request_list.filter(
                        allocation_period=data["allocation_period"]
                    )
            form_filter_parameters = self.build_filter_parameters(
                search_form.cleaned_data if search_form.is_valid() else {}
            )
            context["renewal_search_form"] = search_form
            context["expand_accordion"] = "show" if form_filter_parameters else ""
        else:
            context["expand_accordion"] = ""

        filter_parameters = form_filter_parameters + f"status={status}&"
        order_by = self.request.GET.get("order_by", "request_time")
        direction = self.request.GET.get("direction", "des")
        context["filter_parameters"] = filter_parameters
        context["filter_parameters_with_order_by"] = (
            filter_parameters + f"order_by={order_by}&direction={direction}&"
        )
        context["form_filter_parameters"] = form_filter_parameters
        context["status"] = status

        page_obj = self.paginate(request_list, context)
        context["renewal_request_list"] = page_obj.object_list

        return context


class AllocationRenewalRequestMixin(object):
    allocation_period_obj = None
    request_obj = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context["allocation_amount"] = self.get_service_units_to_allocate()
        except Exception as e:
            logger.exception(e)
            messages.error(self.request, self.error_message)
            context["allocation_amount"] = "Failed to compute."
        if flag_enabled("RENEWAL_SURVEY_ENABLED"):
            try:
                context["survey_response"] = get_renewal_survey_response(
                    self.request_obj.allocation_period.name,
                    self.request_obj.post_project.name,
                    self.request_obj.pi.username,
                )
            except Exception as e:
                logger.exception(e)
                messages.error(self.request, self.error_message)
                context["survey_response"] = None
        context["has_survey_answers"] = bool(context.get("survey_response", None))
        return context

    @staticmethod
    def get_redirect_url(pk):
        return reverse("pi-allocation-renewal-request-detail", kwargs={"pk": pk})

    def get_service_units_to_allocate(self):
        """Return the number of service units to allocate to the
        project."""
        return calculate_service_units_to_allocate(
            self.computing_allowance_obj,
            self.request_obj.request_time,
            allocation_period=self.allocation_period_obj,
        )

    def set_common_context_data(self, context):
        """Given a dictionary of context variables to include in the
        template, add additional, commonly-used variables."""
        context["renewal_request"] = self.request_obj
        context["computing_allowance_name"] = self.computing_allowance_obj.get_name()

    def set_objs(self, pk):
        self.request_obj = get_object_or_404(
            AllocationRenewalRequest.objects.prefetch_related(
                "pi", "post_project", "pre_project", "requester"
            ),
            pk=pk,
        )
        self.allocation_period_obj = self.request_obj.allocation_period
        self.computing_allowance_obj = ComputingAllowance(
            self.request_obj.computing_allowance
        )


class AllocationRenewalRequestDetailView(
    LoginRequiredMixin, UserPassesTestMixin, AllocationRenewalRequestMixin, DetailView
):
    model = AllocationRenewalRequest
    template_name = "project/project_renewal/project_renewal_request_detail.html"

    error_message = "Unexpected failure. Please contact an administrator."
    request_obj = None

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        permission = "allocation.view_allocationrenewalrequest"
        if self.request.user.has_perm(permission):
            return True

        if (
            self.request.user == self.request_obj.requester
            or self.request.user == self.request_obj.pi
        ):
            return True
        message = "You do not have permission to view the previous page."
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        self.set_objs(pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.set_common_context_data(context)

        is_superuser = self.request.user.is_superuser

        try:
            latest_update_timestamp = (
                allocation_renewal_request_latest_update_timestamp(self.request_obj)
            )
            if not latest_update_timestamp:
                latest_update_timestamp = "No updates yet."
            else:
                latest_update_timestamp = iso8601.parse_date(latest_update_timestamp)
        except Exception as e:
            logger.exception(e)
            messages.error(self.request, self.error_message)
            latest_update_timestamp = "Failed to determine timestamp."
        context["latest_update_timestamp"] = latest_update_timestamp

        if self.request_obj.status.name == "Denied":
            try:
                denial_reason = allocation_renewal_request_denial_reason(
                    self.request_obj
                )
                category = denial_reason.category
                justification = denial_reason.justification
                timestamp = denial_reason.timestamp
            except Exception as e:
                logger.exception(e)
                messages.error(self.request, self.error_message)
                category = "Unknown Category"
                justification = (
                    "Failed to determine denial reason. Please contact an "
                    "administrator."
                )
                timestamp = "Unknown Timestamp"
            context["denial_reason"] = {
                "category": category,
                "justification": justification,
                "timestamp": timestamp,
            }
            context["support_email"] = settings.CENTER_HELP_EMAIL

        context["has_allocation_period_started"] = (
            self.__has_request_allocation_period_started()
        )
        context["is_allowed_to_manage_request"] = is_superuser
        if is_superuser:
            context["checklist"] = self.__get_checklist()
        context["is_checklist_complete"] = self.__is_checklist_complete()
        return context

    def post(self, request, *args, **kwargs):
        """Approve the request. Process it if its AllocationPeriod has
        already started."""
        pk = self.request_obj.pk
        if not request.user.is_superuser:
            message = "You do not have permission to POST to this page."
            messages.error(request, message)
            return HttpResponseRedirect(self.get_redirect_url(pk))
        if not self.__is_checklist_complete():
            message = "Please complete the checklist before final activation."
            messages.error(request, message)
            return HttpResponseRedirect(self.get_redirect_url(pk))

        email_strategy = EnqueueEmailStrategy()
        try:
            should_process_request = self.__has_request_allocation_period_started()
            num_service_units = self.get_service_units_to_allocate()

            with transaction.atomic():
                # Approve the request. If the request will be processed
                # immediately after, avoid sending an approval email.
                if should_process_request:
                    approval_email_strategy = DropEmailStrategy()
                else:
                    approval_email_strategy = email_strategy
                approval_runner = AllocationRenewalApprovalRunner(
                    self.request_obj,
                    num_service_units,
                    email_strategy=approval_email_strategy,
                )
                approval_runner.run()

                if should_process_request:
                    self.request_obj.refresh_from_db()
                    processing_runner = AllocationRenewalProcessingRunner(
                        self.request_obj,
                        num_service_units,
                        email_strategy=email_strategy,
                    )
                    processing_runner.run()
        except Exception as e:
            logger.exception(e)
            messages.error(self.request, self.error_message)
        else:
            if not should_process_request:
                formatted_start_date = format_date_month_name_day_year(
                    self.request_obj.allocation_period.start_date
                )
                phrase = f"is scheduled for renewal on {formatted_start_date}."
            else:
                phrase = "has been renewed."
            message = f"PI {self.request_obj.pi.username}'s allocation {phrase}"
            messages.success(self.request, message)
            logger.info(message)

        try:
            email_strategy.send_queued_emails()
        except Exception as e:
            pass

        return HttpResponseRedirect(
            reverse_lazy("pi-allocation-renewal-pending-request-list")
        )

    def __get_checklist(self):
        """Return a nested list, where each row contains the details of
        one item on the checklist.

        Each row is of the form: [task text, status name, latest update
        timestamp, is "Manage" button available, URL of "Manage"
        button]."""
        checklist = []
        new_project_request = self.request_obj.new_project_request
        if new_project_request:
            checklist.append(
                [
                    "Approve and process the new project request.",
                    new_project_request.status.name,
                    new_project_request.latest_update_timestamp(),
                    True,
                    reverse(
                        "new-project-request-detail",
                        kwargs={"pk": new_project_request.pk},
                    ),
                ]
            )
        else:
            eligibility = self.request_obj.state["eligibility"]
            checklist.append(
                [
                    (
                        f"Confirm that the requested PI is still eligible for a  "
                        f"{self.computing_allowance_obj.get_name()}."
                    ),
                    eligibility["status"],
                    eligibility["timestamp"],
                    True,
                    reverse(
                        "pi-allocation-renewal-request-review-eligibility",
                        kwargs={"pk": self.request_obj.pk},
                    ),
                ]
            )
        return checklist

    def __has_request_allocation_period_started(self):
        """Return whether the request's AllocationPeriod has started."""
        return (
            self.request_obj.allocation_period.start_date
            <= display_time_zone_current_date()
        )

    def __is_checklist_complete(self):
        """Return whether the request is ready for final submission."""
        new_project_request = self.request_obj.new_project_request
        if new_project_request:
            complete_status = ProjectAllocationRequestStatusChoice.objects.get(
                name="Approved - Complete"
            )
            if new_project_request.status != complete_status:
                return False
        else:
            eligibility = self.request_obj.state["eligibility"]
            if eligibility["status"] != "Approved":
                return False
        return True


class AllocationRenewalRequestReviewEligibilityView(
    LoginRequiredMixin, UserPassesTestMixin, AllocationRenewalRequestMixin, FormView
):
    form_class = ReviewStatusForm
    template_name = "project/project_renewal/review_eligibility.html"

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = "You do not have permission to view the previous page."
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        self.set_objs(pk)
        response_redirect = HttpResponseRedirect(self.get_redirect_url(pk))
        status_name = self.request_obj.status.name
        if status_name in ["Approved", "Complete", "Denied"]:
            message = f"You cannot review a request with status {status_name}."
            messages.error(request, message)
            return response_redirect
        if self.request_obj.new_project_request:
            message = (
                "This request involves creating a new project. Eligibility "
                "review must be handled in the associated project request."
            )
            messages.error(request, message)
            return response_redirect
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data["status"]
        justification = form_data["justification"]

        set_allocation_renewal_request_eligibility(
            self.request_obj, status, justification
        )

        if status == "Denied":
            runner = AllocationRenewalDenialRunner(self.request_obj)
            runner.run()

        message = (
            f"Eligibility status for request {self.request_obj.pk} has been "
            f"set to {status}."
        )
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.set_common_context_data(context)
        context["is_allowance_one_per_pi"] = (
            self.computing_allowance_obj.is_one_per_pi()
        )
        return context

    def get_initial(self):
        initial = super().get_initial()
        eligibility = self.request_obj.state["eligibility"]
        initial["status"] = eligibility["status"]
        initial["justification"] = eligibility["justification"]
        return initial

    def get_success_url(self):
        return self.get_redirect_url(self.kwargs.get("pk"))


class AllocationRenewalRequestReviewDenyView(
    LoginRequiredMixin, UserPassesTestMixin, AllocationRenewalRequestMixin, FormView
):
    form_class = ReviewDenyForm
    template_name = "project/project_renewal/review_deny.html"

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = "You do not have permission to view the previous page."
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        self.set_objs(pk)
        response_redirect = HttpResponseRedirect(self.get_redirect_url(pk))

        status_name = self.request_obj.status.name
        if status_name in ["Approved", "Complete", "Denied"]:
            message = f"You cannot review a request with status {status_name}."
            messages.error(request, message)
            return response_redirect

        new_project_request = self.request_obj.new_project_request
        if new_project_request:
            if new_project_request.status.name != "Denied":
                message = (
                    "Deny the associated Savio Project request first, which "
                    "should automatically deny this request."
                )
                messages.error(request, message)
                return response_redirect

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        justification = form_data["justification"]
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state["other"] = {
            "justification": justification,
            "timestamp": timestamp,
        }
        self.request_obj.status = allocation_renewal_request_state_status(
            self.request_obj
        )

        runner = AllocationRenewalDenialRunner(self.request_obj)
        runner.run()

        self.request_obj.save()

        message = (
            f"Status for {self.request_obj.pk} has been set to "
            f"{self.request_obj.status}."
        )
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.set_common_context_data(context)
        return context

    def get_initial(self):
        initial = super().get_initial()
        other = self.request_obj.state["other"]
        initial["justification"] = other["justification"]
        return initial

    def get_success_url(self):
        return self.get_redirect_url(self.kwargs.get("pk"))


# This is disabled because a PI may always make a new request.
# In addition, checks need to be done to ensure that a request cannot be
# un-denied if the PI has already renewed elsewhere.
# class AllocationRenewalRequestUndenyView(LoginRequiredMixin,
#                                          UserPassesTestMixin,
#                                          AllocationRenewalRequestMixin,
#                                          View):
#
#     def test_func(self):
#         """UserPassesTestMixin tests."""
#         if self.request.user.is_superuser:
#             return True
#         message = 'You do not have permission to view the previous page.'
#         messages.error(self.request, message)
#
#     def dispatch(self, request, *args, **kwargs):
#         pk = self.kwargs.get('pk')
#         self.set_objs(pk)
#         response_redirect = HttpResponseRedirect(self.get_redirect_url(pk))
#
#         status_name = self.request_obj.status.name
#         if status_name != 'Denied':
#             message = (
#                 f'You cannot un-deny a request with status '
#                 f'\'{status_name}\'.')
#             messages.error(request, message)
#             return response_redirect
#
#         new_project_request = self.request_obj.new_project_request
#         if new_project_request:
#             if new_project_request.status.name == 'Complete':
#                 message = (
#                     f'You cannot un-deny a request that has an associated '
#                     f'new project request with status \'Complete\'.')
#                 messages.error(request, message)
#                 return response_redirect
#
#         return super().dispatch(request, *args, **kwargs)
#
#     def get(self, request, *args, **kwargs):
#         message = 'Unsupported method.'
#         messages.error(request, message)
#         return HttpResponseRedirect(
#             self.get_redirect_url(self.request_obj.pk))
#
#     def post(self, request, *args, **kwargs):
#         request_obj = self.request_obj
#         response_redirect = HttpResponseRedirect(
#             self.get_redirect_url(request_obj.pk))
#
#         new_project_request = request_obj.new_project_request
#         if new_project_request:
#             if new_project_request.status == 'Denied':
#                 message = (
#                     'Un-deny the associated Savio Project request before '
#                     'un-denying this request.')
#                 messages.error(request, message)
#                 return response_redirect
#
#         eligibility = request_obj.state['eligibility']
#         if eligibility['status'] == 'Denied':
#             eligibility['status'] = 'Pending'
#
#         other = request_obj.state['other']
#         if other['timestamp']:
#             other['justification'] = ''
#             other['timestamp'] = ''
#
#         request_obj.status = allocation_renewal_request_state_status(
#             request_obj)
#         request_obj.save()
#
#         message = (
#             f'Status for {request_obj.pk} has been set to '
#             f'{request_obj.status}.')
#         messages.success(request, message)
#
#         return HttpResponseRedirect(self.get_redirect_url(request_obj.pk))
