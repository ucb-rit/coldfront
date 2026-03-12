import csv
import itertools
import json
import logging

from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import StreamingHttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import strip_tags
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from django.db import connection

from coldfront.core.project.models import Project, ProjectUser
from coldfront.core.statistics.models import Job, JobWaitHeatmap30d
from coldfront.core.statistics.forms import JobSearchForm
from coldfront.core.statistics.utils_.job_accessibility_manager import JobAccessibilityManager
from coldfront.core.statistics.utils_.job_query_filtering import job_query_filtering
from coldfront.core.statistics.utils_.job_query_filtering import JobSearchFilterSessionStorage
from coldfront.core.statistics.utils_.queue_wait_analytics import (
    CPU_BUCKET_ORDER,
    get_cpu_bucket_sql_case,
)
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

        job_list = context['job_list']
        paginator = Paginator(job_list, self.paginate_by)

        page = self.request.GET.get('page')

        try:
            job_list = paginator.page(page)
        except PageNotAnInteger:
            job_list = paginator.page(1)
        except EmptyPage:
            job_list = paginator.page(paginator.num_pages)

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

        if self.object_list.count() > 100000:
            context['total_service_units'] = 'Too many jobs to calculate'
        else:
            total_service_units = Decimal('0.00')
            for job in self.object_list.iterator():
                total_service_units += job.amount
            context['total_service_units'] = \
                total_service_units.quantize(Decimal('0.01'))

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


class AnalyticsView(LoginRequiredMixin, TemplateView):
    template_name = 'analytics_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Fetch latest heatmap data
        heatmap_data = JobWaitHeatmap30d.objects.all().order_by('partition', 'cpu_bucket')

        if not heatmap_data.exists():
            context['no_data'] = True
            return context

        # Get unique partitions and ensure bucket order
        partitions = sorted(set(row.partition for row in heatmap_data))

        # Build 2D data structure for heatmap: rows=partitions, cols=buckets
        # C3.js expects data in columnar format
        heatmap_matrix = {}
        sample_sizes = {}

        for row in heatmap_data:
            if row.partition not in heatmap_matrix:
                heatmap_matrix[row.partition] = {}
                sample_sizes[row.partition] = {}

            # Convert seconds to hours for display
            wait_hours = float(row.p50_wait_seconds) / 3600.0
            heatmap_matrix[row.partition][row.cpu_bucket] = wait_hours
            sample_sizes[row.partition][row.cpu_bucket] = row.sample_size

        # Fill missing cells with null
        for partition in partitions:
            for bucket in CPU_BUCKET_ORDER:
                if bucket not in heatmap_matrix[partition]:
                    heatmap_matrix[partition][bucket] = None

        # Compute cluster-wide median for context
        total_jobs = sum(row.sample_size for row in heatmap_data)

        # Get generation timestamp
        generated_at = heatmap_data.first().generated_at if heatmap_data else None

        context['partitions'] = partitions
        context['cpu_buckets'] = CPU_BUCKET_ORDER
        context['heatmap_matrix'] = json.dumps(heatmap_matrix)
        context['sample_sizes'] = json.dumps(sample_sizes)
        context['total_jobs'] = total_jobs
        context['generated_at'] = generated_at
        context['no_data'] = False

        return context


class ProjectAnalyticsView(LoginRequiredMixin, TemplateView):
    """
    Ad-hoc project-specific analytics view.

    URL: /analytics/project/<project_name>/?days=90

    Queries wait time statistics on-demand for a specific project
    and compares to cluster-wide stats.
    """
    template_name = 'project_analytics_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        project_name = self.kwargs.get('project_name')
        days = int(self.request.GET.get('days', 90))
        min_sample = 5  # Lower threshold for project-specific data

        # Verify project exists
        try:
            project = Project.objects.get(name=project_name)
        except Project.DoesNotExist:
            context['error'] = f"Project '{project_name}' not found"
            return context

        context['project'] = project
        context['days'] = days

        # Get project stats
        project_stats = self._get_wait_stats(project_name, days, min_sample)

        # Get cluster-wide stats for comparison
        cluster_stats = self._get_wait_stats(None, days, min_sample)

        if not project_stats:
            context['no_data'] = True
            context['message'] = f"No job data found for {project_name} in the last {days} days"
            return context

        # Build heat map data structures
        context['project_heatmap'] = self._build_heatmap_data(project_stats)
        context['cluster_heatmap'] = self._build_heatmap_data(cluster_stats)
        context['comparison_data'] = self._build_comparison_data(project_stats, cluster_stats)

        # Summary stats
        context['total_project_jobs'] = sum(s['jobs'] for s in project_stats)
        context['total_cluster_jobs'] = sum(s['jobs'] for s in cluster_stats)

        # QoS breakdown
        project_qos = set(s['qos'] or 'None' for s in project_stats)
        cluster_qos = set(s['qos'] or 'None' for s in cluster_stats)
        context['project_qos'] = sorted(project_qos)
        context['cluster_qos'] = sorted(cluster_qos)

        context['no_data'] = False

        return context

    def _get_wait_stats(self, project_name, days, min_sample):
        """Query wait time statistics, optionally filtered by project."""
        project_filter = ""
        params = {'days': days, 'min_sample': min_sample}

        if project_name:
            project_filter = "AND p.name = %(project_name)s"
            params['project_name'] = project_name

        sql = f"""
            WITH job_waits AS (
                SELECT
                    j.partition,
                    j.qos,
                    j.num_cpus,
                    {get_cpu_bucket_sql_case('j')} AS cpu_bucket,
                    EXTRACT(EPOCH FROM (j.startdate - j.submitdate)) AS wait_seconds
                FROM statistics_job j
                JOIN project_project p ON j.accountid_id = p.id
                WHERE j.startdate >= NOW() - INTERVAL '%(days)s days'
                    AND j.startdate IS NOT NULL
                    AND j.submitdate IS NOT NULL
                    {project_filter}
            )
            SELECT
                partition,
                qos,
                cpu_bucket,
                COUNT(*) as jobs,
                percentile_cont(0.5) WITHIN GROUP (ORDER BY wait_seconds) AS p50_seconds,
                percentile_cont(0.90) WITHIN GROUP (ORDER BY wait_seconds) AS p90_seconds,
                percentile_cont(0.99) WITHIN GROUP (ORDER BY wait_seconds) AS p99_seconds
            FROM job_waits
            GROUP BY partition, qos, cpu_bucket
            HAVING COUNT(*) >= %(min_sample)s
            ORDER BY partition, qos, cpu_bucket;
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return results

    def _build_heatmap_data(self, stats):
        """Build heatmap matrix structure for rendering."""
        partitions = sorted(set(s['partition'] for s in stats))
        qos_values = sorted(set(s['qos'] or 'None' for s in stats))

        # Group by partition, QoS, CPU bucket
        heatmap = {}

        for stat in stats:
            partition = stat['partition']
            qos = stat['qos'] or 'None'
            cpu_bucket = stat['cpu_bucket']

            key = f"{partition}|{qos}"
            if key not in heatmap:
                heatmap[key] = {}

            heatmap[key][cpu_bucket] = {
                'p50': stat['p50_seconds'] / 3600,  # Convert to hours
                'p90': stat['p90_seconds'] / 3600,
                'p99': stat['p99_seconds'] / 3600,
                'jobs': stat['jobs']
            }

        # Fill missing cells with None
        for partition in partitions:
            for qos in qos_values:
                key = f"{partition}|{qos}"
                if key not in heatmap:
                    heatmap[key] = {}
                for bucket in CPU_BUCKET_ORDER:
                    if bucket not in heatmap[key]:
                        heatmap[key][bucket] = None

        return {
            'partitions': partitions,
            'qos_values': qos_values,
            'matrix': json.dumps(heatmap),
            'cpu_buckets': CPU_BUCKET_ORDER
        }

    def _build_comparison_data(self, project_stats, cluster_stats):
        """Build comparison table data."""
        comparisons = []

        # Create lookup for cluster stats
        cluster_lookup = {}
        for stat in cluster_stats:
            key = (stat['partition'], stat['qos'] or 'None', stat['cpu_bucket'])
            cluster_lookup[key] = stat

        for pstat in project_stats:
            partition = pstat['partition']
            qos = pstat['qos'] or 'None'
            cpu_bucket = pstat['cpu_bucket']

            key = (partition, qos, cpu_bucket)
            cstat = cluster_lookup.get(key)

            comparison = {
                'partition': partition,
                'qos': qos,
                'cpu_bucket': cpu_bucket,
                'project_jobs': pstat['jobs'],
                'project_p50': pstat['p50_seconds'] / 3600,
                'project_p90': pstat['p90_seconds'] / 3600,
                'project_p99': pstat['p99_seconds'] / 3600,
            }

            if cstat:
                comparison['cluster_jobs'] = cstat['jobs']
                comparison['cluster_p50'] = cstat['p50_seconds'] / 3600
                comparison['cluster_p90'] = cstat['p90_seconds'] / 3600
                comparison['cluster_p99'] = cstat['p99_seconds'] / 3600

                # Calculate percentage difference
                if cstat['p50_seconds'] > 0:
                    comparison['p50_diff_pct'] = (
                        (pstat['p50_seconds'] - cstat['p50_seconds']) /
                        cstat['p50_seconds'] * 100
                    )
            else:
                comparison['cluster_jobs'] = 0
                comparison['cluster_p50'] = None
                comparison['cluster_p90'] = None
                comparison['cluster_p99'] = None
                comparison['p50_diff_pct'] = None

            comparisons.append(comparison)

        # Sort by partition, QoS, CPU bucket
        comparisons.sort(
            key=lambda x: (
                x['partition'],
                x['qos'],
                CPU_BUCKET_ORDER.index(x['cpu_bucket']) if x['cpu_bucket'] in CPU_BUCKET_ORDER else 999
            )
        )

        return comparisons
