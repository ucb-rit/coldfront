import csv
import itertools
import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
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
            order_by = '-submitdate'

        is_pi = ProjectUser.objects.filter(
            role__name__in=['Manager', 'Principal Investigator'],
            user=self.request.user).exists()
        job_search_form = JobSearchForm(self.request.GET,
                                        user=self.request.user,
                                        is_pi=is_pi)

        if job_search_form.is_valid():
            job_filters = job_search_form.cleaned_data

            session_storage = JobSearchFilterSessionStorage(self.request)
            session_storage.set(job_filters)

            show_all_jobs = job_filters.get('show_all_jobs', False)

            job_accessibility_manager = JobAccessibilityManager()
            accessible_jobs = \
                job_accessibility_manager.get_jobs_accessible_to_user(
                    self.request.user, include_global=show_all_jobs)

            job_list = job_query_filtering(accessible_jobs, job_filters)

        else:
            job_list = Job.objects.none()

            for error in job_search_form.errors:
                messages.warning(self.request,
                                 strip_tags(job_search_form.errors[error]))

        return job_list.order_by(order_by)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        is_pi = ProjectUser.objects.filter(
            role__name__in=['Manager', 'Principal Investigator'],
            user=self.request.user).exists()
        job_search_form = JobSearchForm(self.request.GET,
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
            context['job_search_form'] = job_search_form
        else:
            filter_parameters = None
            context['job_search_form'] = JobSearchForm()

        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            filter_parameters_with_order_by = filter_parameters + \
                                              'order_by=%s&direction=%s&' % \
                                              (order_by, direction)
        else:
            filter_parameters_with_order_by = filter_parameters

        context['expand_accordion'] = 'show'

        context['filter_parameters'] = filter_parameters
        context['filter_parameters_with_order_by'] = filter_parameters_with_order_by

        context['inline_fields'] = ['submitdate', 'submit_modifier',
                                    'startdate', 'start_modifier',
                                    'enddate', 'end_modifier']

        context['status_danger_list'] = ['NODE_FAIL',
                                         'CANCELLED',
                                         'FAILED',
                                         'OUT_OF_MEMORY',
                                         'TIMEOUT']

        context['status_warning_list'] = ['PREEMPTED',
                                          'REQUEUED']

        context['can_view_all_jobs'] = \
            self.request.user.is_superuser or \
            self.request.user.has_perm('statistics.view_job')

        context['show_username'] = (self.request.user.is_superuser or self.request.user.has_perm('statistics.view_job')) or is_pi

        if self.object_list.count() < 100000:
            total_service_units = 0
            for job in self.object_list.iterator():
                total_service_units += job.amount
                if total_service_units > 1000000:
                    total_service_units = '1000000+'
                    break
            context['total_service_units'] = str(total_service_units)
        else:
            context['total_service_units'] = ''

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
