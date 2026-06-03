import csv
import itertools
import logging

from decimal import Decimal
from django.contrib import messages
from django.db.models import Sum
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import StreamingHttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import strip_tags
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from coldfront.core.project.models import ProjectUser
from coldfront.core.statistics.models import Job
from coldfront.core.statistics.forms import JobSearchForm
from coldfront.core.statistics.utils_.job_accessibility_manager import JobAccessibilityManager
from coldfront.core.statistics.utils_.job_query_filtering import job_query_filtering
from coldfront.core.statistics.utils_.job_query_filtering import JobSearchFilterSessionStorage
from coldfront.core.utils.common import Echo


logger = logging.getLogger(__name__)


class SlurmJobListView(LoginRequiredMixin,
                       ListView):
    template_name = 'job_list.html'
    paginate_by = 30
    context_object_name = 'job_list'

    _FILTER_FIELDS = (
        'status', 'jobslurmid', 'project_name', 'username',
        'partition', 'submitdate_after', 'submitdate_before',
    )

    def get_queryset(self):
        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            direction = '' if direction == 'asc' else '-'
            order_by = direction + order_by
        else:
            order_by = '-submitdate'

        self._is_pi = ProjectUser.objects.filter(
            role__name__in=['Manager', 'Principal Investigator'],
            user=self.request.user).exists()
        job_search_form = JobSearchForm(
            self.request.GET,
            user=self.request.user,
            is_pi=self._is_pi)

        if job_search_form.is_valid():
            job_filters = job_search_form.cleaned_data

            session_storage = JobSearchFilterSessionStorage(self.request)
            session_storage.set(job_filters)

            show_all_jobs = job_filters.get('show_all_jobs', False)

            if show_all_jobs and not any(
                    job_filters.get(f) for f in self._FILTER_FIELDS):
                messages.warning(
                    self.request,
                    'Please provide at least one search filter '
                    'when viewing all jobs.')
                job_list = Job.objects.none()
            else:
                job_accessibility_manager = JobAccessibilityManager()
                accessible_jobs = (
                    job_accessibility_manager.get_jobs_accessible_to_user(
                        self.request.user,
                        include_global=show_all_jobs))
                job_list = job_query_filtering(
                    accessible_jobs, job_filters)

        else:
            job_list = Job.objects.none()

            for error in job_search_form.errors:
                messages.warning(self.request,
                                 strip_tags(job_search_form.errors[error]))

        return job_list.select_related(
            'userid', 'accountid').order_by(order_by)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        is_pi = getattr(self, '_is_pi', False)
        job_search_form = JobSearchForm(
            self.request.GET,
            user=self.request.user,
            is_pi=is_pi)

        if job_search_form.is_valid():
            context['job_search_form'] = job_search_form
            data = job_search_form.cleaned_data
            filter_parameters = ''
            for key, value in data.items():
                if value:
                    if isinstance(value, list):
                        for ele in value:
                            filter_parameters += '{}={}&'.format(key, ele)
                    else:
                        filter_parameters += '{}={}&'.format(key, value)
        else:
            filter_parameters = None
            context['job_search_form'] = JobSearchForm()

        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            filter_parameters_with_order_by = (
                filter_parameters
                + 'order_by=%s&direction=%s&' % (order_by, direction))
        else:
            filter_parameters_with_order_by = filter_parameters

        context['expand_accordion'] = 'show'
        context['filter_parameters'] = filter_parameters
        context['filter_parameters_with_order_by'] = (
            filter_parameters_with_order_by)

        context['status_danger_list'] = [
            'NODE_FAIL', 'CANCELLED', 'FAILED',
            'OUT_OF_MEMORY', 'TIMEOUT']
        context['status_warning_list'] = ['PREEMPTED', 'REQUEUED']

        context['can_view_all_jobs'] = (
            self.request.user.is_superuser
            or self.request.user.has_perm('statistics.view_job'))
        context['show_username'] = (
            context['can_view_all_jobs'] or is_pi)

        total_service_units = self.object_list.aggregate(
            total=Sum('amount'))['total'] or Decimal('0.00')
        context['total_service_units'] = (
            total_service_units.quantize(Decimal('0.01')))

        return context


class SlurmJobDetailView(LoginRequiredMixin,
                         UserPassesTestMixin,
                         DetailView):
    model = Job
    template_name = 'job_detail.html'
    context_object_name = 'job'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        job_obj = self.get_object()

        job_accessibility_manager = JobAccessibilityManager()
        is_job_accessible = job_accessibility_manager.can_user_access_job(
            self.request.user, job_obj)

        if not is_job_accessible:
            message = 'You do not have permission to view the previous page.'
            messages.error(self.request, message)

        return is_job_accessible

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        job_obj = self.get_object()
        context['job'] = job_obj

        context['status_danger_list'] = ['NODE_FAIL',
                                         'CANCELLED',
                                         'FAILED',
                                         'OUT_OF_MEMORY',
                                         'TIMEOUT']

        context['status_warning_list'] = ['PREEMPTED',
                                          'REQUEUED']

        context['nodes'] = ', '.join([x.name for x in job_obj.nodes.all()])

        return context


class ExportJobListView(LoginRequiredMixin,
                        UserPassesTestMixin,
                        View):

    MAX_JOBS_EXPORTABLE = 100000

    def test_func(self):
        """Allow access to all users.

        Access to specific jobs is determined by the dispatch method.
        """
        return True

    def dispatch(self, request, *args, **kwargs):
        session_storage = JobSearchFilterSessionStorage(request)
        job_filters = session_storage.get()

        show_all_jobs = job_filters.get('show_all_jobs', False)

        job_accessibility_manager = JobAccessibilityManager()
        accessible_jobs = job_accessibility_manager.get_jobs_accessible_to_user(
            self.request.user, include_global=show_all_jobs)

        if job_filters:
            filtered_jobs = job_query_filtering(accessible_jobs, job_filters)
        else:
            filtered_jobs = accessible_jobs

        num_jobs = filtered_jobs.count()
        if num_jobs > self.MAX_JOBS_EXPORTABLE:
            message = (
                f'Your search produced too many results to export. Please '
                f'limit your search to have fewer than '
                f'{self.MAX_JOBS_EXPORTABLE} results.')
            messages.error(request, message)
            return redirect(reverse('slurm-job-list'))

        return self._get_response(filtered_jobs)

    @staticmethod
    def _get_response(jobs):
        """Return a response that streams a CSV containing the requested
        jobs to an attachment named 'job_list.csv' to be downloaded."""
        header = (
            'jobslurmid', 'username', 'project_name', 'partition', 'jobstatus',
            'submitdate', 'startdate', 'enddate', 'service_units')
        job_fields = (
            'jobslurmid', 'userid__username', 'accountid__name', 'partition',
            'jobstatus', 'submitdate', 'startdate', 'enddate', 'amount')

        job_values_iterator = jobs.values_list(*job_fields).iterator()

        echo_buffer = Echo()
        writer = csv.writer(echo_buffer)
        rows = (
            writer.writerow(row)
            for row in itertools.chain([header], job_values_iterator))

        response = StreamingHttpResponse(rows, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="job_list.csv"'

        return response
