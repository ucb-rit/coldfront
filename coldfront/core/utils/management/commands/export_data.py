import csv
import json
import datetime
from sys import stdout, stderr

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Value, F, CharField, Func, \
    DurationField, ExpressionWrapper

from coldfront.core.allocation.models import AllocationAttributeType, \
    AllocationUserAttribute, AllocationRenewalRequest, AllocationPeriod
from coldfront.core.statistics.models import Job
from coldfront.core.project.models import Project, ProjectStatusChoice, \
    SavioProjectAllocationRequest, VectorProjectAllocationRequest
from django.contrib.auth.models import User
from coldfront.core.project.forms_.renewal_forms.request_forms import DeprecatedProjectRenewalSurveyForm
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.common import display_time_zone_date_to_utc_datetime

from django import forms
from flags.state import flag_enabled

"""An admin command that exports the results of useful database queries
in user-friendly formats."""


class Command(BaseCommand):

    help = 'Exports data based on the requested query.'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.computing_allowance_interface = ComputingAllowanceInterface()
        self.allowance_prefixes = []
        for allowance in self.computing_allowance_interface.allowances():
            self.allowance_prefixes.append(
                self.computing_allowance_interface.code_from_name(
                    allowance.name))
        self.allocation_periods = [period for period in AllocationPeriod.objects.values_list('name', flat=True)]

    def add_arguments(self, parser):
        """Define subcommands with different functions."""
        subparsers = parser.add_subparsers(
            dest='subcommand',
            help='The subcommand to run.',
            title='subcommands')
        subparsers.required = True
        self.add_subparsers(subparsers)

    def add_subparsers(self, subparsers):
        """Add subcommands and their respective parsers."""
        latest_jobs_by_user_parser = \
            subparsers.add_parser('latest_jobs_by_user',
                                  help='Export list of users and their latest '
                                       'job if they have submitted a job since '
                                       'a given date.')
        latest_jobs_by_user_parser.add_argument(
            '--format',
            choices=['csv', 'json'],
            required=True,
            help='Export results in the given format.',
            type=str)
        latest_jobs_by_user_parser.add_argument(
            '--start_date',
            help='Date since users last submitted a job. '
                 'Must take the form of "MM-DD-YYYY".',
            type=valid_date)

        new_cluster_accounts_parser = \
            subparsers.add_parser('new_cluster_accounts',
                                  help='Export list of new user accounts '
                                       'created since a given date.')
        new_cluster_accounts_parser.add_argument(
            '--format',
            choices=['csv', 'json'],
            required=True,
            help='Export results in the given format.',
            type=str)
        new_cluster_accounts_parser.add_argument(
            '--start_date',
            help='Date that users last created an account. '
                 'Must take the form of "MM-DD-YYYY".',
            type=valid_date)

        job_avg_queue_time_parser = \
            subparsers.add_parser('job_avg_queue_time',
                                  help='Export average queue time for jobs '
                                       'between the given dates.')
        job_avg_queue_time_parser.add_argument(
            '--start_date',
            help='Starting date for jobs. '
                 'Must take the form of "MM-DD-YYYY".',
            type=valid_date)
        job_avg_queue_time_parser.add_argument(
            '--end_date',
            help='Ending date for jobs. '
                 'Must take the form of "MM-DD-YYYY".',
            type=valid_date)
        job_avg_queue_time_parser.add_argument(
            '--allowance_type',
            choices=self.allowance_prefixes,
            help='Filter projects by the given allowance type.',
            type=str)
        job_avg_queue_time_parser.add_argument(
            '--partition',
            help='Filter jobs by the partition they requested.',
            type=str)

        user_subparser = subparsers.add_parser(
            'users', help='Export user data.')
        user_subparser.add_argument(
            '--format',
            choices=['csv', 'json'],
            required=True,
            help='Export results in the given format.',
            type=str)
        user_subparser.add_argument(
            '--pi_only',
            help='Only return PI users.',
            action='store_true')

        project_subparser = subparsers.add_parser('projects',
                                                  help='Export projects data')
        project_subparser.add_argument('--allowance_type',
                                       choices=self.allowance_prefixes,
                                       help='Filter projects by the given allowance type.',
                                       type=str)
        project_subparser.add_argument('--format',
                                       choices=['csv', 'json'],
                                       required=True,
                                       help='Export results in the given format.',
                                       type=str)
        project_subparser.add_argument('--active_only', action='store_true')

        new_project_requests_subparser = subparsers.\
            add_parser('new_project_requests', help='Export new project requests')
        new_project_requests_subparser.add_argument('--type',
                                                    choices=['vector', 'savio'],
                                                    required=True,
                                                    help='Filter based on allocation type',
                                                    type=str)
        new_project_requests_subparser.add_argument('--start_date',
                                                    help='Get Requests from this date.'
                                                    'Must take the form of "MM-DD-YYYY".',
                                                    type=valid_date)
        new_project_requests_subparser.add_argument('--format',
                                                    choices=['csv', 'json'],
                                                    required=True,
                                                    help='Export results in the given format.',
                                                    type=str)

        new_project_survey_responses_subparser = subparsers.add_parser('new_project_survey_responses',
                                                           help='Export survey responses for new projects')
        new_project_survey_responses_subparser.add_argument('--format', help='Format to dump new project survey responses in',
                                                type=str, required=True, choices=['json', 'csv'])
        new_project_survey_responses_subparser.add_argument('--allowance_type',
                                                help='Dump responses for Projects with given prefix',
                                                type=str, required=False, default='',
                                                choices=self.allowance_prefixes)
        
        renewal_survey_responses_subparser = subparsers.add_parser('renewal_survey_responses',
                                                           help='Export survey responses for project renewals')
        renewal_survey_responses_subparser.add_argument('--format', help='Format to dump renewal survey responses in',
                                                type=str, required=True, choices=['json', 'csv'])
        renewal_survey_responses_subparser.add_argument('--allocation_period',
                                                help='Dump responses for Projects in given allocation period. i.e. \
                                                \'Allowance Year 2024 - 2025\'',
                                                type=str, required=True, default='',
                                                choices=self.allocation_periods)
        renewal_survey_responses_subparser.add_argument('--allowance_type',
                                                help='Dump responses for Projects with given prefix',
                                                type=str, required=False, default='',
                                                choices=self.allowance_prefixes)


    def handle(self, *args, **options):
        """Call the handler for the provided subcommand."""
        subcommand = options['subcommand']
        handler = getattr(self, f'handle_{subcommand}')
        handler(*args, **options)

    def handle_latest_jobs_by_user(self, *args, **options):
        """Handle the 'latest_jobs_by_user' subcommand."""
        date = options.get('start_date', None)
        format = options.get('format', None)
        output = options.get('stdout', stdout)
        error = options.get('stderr', stderr)
        fields = ['username', 'jobslurmid', 'submit_date']

        query_set = Job.objects.annotate(
            submit_date=Func(
                F('submitdate'),
                Value('MM-dd-yyyy HH24:mi:ss'),
                function='to_char',
                output_field=CharField()
            ),
            username=F('userid__username')
        )

        if date:
            date = display_time_zone_date_to_utc_datetime(date)
            query_set = query_set.filter(submitdate__gte=date)

        query_set = query_set.order_by('userid', '-submitdate').\
            distinct('userid')

        if format == 'csv':
            query_set = query_set.values_list(*fields)
            self.to_csv(query_set,
                        header=[*fields],
                        output=output,
                        error=error)

        else:
            query_set = query_set.values(*fields)
            self.to_json(query_set,
                         output=output,
                         error=error)

    def handle_new_cluster_accounts(self, *args, **options):
        """Handle the 'new_cluster_accounts' subcommand."""
        date = options.get('start_date', None)
        format = options.get('format', None)
        output = options.get('stdout', stdout)
        error = options.get('stderr', stderr)
        fields = ['username', 'date_created']

        cluster_account_status = AllocationAttributeType.objects.get(
            name='Cluster Account Status')

        query_set = AllocationUserAttribute.objects.filter(
            allocation_attribute_type=cluster_account_status,
            value='Active')

        query_set = query_set.annotate(
            date_created=Func(
                F('created'),
                Value('MM-dd-yyyy HH24:mi:ss'),
                function='to_char',
                output_field=CharField()
            ),
            username=F('allocation_user__user__username')
        )

        if date:
            date = display_time_zone_date_to_utc_datetime(date)
            query_set = query_set.filter(created__gte=date)

        query_set = query_set.order_by('username', '-created'). \
            distinct('username')

        if format == 'csv':
            query_set = query_set.values_list(*fields)
            self.to_csv(query_set,
                        header=[*fields],
                        output=output,
                        error=error)

        else:
            query_set = query_set.values(*fields)
            self.to_json(query_set,
                         output=output,
                         error=error)

    def handle_job_avg_queue_time(self, *args, **options):
        """Handle the 'job_avg_queue_time' subcommand."""
        start_date = options.get('start_date', None)
        end_date = options.get('end_date', None)
        allowance_type = options.get('allowance_type', None)
        partition = options.get('partition', None)

        if start_date and end_date and end_date < start_date:
            message = 'start_date must be before end_date.'
            raise CommandError(message)

        # only select jobs that have valid start and submit dates
        query_set = Job.objects.exclude(startdate=None, submitdate=None)

        query_set = query_set.annotate(queue_time=ExpressionWrapper(
            F('startdate') - F('submitdate'), output_field=DurationField()))

        if start_date:
            start_date = display_time_zone_date_to_utc_datetime(start_date)
            query_set = query_set.filter(submitdate__gte=start_date)

        if end_date:
            end_date = display_time_zone_date_to_utc_datetime(end_date)
            query_set = query_set.filter(submitdate__lte=end_date)

        if allowance_type:
            query_set = query_set.filter(accountid__name__startswith=allowance_type)

        if partition:
            message = 'Filtering on job partitions may take over a minute...'
            self.stdout.write(self.style.WARNING(message))

            # further reduce query_set size before splitting partition
            query_set = query_set.filter(partition__icontains=partition)
            ids = set()

            for job in query_set.iterator():
                if partition in job.partition.split(','):
                    ids.add(job.jobslurmid)
            query_set = query_set.filter(jobslurmid__in=ids)

        if query_set.count() == 0:
            message = 'No jobs found that satisfy the passed arguments'
            raise CommandError(message)

        message = 'Calculating average job queue time...'
        self.stdout.write(self.style.WARNING(message))
        query_set = query_set.values_list('queue_time', flat=True)
        avg_queue_time = sum(query_set, datetime.timedelta()) / query_set.count()

        total_seconds = int(avg_queue_time.total_seconds())
        hours, remainder = divmod(total_seconds, 60*60)
        minutes, seconds = divmod(remainder, 60)
        time_str = '{}hrs {}mins {}secs'.format(hours, minutes, seconds)

        self.stdout.write(self.style.SUCCESS(time_str))

    def handle_users(self, *args, **kwargs):

        def _get_department_fields_for_user(_user):
            """Return a list of two strs representing the given User's
            authoritative and non-authoritative departments. Each str is
            a semicolon-separated list of str representations of
            departments."""
            from coldfront.plugins.departments.utils.queries import get_departments_for_user

            authoritative_department_strs, non_authoritative_department_strs = \
                get_departments_for_user(_user, strs_only=True)
            authoritative_str = ';'.join(
                [s for s in authoritative_department_strs])
            non_authoritative_str = ';'.join(
                [s for s in non_authoritative_department_strs])
            return [authoritative_str, non_authoritative_str]

        _format = kwargs['format']
        pi_only = kwargs['pi_only']

        users = User.objects.order_by('pk')
        if pi_only:
            users = users.filter(userprofile__is_pi=True)

        include_departments = flag_enabled('USER_DEPARTMENTS_ENABLED')

        fields = [
            'id', 'username', 'first_name', 'last_name', 'email', 'is_active']

        all_user_data = []
        for user in users:
            user_data = [getattr(user, field) for field in fields]
            if include_departments:
                user_data.extend(_get_department_fields_for_user(user))
            all_user_data.append(user_data)

        if include_departments:
            department_fields = [
                'authoritative_departments', 'non_authoritative_departments']
            fields.extend(department_fields)

        if _format == 'csv':
            self.to_csv(
                all_user_data,
                header=fields,
                output=kwargs.get('stdout', stdout),
                error=kwargs.get('stderr', stderr))
        elif _format == 'json':
            json_objects = []
            for user_data in all_user_data:
                json_objects.append(dict(zip(fields, user_data)))
            self.to_json(
                json_objects,
                output=kwargs.get('stdout', stdout),
                error=kwargs.get('stderr', stderr))

    def handle_projects(self, *args, **kwargs):
        format = kwargs['format']
        active_only = kwargs['active_only']
        allowance_type = kwargs['allowance_type']
        projects = Project.objects.all()

        if allowance_type:
            projects = projects.filter(name__istartswith=allowance_type)

        if active_only:
            active_status = ProjectStatusChoice.objects.get(name='Active')
            projects = projects.filter(status=active_status)

        projects = projects.order_by('id')

        pi_table, manager_table, status_table = [], [], []
        for project in projects:
            pis = project.pis()
            table = [
                f'{pi.first_name} {pi.last_name} ({pi.email})' for pi in pis]
            if len(table) > 0:
                pi_table.append(table)
            else:
                pi_table.append(None)

            managers = project.managers()
            table = [
                f'{manager.first_name} {manager.last_name} ({manager.email})'
                for manager in managers]
            if len(table) > 0:
                manager_table.append(table)
            else:
                manager_table.append(None)

            status_table.append(str(project.status))

        header = ['id', 'created', 'modified', 'name', 'title', 'description']
        query_set_ = projects.values_list(*header)

        query_set = []
        for index, project in enumerate(query_set_):
            project = list(project)
            project.extend([status_table[index],
                            ';'.join(pi_table[index] or []),
                            ';'.join(manager_table[index] or [])])

            query_set.append(project)

        header.extend(['status', 'pis', 'manager'])
        if format == 'csv':
            self.to_csv(query_set,
                        header=header,
                        output=kwargs.get('stdout', stdout),
                        error=kwargs.get('stderr', stderr))

        elif format == 'json':
            query_set_ = query_set
            query_set = []

            for project in query_set_:
                project = dict(zip(header, project))
                query_set.append(project)

            self.to_json(query_set,
                         output=kwargs.get('stdout', stdout),
                         error=kwargs.get('stderr', stderr))

    def handle_new_project_requests(self, *args, **kwargs):
        format = kwargs['format']
        type = kwargs['type']
        date = kwargs.get('start_date', None)

        if type == 'savio':
            requests = SavioProjectAllocationRequest.objects.all()
            header = ['id', 'created', 'modified', 'allocation_type',
                      'survey_answers', 'state', 'pool', 'extra_fields']

        else:
            requests = VectorProjectAllocationRequest.objects.all()
            header = ['id', 'created', 'modified', 'state']

        if date:
            date = display_time_zone_date_to_utc_datetime(date)
            requests = requests.filter(created__gte=date)

        additional_headers = ['project', 'status', 'requester', 'pi']
        projects = [request.project.name for request in requests]
        statuses = [request.status.name for request in requests]

        requesters = []
        for request in requests:
            requesters.append(f'{request.requester.first_name} ' +
                              f'{request.requester.last_name} ' +
                              f'({request.requester.email})')

        pis = []
        for request in requests:
            pis.append(f'{request.pi.first_name} ' +
                       f'{request.pi.last_name} ' +
                       f'({request.pi.email})')

        query_set = []
        requests = requests.values_list(*header)
        for project, status, requester, pi, request in \
                zip(projects, statuses, requesters, pis, requests):
            request = list(request)
            request[1] = str(request[1])
            request[2] = str(request[2])

            request.extend([project, status, requester, pi])
            query_set.append(request)

        headers = header + additional_headers
        query_set = list(map(lambda query: dict(zip(headers, query)), query_set))

        if format == 'csv':
            query_set_ = [query.values() for query in query_set]

            self.to_csv(query_set_,
                        header=headers,
                        output=kwargs.get('stdout', stdout),
                        error=kwargs.get('stderr', stderr))

        elif format == 'json':
            self.to_json(query_set,
                         output=kwargs.get('stdout', stdout),
                         error=kwargs.get('stderr', stderr))

    def handle_new_project_survey_responses(self, *args, **kwargs):
        format = kwargs['format']
        allowance_type = kwargs['allowance_type']
        allocation_requests = SavioProjectAllocationRequest.objects.all()

        if allowance_type:
            allocation_requests = allocation_requests.filter(
                project__name__istartswith=allowance_type)

        _surveys = list(allocation_requests.values_list('survey_answers', flat=True))
        projects = Project.objects.filter(
            pk__in=allocation_requests.values_list('project', flat=True))
        surveys = []

        if format == 'csv':
            for project, survey in zip(projects, _surveys):
                surveys.append({
                    'project_name': project.name,
                    'project_title': project.title,
                    **survey
                })

            surveys = list(sorted(surveys, key=lambda x: x['project_name'], reverse=True))
            try:
                writer = csv.DictWriter(kwargs.get('stdout', stdout), surveys[0].keys())
                writer.writeheader()

                for survey in surveys:
                    writer.writerow(survey)

            except Exception as e:
                kwargs.get('stderr', stderr).write(str(e))

        elif format == 'json':
            for project, survey in zip(projects, _surveys):
                surveys.append({
                    'project_name': project.name,
                    'project_title': project.title,
                    'new_project_survey_responses': survey
                })

            surveys = list(sorted(surveys, key=lambda x: x['project_name'], reverse=True))
            self.to_json(surveys,
                         output=kwargs.get('stdout', stdout),
                         error=kwargs.get('stderr', stderr))
    
    def handle_renewal_survey_responses(self, *args, **kwargs):
        def _swap_form_answer_id_for_text(_survey, _multiple_choice_fields):
            '''
            Takes a survey, a dict mapping survey question IDs to answer IDs.
            Uses multiple_choice_fields to swap answer IDs for answer text, then 
            question IDs for question text.
            Returns the modified survey.

            Parameters
            ----------
            _survey : survey to modify
            _multiple_choice_fields : mapping of {question ID : {answer ID : answer text}}
            '''
            for question, answer in _survey.items():
                if question in _multiple_choice_fields.keys():
                    sub_map = _multiple_choice_fields[question]
                    if (isinstance(answer, list)):
                        # Multiple choice, array
                        _survey[question] = [sub_map.get(i,i) for i in answer]
                    elif answer != "":
                        # Single choice replacement 
                        _survey[question] = sub_map[answer]
            # Change keys of survey (question IDs) to be the human-readable text
            for id, text in form.fields.items():
                _survey[text.label] = _survey.pop(id)
            return _survey
        format = kwargs['format']
        allowance_type = kwargs['allowance_type']
        allocation_requests = AllocationRenewalRequest.objects.all()
        allocation_period = kwargs['allocation_period']


        if allowance_type:
            allocation_requests = allocation_requests.filter(
                post_project__name__istartswith=allowance_type)
            
        if allocation_period:
             allocation_requests = allocation_requests.filter(
                 allocation_period__name=allocation_period)

        _surveys = list(allocation_requests.values_list('renewal_survey_answers', flat=True))
        _surveys = [i for i in _surveys if i != {}]
        if len(_surveys) == 0:
            raise Exception("There are no valid renewal requests in the specified allocation period.")
        
        if {} in _surveys:
            raise Exception("This allocation period does not have an associated survey.")
        surveys = []
        # Create dict of multiple choice fields to replace field IDs with text. ID : text
        multiple_choice_fields = {}
        form = DeprecatedProjectRenewalSurveyForm()
        for k, v in form.fields.items():
            # Only ChoiceField or MultipleChoiceField (in this specific survey form) have choices 
            if (isinstance(v, forms.MultipleChoiceField)) or (isinstance(v, forms.ChoiceField)):
                multiple_choice_fields[k] = {_k: _v for _k, _v in form.fields[k].choices}

        if format == 'csv':
            for allocation_request, survey in zip(allocation_requests, _surveys):
                survey = _swap_form_answer_id_for_text(survey, multiple_choice_fields)
                surveys.append({
                    'project_name': allocation_request.post_project.name,
                    'project_title': allocation_request.post_project.title,
                    'project_pi': allocation_request.pi.username,
                    **survey
                })

            surveys = list(sorted(surveys, key=lambda x: x['project_name'], reverse=True))
            try:
                headers = {}
                for field in surveys[0].keys():
                    if field in form.fields:
                        headers[field] = form.fields[field].label
                    else:
                        headers[field] = field
                writer = csv.DictWriter(kwargs.get('stdout', stdout), headers, extrasaction="ignore")
                writer.writerow(headers)

                for survey in surveys:
                    writer.writerow(survey)

            except Exception as e:
                kwargs.get('stderr', stderr).write(str(e))

        elif format == 'json':
            for allocation_request, survey in zip(allocation_requests, _surveys):
                survey = _swap_form_answer_id_for_text(survey, multiple_choice_fields)
                surveys.append({
                    'project_name': allocation_request.post_project.name,
                    'project_title': allocation_request.post_project.title,
                    'project_pi': allocation_request.pi.username,
                    'renewal_survey_responses': survey
                })

            surveys = list(sorted(surveys, key=lambda x: x['project_name'], reverse=True))
            self.to_json(surveys,
                         output=kwargs.get('stdout', stdout),
                         error=kwargs.get('stderr', stderr))

    @staticmethod
    def to_csv(query_set, header=None, output=stdout, error=stderr):
        '''
        write query_set to output and give errors to error.
        does not manage the fds, only writes to them

        Parameters
        ----------
        query_set : QuerySet to write
        header: csv header to write
        output : output fd, defaults to stdout
        error : error fd, defaults to stderr
        '''

        if not query_set:
            error.write('Empty QuerySet')
            return

        try:
            writer = csv.writer(output)

            if header:
                writer.writerow(header)

            for x in query_set:
                writer.writerow(x)

        except Exception as e:
            error.write(str(e))

    @staticmethod
    def to_json(query_set, output=stdout, error=stderr):
        '''
        write query_set to output and give errors to error.
        does not manage the fds, only writes to them

        Parameters
        ----------
        query_set : QuerySet to write
        output : output fd, defaults to stdout
        error : error fd, defaults to stderr
        '''

        if not query_set:
            error.write('Empty QuerySet')
            return

        try:
            json_output = json.dumps(list(query_set), indent=4, default=str)
            output.writelines(json_output + '\n')
        except Exception as e:
            error.write(str(e))


def valid_date(s):
    try:
        return datetime.datetime.strptime(s, '%m-%d-%Y')
    except ValueError:
        msg = f'{s} is not a valid date. ' \
              f'Must take the form of "MM-DD-YYYY".'
        raise CommandError(msg)
