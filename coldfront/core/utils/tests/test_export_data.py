import datetime
import json
from decimal import Decimal

import sys
from csv import DictReader
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command, CommandError
from django.urls import reverse
from django import forms
from http import HTTPStatus

from coldfront.api.statistics.utils import get_accounting_allocation_objects, \
    create_project_allocation, create_user_project_allocation
from coldfront.core.allocation.models import AllocationAttributeType, \
    AllocationUserAttribute, AllocationRenewalRequest, AllocationPeriod, \
    AllocationRenewalRequestStatusChoice
from coldfront.core.statistics.models import Job
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.common import display_time_zone_date_to_utc_datetime
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import enable_deployment
from coldfront.core.utils.tests.test_base import TestBase
from coldfront.core.project.models import Project, ProjectStatusChoice, \
    ProjectUser, ProjectUserStatusChoice, ProjectUserRoleChoice, \
    ProjectAllocationRequestStatusChoice, SavioProjectAllocationRequest, \
    VectorProjectAllocationRequest
from coldfront.core.project.forms_.renewal_forms.request_forms import DeprecatedProjectRenewalSurveyForm
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface

DATE_FORMAT = '%m-%d-%Y %H:%M:%S'
ABR_DATE_FORMAT = '%m-%d-%Y'


class TestBaseExportData(TestBase):
    def setUp(self):
        """Setup test data"""
        super().setUp()

        # Create two Users.
        for i in range(2):
            user = User.objects.create(
                username=f'user{i}', email=f'user{i}@nonexistent.com')
            user_profile = UserProfile.objects.get(user=user)
            user_profile.cluster_uid = f'{i}'
            user_profile.save()
            setattr(self, f'user{i}', user)
            setattr(self, f'user_profile{i}', user_profile)

        # Create Projects and associate Users with them.
        project_status = ProjectStatusChoice.objects.get(name='Active')
        project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        user_role = ProjectUserRoleChoice.objects.get(name='User')

        # Create a Project and ProjectUsers.
        project = Project.objects.create(
            name='fc_project0', status=project_status)
        setattr(self, 'fc_project0', project)
        for j in range(2):
            ProjectUser.objects.create(
                user=getattr(self, f'user{j}'), project=project,
                role=user_role, status=project_user_status)

        # Create a compute allocation for the Project.
        allocation = Decimal('1000.00')
        create_project_allocation(project, allocation)

        # Create a compute allocation for each User on the Project.
        for j in range(2):
            create_user_project_allocation(
                getattr(self, f'user{j}'), project, allocation / 2)

        self.cluster_account_status = AllocationAttributeType.objects.get(
            name='Cluster Account Status')

        allocation_object = get_accounting_allocation_objects(self.fc_project0)
        for j, project_user in enumerate(project.projectuser_set.all()):
            if project_user.role.name != 'User':
                continue

            allocation_user_objects = get_accounting_allocation_objects(
                project, user=project_user.user)

            AllocationUserAttribute.objects.create(
                allocation_attribute_type=self.cluster_account_status,
                allocation=allocation_object.allocation,
                allocation_user=allocation_user_objects.allocation_user,
                value='Active')

        # create test jobs
        self.current_time = datetime.datetime.now(tz=datetime.timezone.utc)

        self.job1 = Job.objects.create(jobslurmid='1',
                                       submitdate=self.current_time - datetime.timedelta(
                                           days=5),
                                       startdate=self.current_time - datetime.timedelta(
                                           days=4),
                                       enddate=self.current_time - datetime.timedelta(
                                           days=3),
                                       userid=self.user0,
                                       partition='savio,savio2')

        self.job2 = Job.objects.create(jobslurmid='2',
                                       submitdate=self.current_time - datetime.timedelta(
                                           days=8),
                                       startdate=self.current_time - datetime.timedelta(
                                           days=6),
                                       enddate=self.current_time - datetime.timedelta(
                                           days=4),
                                       userid=self.user1,
                                       partition='savio_bigmem,savio2')

        self.job3 = Job.objects.create(jobslurmid='3',
                                       submitdate=self.current_time - datetime.timedelta(
                                           days=13),
                                       startdate=self.current_time - datetime.timedelta(
                                           days=10),
                                       enddate=self.current_time - datetime.timedelta(
                                           days=7),
                                       userid=self.user0,
                                       partition='savio3')

    def call_command(self, *args):
        """Call the command with the given arguments, returning the messages
        written to stdout and stderr."""

        out, err = StringIO(), StringIO()
        args = [*args]
        kwargs = {'stdout': out, 'stderr': err}
        call_command(*args, **kwargs)

        return out.getvalue(), err.getvalue()

    def convert_output(self, out, format):
        if format == 'json':
            output = json.loads(''.join(out))
        elif format == 'csv':
            output = [line.split(',') for line in
                      out.replace('\r', '').split('\n')
                      if line != '']
        else:
            raise CommandError('convert_output out_format must be either '
                               '\"csv\" or \"json\"')

        return output


class TestLatestJobsByUser(TestBaseExportData):
    """ Test class to test export data subcommand latest_jobs_by_user runs correctly """

    @enable_deployment('BRC')
    def setUp(self):
        """Setup test data"""
        super().setUp()

    @enable_deployment('BRC')
    def test_json_no_date(self):
        """Testing latest_jobs_by_user subcommand with NO date arg passed,
        exporting as JSON"""

        output, error = self.call_command('export_data',
                                          'latest_jobs_by_user',
                                          '--format=json')
        output = self.convert_output(output, 'json')

        self.assertEqual(len(output), 2)
        for index in range(2):
            item = output[index]
            self.assertEqual(item['username'], f'user{index}')
            self.assertEqual(item['jobslurmid'], f'{index + 1}')
            job = Job.objects.get(jobslurmid=f'{index + 1}')
            submit_date_str = datetime.datetime.strftime(job.submitdate,
                                                         DATE_FORMAT)
            self.assertEqual(item['submit_date'], submit_date_str)

        self.assertEqual(error, '')

    @enable_deployment('BRC')
    def test_json_with_date(self):
        """Testing latest_jobs_by_user subcommand with date arg passed,
        exporting as JSON"""

        start_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=6), ABR_DATE_FORMAT)

        output, error = self.call_command('export_data',
                                          'latest_jobs_by_user',
                                          '--format=json',
                                          f'--start_date={start_date}')
        output = self.convert_output(output, 'json')

        self.assertEqual(len(output), 1)
        for index in range(1):
            item = output[index]
            self.assertEqual(item['username'], f'user{index}')
            self.assertEqual(item['jobslurmid'], f'{index + 1}')
            job = Job.objects.get(jobslurmid=f'{index + 1}')
            submit_date_str = datetime.datetime.strftime(job.submitdate,
                                                         DATE_FORMAT)
            self.assertEqual(item['submit_date'], submit_date_str)

        self.assertEqual(error, '')

    @enable_deployment('BRC')
    def test_csv_no_date(self):
        """Testing latest_jobs_by_user subcommand with NO date arg passed,
        exporting as CSV"""

        output, error = self.call_command('export_data',
                                          'latest_jobs_by_user',
                                          '--format=csv')
        output = self.convert_output(output, 'csv')

        for index, item in enumerate(output):
            if index == 0:
                self.assertEqual(item,
                                 ['username', 'jobslurmid', 'submit_date'])
            else:
                self.assertEqual(item[0], f'user{index - 1}')
                self.assertEqual(item[1], f'{index}')
                job = Job.objects.get(jobslurmid=f'{index}')
                submit_date_str = datetime.datetime.strftime(job.submitdate,
                                                             DATE_FORMAT)
                self.assertEqual(item[2], submit_date_str)

        self.assertEqual(error, '')

    @enable_deployment('BRC')
    def test_with_date(self):
        """Testing latest_jobs_by_user subcommand with date arg passed,
        exporting as CSV"""

        start_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=6), ABR_DATE_FORMAT)

        output, error = self.call_command('export_data',
                                          'latest_jobs_by_user',
                                          '--format=csv',
                                          f'--start_date={start_date}')
        output = self.convert_output(output, 'csv')

        for index, item in enumerate(output):
            if index == 0:
                self.assertEqual(item,
                                 ['username', 'jobslurmid', 'submit_date'])
            else:
                self.assertEqual(item[0], f'user{index - 1}')
                self.assertEqual(item[1], f'{index}')
                job = Job.objects.get(jobslurmid=f'{index}')
                submit_date_str = datetime.datetime.strftime(job.submitdate,
                                                             DATE_FORMAT)
                self.assertEqual(item[2], submit_date_str)

        self.assertEqual(error, '')


class TestNewClusterAccounts(TestBaseExportData):
    """Test class to test export data subcommand new_cluster_accounts runs
    correctly."""

    @enable_deployment('BRC')
    def setUp(self):
        """Setup test data"""
        super().setUp()

        self.pre_time = utc_now_offset_aware().replace(tzinfo=None,
                                                       microsecond=0)

    @enable_deployment('BRC')
    def test_json_no_date(self):
        """Testing new_cluster_accounts subcommand with NO date arg passed,
        exporting as JSON"""
        output, error = self.call_command('export_data',
                                          'new_cluster_accounts',
                                          '--format=json')
        output = self.convert_output(output, 'json')

        post_time = utc_now_offset_aware().replace(tzinfo=None,
                                                   microsecond=999999)
        for index, item in enumerate(output):
            self.assertEqual(item['username'], f'user{index}')
            date_created = \
                datetime.datetime.strptime(item['date_created'],
                                           DATE_FORMAT)
            # TODO: This comparison is flaky. Make it not so.
            # self.assertTrue(self.pre_time <= date_created <= post_time)

        self.assertEqual(error, '')

    @enable_deployment('BRC')
    def test_json_with_date(self):
        """Testing new_cluster_accounts subcommand with ONE date arg passed,
        exporting as JSON"""

        start_date = datetime.datetime.strftime(
            self.pre_time - datetime.timedelta(days=4), ABR_DATE_FORMAT)

        new_date = display_time_zone_date_to_utc_datetime(
            (self.pre_time - datetime.timedelta(days=10)).date())

        allocation_user_attr_obj = AllocationUserAttribute.objects.get(
            allocation_attribute_type=self.cluster_account_status,
            allocation__project__name='fc_project0',
            allocation_user__user__username='user0',
            value='Active')

        allocation_user_attr_obj.created = new_date
        allocation_user_attr_obj.save()
        self.assertEqual(allocation_user_attr_obj.created, new_date)

        output, error = self.call_command('export_data',
                                          'new_cluster_accounts',
                                          '--format=json',
                                          f'--start_date={start_date}')
        output = self.convert_output(output, 'json')

        # this should only output the cluster account creation for user1
        post_time = utc_now_offset_aware().replace(tzinfo=None,
                                                   microsecond=999999)
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]['username'], 'user1')
        date_created = \
            datetime.datetime.strptime(output[0]['date_created'],
                                       DATE_FORMAT)
        # TODO: This comparison is flaky. Make it not so.
        # self.assertTrue(self.pre_time <= date_created <= post_time)

        self.assertEqual(error, '')

    @enable_deployment('BRC')
    def test_csv_no_date(self):
        """Testing new_cluster_accounts subcommand with NO date arg passed,
        exporting as CSV"""
        output, error = self.call_command('export_data',
                                          'new_cluster_accounts',
                                          '--format=csv')
        output = self.convert_output(output, 'csv')

        post_time = utc_now_offset_aware().replace(tzinfo=None,
                                                   microsecond=999999)
        for index, item in enumerate(output):
            if index == 0:
                self.assertEqual(item, ['username', 'date_created'])
            else:
                self.assertEqual(item[0], f'user{index - 1}')
                date_created = \
                    datetime.datetime.strptime(item[1],
                                               DATE_FORMAT)
                # TODO: This comparison is flaky. Make it not so.
                # self.assertTrue(self.pre_time <= date_created <= post_time)

            self.assertEqual(error, '')

    @enable_deployment('BRC')
    def test_csv_with_date(self):
        """Testing new_cluster_accounts subcommand with ONE date arg passed,
        exporting as CSV"""

        start_date = datetime.datetime.strftime(
            self.pre_time - datetime.timedelta(days=4), ABR_DATE_FORMAT)

        new_date = display_time_zone_date_to_utc_datetime(
            (self.pre_time - datetime.timedelta(days=10)).date())

        allocation_user_attr_obj = AllocationUserAttribute.objects.get(
            allocation_attribute_type=self.cluster_account_status,
            allocation__project__name='fc_project0',
            allocation_user__user__username='user0',
            value='Active')

        allocation_user_attr_obj.created = new_date
        allocation_user_attr_obj.save()
        self.assertEqual(allocation_user_attr_obj.created, new_date)

        output, error = self.call_command('export_data',
                                          'new_cluster_accounts',
                                          '--format=csv',
                                          f'--start_date={start_date}')
        output = self.convert_output(output, 'csv')

        post_time = utc_now_offset_aware().replace(tzinfo=None,
                                                   microsecond=999999)
        for index, item in enumerate(output):
            if index == 0:
                self.assertEqual(item, ['username', 'date_created'])
            else:
                self.assertEqual(item[0], 'user1')
                date_created = \
                    datetime.datetime.strptime(item[1],
                                               DATE_FORMAT)
                # TODO: This comparison is flaky. Make it not so.
                # self.assertTrue(self.pre_time <= date_created <= post_time)

        self.assertEqual(error, '')


class TestJobAvgQueueTime(TestBaseExportData):
    """ Test class to test export data subcommand job_avg_queue_time
    runs correctly """

    @enable_deployment('BRC')
    def setUp(self):
        """Setup test data"""
        super().setUp()

    @enable_deployment('BRC')
    def test_no_dates(self):
        """Testing job_avg_queue_time with NO date args passed"""
        output, error = self.call_command('export_data',
                                          'job_avg_queue_time')

        self.assertIn('48hrs 0mins 0secs', output)
        self.assertEqual(error, '')

    @enable_deployment('BRC')
    def test_two_dates(self):
        """Testing job_avg_queue_time with BOTH date args passed"""
        start_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=6), ABR_DATE_FORMAT)
        end_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=4), ABR_DATE_FORMAT)

        output, error = self.call_command('export_data',
                                          'job_avg_queue_time',
                                          f'--start_date={start_date}',
                                          f'--end_date={end_date}')
        self.assertIn('24hrs 0mins 0secs', output)
        self.assertEqual(error, '')

    @enable_deployment('BRC')
    def test_start_date(self):
        """Testing job_avg_queue_time with only start date arg passed"""
        start_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=6), ABR_DATE_FORMAT)

        output, error = self.call_command('export_data',
                                          'job_avg_queue_time',
                                          f'--start_date={start_date}')
        self.assertIn('24hrs 0mins 0secs', output)
        self.assertEqual(error, '')

    @enable_deployment('BRC')
    def test_end_date(self):
        """Testing job_avg_queue_time with only end date arg passed"""
        end_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=6), ABR_DATE_FORMAT)

        output, error = self.call_command('export_data',
                                          'job_avg_queue_time',
                                          f'--end_date={end_date}')
        self.assertIn('60hrs 0mins 0secs', output)
        self.assertEqual(error, '')

    @enable_deployment('BRC')
    def test_partition(self):
        """Testing job_avg_queue_time with parition arg passed"""
        output, error = self.call_command('export_data',
                                          'job_avg_queue_time',
                                          f'--partition=savio_bigmem')
        self.assertIn('48hrs 0mins 0secs', output)
        self.assertEqual(error, '')

    @enable_deployment('BRC')
    def test_errors(self):
        # invalid date error
        start_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=6), '%Y-%d-%m')
        end_date = datetime.datetime.strftime(
            self.current_time - datetime.timedelta(days=4), ABR_DATE_FORMAT)

        with self.assertRaises(CommandError):
            output, error = self.call_command('export_data',
                                              'job_avg_queue_time',
                                              f'--start_date={start_date}',
                                              f'--end_date={end_date}')
            self.assertEqual(output, '')
            self.assertEqual(error, '')

        # end date is before start date
        with self.assertRaises(CommandError):
            output, error = self.call_command('export_data',
                                              'job_avg_queue_time',
                                              f'--start_date={end_date}',
                                              f'--end_date={start_date}')
            self.assertEqual(output, '')
            self.assertEqual(error, '')

        # no jobs found with the passed args
        with self.assertRaises(CommandError):
            output, error = self.call_command('export_data',
                                              'job_avg_queue_time',
                                              f'--partition=test_partition')
            self.assertEqual(output, '')
            self.assertEqual(error, '')


class TestProjects(TestBase):
    """ Test class to test export data subcommand projects runs correctly """

    @enable_deployment('BRC')
    def setUp(self):
        super().setUp()

        # create sample projects
        active_status = ProjectStatusChoice.objects.get(name='Active')
        inactive_status = ProjectStatusChoice.objects.get(name='Inactive')
        prefixes = ['fc', 'ac', 'co']

        for index in range(10):
            project = Project.objects.create(
                name=f'{prefixes[index % len(prefixes)]}_project_{index}',
                status=active_status)

        for index in range(10, 20):
            project = Project.objects.create(
                name=f'{prefixes[index % len(prefixes)]}_project_{index}',
                status=inactive_status)

        total_projects = Project.objects.all()
        active_projects = total_projects.filter(status=active_status)
        fc_projects = total_projects.filter(name__istartswith='fc_')

        fc_project_ids = list(map(lambda x: x[0], fc_projects.values_list('id')))
        active_project_ids = list(map(lambda x: x[0], active_projects.values_list('id')))

        pi_table = []
        for project in total_projects:
            pis = project.pis()
            table = [f'{pi.first_name} {pi.last_name} ({pi.email})' for pi in pis]

            if table != []:
                pi_table.append(table)
            else:
                pi_table.append(None)

        manager_table = []
        for project in total_projects:
            managers = project.managers()
            table = [f'{manager.first_name} {manager.last_name} ({manager.email})'
                     for manager in managers]

            if table != []:
                manager_table.append(table)
            else:
                manager_table.append(None)

        status_table = []
        for project in total_projects:
            status_table.append(str(project.status))

        header = ['id', 'created', 'modified', 'name', 'title', 'description']
        query_set_ = total_projects.values_list(*header)

        query_set = []
        for index, project in enumerate(query_set_):
            project = list(project)
            project.extend([status_table[index],
                            ';'.join(pi_table[index] or []),
                            ';'.join(manager_table[index] or [])])
            query_set.append(project)

        # convert created and modified fields to strings
        base_queryset = []
        final_header = header + ['status', 'pis', 'manager']
        for project in query_set:
            project[1] = str(project[1])
            project[2] = str(project[2])
            base_queryset.append(dict(zip(final_header, project)))

        self.fc_queryset = [project for project in base_queryset if project['id'] in fc_project_ids]
        self.active_queryset = [
            project for project in base_queryset if project['id'] in active_project_ids]
        self.base_queryset = base_queryset

    @enable_deployment('BRC')
    def test_default(self):
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'projects',
                     '--format=csv', stdout=out, stderr=err)

        sys.stdout = sys.__stdout__
        out.seek(0)

        query_set = self.base_queryset

        output = DictReader(out.readlines())
        count = 0
        for index, item in enumerate(output):
            count += 1
            compare = query_set[index]

            self.assertListEqual(list(compare.keys()), list(item.keys()))

            for key in item.keys():
                self.assertEqual(str(compare[key]), item[key])

        self.assertEqual(len(query_set), count)

    @enable_deployment('BRC')
    def test_active_filter(self):
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'projects',
                     '--format=csv', '--active_only', stdout=out, stderr=err)

        sys.stdout = sys.__stdout__
        out.seek(0)

        query_set = self.active_queryset

        output = DictReader(out.readlines())
        count = 0
        for index, item in enumerate(output):
            count += 1
            compare = query_set[index]

            self.assertListEqual(list(compare.keys()), list(item.keys()))

            for key in item.keys():
                self.assertEqual(str(compare[key]), item[key])

        self.assertEqual(len(query_set), count)

    @enable_deployment('BRC')
    def test_allowance_filter(self):
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'projects',
                     '--format=csv', '--allowance_type=fc_', stdout=out,
                     stderr=err)

        sys.stdout = sys.__stdout__
        out.seek(0)

        query_set = self.fc_queryset

        output = DictReader(out.readlines())
        count = 0
        for index, item in enumerate(output):
            count += 1
            compare = query_set[index]

            self.assertListEqual(list(compare.keys()), list(item.keys()))

            for key in item.keys():
                self.assertEqual(str(compare[key]), str(item[key]))

        self.assertEqual(len(query_set), count)

    @enable_deployment('BRC')
    def test_format(self):
        # NOTE: csv is tested in other tests, only check json here
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'projects',
                     '--format=json', stdout=out, stderr=err)

        sys.stdout = sys.__stdout__
        out.seek(0)

        query_set = self.base_queryset

        output = json.loads(''.join(out.readlines()))
        count = 0
        for index, item in enumerate(output):
            count += 1
            compare = query_set[index]

            self.assertListEqual(list(compare.keys()), list(item.keys()))

            for key in item.keys():
                self.assertEqual(str(compare[key]), str(item[key]))

        self.assertEqual(len(query_set), count)


class TestNewProjectRequests(TestBase):
    """ Test class to test export data subcommand new_project_requests runs correctly """

    @enable_deployment('BRC')
    def setUp(self):
        super().setUp()

        project_status = ProjectStatusChoice.objects.get(name='Inactive')
        request_status = ProjectAllocationRequestStatusChoice.objects.get(
            name='Approved - Complete')

        savio_headers = ['id', 'created', 'modified',
                         'allocation_type', 'survey_answers', 'state', 'pool',
                         'extra_fields']
        vector_headers = ['id', 'created', 'modified', 'state']
        additional_headers = ['project', 'status', 'requester', 'pi']

        # create sample requests
        fca_computing_allowance = Resource.objects.get(name=BRCAllowances.FCA)
        fca_allocation_type = \
            ComputingAllowanceInterface().name_short_from_name(
                fca_computing_allowance.name)
        projects, statuses, requesters, pis = [], [], [], []
        for index in range(15):
            test_user = User.objects.create(
                first_name=f'Test{index}', last_name=f'User{index}',
                username=f'user{index}', email=f'user{index}@nonexistent.com')
            project = Project.objects.create(name=f'test_project_{index}', status=project_status)

            projects.append(project.name)
            statuses.append(request_status.name)
            requesters.append(f'{test_user.first_name} ' +
                              f'{test_user.last_name} ' +
                              f'({test_user.email})')
            pis.append(f'{test_user.first_name} ' +
                       f'{test_user.last_name} ' +
                       f'({test_user.email})')

            if 0 <= index < 5:
                VectorProjectAllocationRequest.objects.create(
                    requester=test_user,
                    project=project,
                    pi=test_user,
                    status=ProjectAllocationRequestStatusChoice.objects.get(
                        name='Approved - Complete'))

            elif 5 <= index < 10:
                SavioProjectAllocationRequest.objects.create(
                    requester=test_user,
                    allocation_type=fca_allocation_type,
                    computing_allowance=fca_computing_allowance,
                    project=project,
                    survey_answers={'abcd': 'bcda'},
                    pi=test_user,
                    created=display_time_zone_date_to_utc_datetime(
                        datetime.date(2022, 5, 5)),
                    status=ProjectAllocationRequestStatusChoice.objects.get(
                        name='Approved - Complete'))

            else:
                SavioProjectAllocationRequest.objects.create(
                    requester=test_user,
                    allocation_type=fca_allocation_type,
                    computing_allowance=fca_computing_allowance,
                    project=project,
                    survey_answers={'abcd': 'bcda'},
                    pi=test_user,
                    created=display_time_zone_date_to_utc_datetime(
                        datetime.date(2021, 1, 1)),
                    status=ProjectAllocationRequestStatusChoice.objects.get(
                        name='Approved - Complete'))

        vector_queryset = []
        vector_requests = VectorProjectAllocationRequest.objects.all().values_list(*vector_headers)
        for project, project_status, requester, pi, request in \
                zip(projects, statuses, requesters, pis, vector_requests):
            request = list(request)
            request[1] = str(request[1])
            request[2] = str(request[2])

            request.extend([project, project_status, requester, pi])
            vector_queryset.append(request)

        savio_queryset = []
        savio_requests = SavioProjectAllocationRequest.objects.all().values_list(*savio_headers)
        for project, project_status, requester, pi, request in \
                zip(projects[5:], statuses[5:], requesters[5:], pis[5:], savio_requests):
            request = list(request)
            request[1] = str(request[1])
            request[2] = str(request[2])

            request.extend([project, project_status, requester, pi])
            savio_queryset.append(request)

        self.threshold = '01-01-2022'
        date = display_time_zone_date_to_utc_datetime(
            datetime.datetime.strptime(self.threshold, '%m-%d-%Y').date())

        savio_newqueryset = []
        savio_newrequests = SavioProjectAllocationRequest.objects.all().\
            filter(created__gte=date).values_list(*savio_headers)
        for project, project_status, requester, pi, request in \
                zip(projects[5:], statuses[5:], requesters[5:], pis[5:], savio_newrequests):
            request = list(request)
            request[1] = str(request[1])
            request[2] = str(request[2])

            request.extend([project, project_status, requester, pi])
            savio_newqueryset.append(request)

        savio_headers.extend(additional_headers)
        vector_headers.extend(additional_headers)

        self.savio_newqueryset = list(map(lambda r: dict(zip(savio_headers, r)), savio_newqueryset))
        self.savio_queryset = list(map(lambda r: dict(zip(savio_headers, r)), savio_queryset))
        self.vector_queryset = list(map(lambda r: dict(zip(vector_headers, r)), vector_queryset))

    @enable_deployment('BRC')
    def test_savio(self):
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'new_project_requests',
                     '--format=csv', '--type=savio', stdout=out, stderr=err)

        sys.stdout = sys.__stdout__
        out.seek(0)

        query_set = self.savio_queryset

        output = DictReader(out.readlines())
        count = 0
        for index, item in enumerate(output):
            count += 1
            compare = query_set[index]

            self.assertListEqual(list(compare.keys()), list(item.keys()))

            for key in item.keys():
                self.assertEqual(str(compare[key]), str(item[key]))

        self.assertEqual(len(query_set), count)

    @enable_deployment('BRC')
    def test_vector(self):
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'new_project_requests',
                     '--format=csv', '--type=vector', stdout=out, stderr=err)

        sys.stdout = sys.__stdout__
        out.seek(0)

        query_set = self.vector_queryset

        output = DictReader(out.readlines())
        count = 0
        for index, item in enumerate(output):
            count += 1
            compare = query_set[index]

            self.assertListEqual(list(compare.keys()), list(item.keys()))

            for key in item.keys():
                self.assertEqual(str(compare[key]), str(item[key]))

        self.assertEqual(len(query_set), count)

    @enable_deployment('BRC')
    def test_json(self):
        # NOTE: csv is tested in other tests, only check json here
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'new_project_requests',
                     '--format=json', '--type=savio', stdout=out, stderr=err)

        sys.stdout = sys.__stdout__
        out.seek(0)

        query_set = self.savio_queryset

        output = json.loads(''.join(out.readlines()))
        count = 0
        for index, item in enumerate(output):
            count += 1
            compare = query_set[index]

            self.assertListEqual(list(compare.keys()), list(item.keys()))

            for key in item.keys():
                self.assertEqual(str(compare[key]), str(item[key]))

        self.assertEqual(len(query_set), count)

    @enable_deployment('BRC')
    def test_start_date(self):
        # NOTE: csv is tested in other tests, only check json here
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'new_project_requests',
                     '--format=json', '--type=savio', '--start_date=' + self.threshold,
                     stdout=out, stderr=err)

        sys.stdout = sys.__stdout__
        out.seek(0)

        query_set = self.savio_newqueryset

        output = json.loads(''.join(out.readlines()))
        count = 0
        for index, item in enumerate(output):
            count += 1
            compare = query_set[index]

            self.assertListEqual(list(compare.keys()), list(item.keys()))

            for key in item.keys():
                self.assertEqual(str(compare[key]), str(item[key]))

        self.assertEqual(len(query_set), count)


class TestNewProjectSurveyResponses(TestBase):
    """ Test class to test export data subcommand new_project_survey_responses runs correctly """

    @enable_deployment('BRC')
    def setUp(self):
        super().setUp()

        # create dummy survey responses
        fixtures = []
        filtered_fixtures = []

        # dummy params
        fca_computing_allowance = Resource.objects.get(name=BRCAllowances.FCA)
        fca_allocation_type = \
            ComputingAllowanceInterface().name_short_from_name(
                fca_computing_allowance.name)
        pool = False

        for index in range(5):
            pi = User.objects.create(
                username=f'test_user{index}', first_name='Test', last_name='User',
                is_superuser=True)

            project_status = ProjectStatusChoice.objects.get(name='Active')
            allocation_status = ProjectAllocationRequestStatusChoice.objects.get(
                name='Under Review')

            project_prefix = 'fc_' if index % 2 else ''
            project = Project.objects.create(name=f'{project_prefix}test_project{index}',
                                             status=project_status)

            survey_answers = {
                'scope_and_intent': 'sample scope',
                'computational_aspects': 'sample aspects',
            }

            kwargs = {
                'allocation_type': fca_allocation_type,
                'computing_allowance': fca_computing_allowance,
                'pi': pi,
                'project': project,
                'pool': pool,
                'survey_answers': survey_answers,
                'status': allocation_status,
                'requester': pi
            }

            fixture = SavioProjectAllocationRequest.objects.create(**kwargs)
            fixtures.append(fixture)

            if index % 2:
                filtered_fixtures.append(fixture)

        fixtures = list(sorted(fixtures, key=lambda x: x.project.name, reverse=True))
        filtered_fixtures = list(sorted(filtered_fixtures, key=lambda x: x.project.name, reverse=True))

        self.fixtures = fixtures
        self.filtered_fixtures = filtered_fixtures

    @enable_deployment('BRC')
    def test_new_project_survey_responses_json(self):
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'new_project_survey_responses',
                     '--format=json', stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        out.seek(0)
        output = json.loads(''.join(out.readlines()))
        for index, item in enumerate(output):
            project_name = item.pop('project_name')
            project_title = item.pop('project_title')
            self.assertEqual(project_name, self.fixtures[index].project.name)
            self.assertEqual(project_title, self.fixtures[index].project.title)
            self.assertDictEqual(item['new_project_survey_responses'], self.fixtures[index].survey_answers)

        err.seek(0)
        self.assertEqual(err.read(), '')

    @enable_deployment('BRC')
    def test_get_new_project_survey_responses_csv(self):
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'new_project_survey_responses',
                     '--format=csv', stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        out.seek(0)
        reader = DictReader(out.readlines())
        for index, item in enumerate(reader):
            project_name = item.pop('project_name')
            project_title = item.pop('project_title')
            self.assertEqual(project_name, self.fixtures[index].project.name)
            self.assertEqual(project_title, self.fixtures[index].project.title)
            self.assertDictEqual(item, self.fixtures[index].survey_answers)

        err.seek(0)
        self.assertEqual(err.read(), '')

    @enable_deployment('BRC')
    def test_get_new_project_survey_responses_allowance_type(self):
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'new_project_survey_responses',
                     '--format=csv', '--allowance_type=fc_', stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        out.seek(0)
        reader = DictReader(out.readlines())
        for index, item in enumerate(reader):
            project_name = item.pop('project_name')
            project_title = item.pop('project_title')
            self.assertEqual(project_name, self.filtered_fixtures[index].project.name)
            self.assertEqual(project_title, self.filtered_fixtures[index].project.title)
            self.assertDictEqual(item, self.filtered_fixtures[index].survey_answers)

        err.seek(0)
        self.assertEqual(err.read(), '')

class TestRenewalSurveyResponses(TestBase):
    """ Test class to test export data subcommand renewal_survey_responses 
    runs correctly """
    
    @enable_deployment('BRC')
    def setUp(self):
        super().setUp()

        fixtures = []
        filtered_fixtures = []

        allocation_period = AllocationPeriod.objects.get(
            name__exact='Allowance Year 2024 - 2025')
        
        for index in range(5):
            
            renewal_survey = {
                'brc_feedback': 'N/A', 
                'mybrc_comments': '', 
                'do_you_use_mybrc': 'no', 
                'classes_being_taught': f'sample answer {index}', 
                'colleague_suggestions': 'N/A', 
                'grants_supported_by_brc': 'Grant #1 etc. etc.\r\nGrant #2 etc. etc.', 
                'which_brc_services_used': ['savio_hpc', 'srdc'], 
                'indicate_topic_interests': ['have_visited_rdmp_website', 
                                'have_had_rdmp_event_or_consultation', 
                                'want_to_learn_security_and_have_rdm_consult'], 
                'brc_recommendation_rating': '6', 
                'publications_supported_by_brc': 'N/A', 
                'which_open_ondemand_apps_used': ['desktop', 'matlab', 
                                        'jupyter_notebook', 'vscode_server'], 
                'recruitment_or_retention_cases': 'N/A', 
                'brc_recommendation_rating_reason': 'Easy to use', 
                'how_important_to_research_is_brc': '5', 
                'training_session_other_topics_of_interest': 'None', 
                'how_brc_helped_bootstrap_computational_methods': 'N/A', 
                'training_session_usefulness_of_basic_savio_cluster': '4', 
                'training_session_usefulness_of_singularity_on_savio': '4', 
                'training_session_usefulness_of_advanced_savio_cluster': '2', 
                'training_session_usefulness_of_analytic_envs_on_demand': '5', 
                'training_session_usefulness_of_computational_platforms_training': '3'}
            
            active_project_status = ProjectStatusChoice.objects.get(name='Active')
            
            project_prefix = 'fc_' if index % 2 else 'pc_'
            project = Project.objects.create(
                name=f'{project_prefix}test_project{index}',
                status=active_project_status)
            
            requester = User.objects.create(
                email=f'requester{index}@email.com',
                first_name='Requester',
                last_name=f'User {index}',
                username=f'requester{index}')
            pi = User.objects.create(
                email=f'pi{index}@email.com',
                first_name='PI',
                last_name=f'User {index}',
                username=f'pi{index}')
            allocation_period_start_utc = display_time_zone_date_to_utc_datetime(
                allocation_period.start_date)
            fixture = AllocationRenewalRequest.objects.create(
                requester=requester,
                pi=pi,
                computing_allowance=Resource.objects.get(
                    name=BRCAllowances.FCA),
                allocation_period=allocation_period,
                status=AllocationRenewalRequestStatusChoice.objects.get(
                    name='Under Review'),
                renewal_survey_answers = renewal_survey, 
                pre_project=project,
                post_project=project,
                request_time=allocation_period_start_utc - datetime.timedelta(days=1))
            
            fixtures.append(fixture)
            if index % 2:
                filtered_fixtures.append(fixture)
        
        fixtures = list(sorted(
            fixtures, key=lambda x: x.pre_project.name, reverse=True))
        filtered_fixtures = list(sorted(
            filtered_fixtures, key=lambda x: x.pre_project.name, reverse=True))
        self.fixtures = fixtures
        self.filtered_fixtures = filtered_fixtures

    @enable_deployment('BRC')
    def test_get_renewal_survey_responses_json(self):
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'renewal_survey_responses',
                     '--format=json', 
                     '--allocation_period=Allowance Year 2024 - 2025', 
                     stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        out.seek(0)
        output = json.loads(''.join(out.readlines()))
        for index, item in enumerate(output):
            project_name = item.pop('project_name')
            fixture = self.fixtures[index]
            self.assertEqual(project_name, fixture.pre_project.name)
            self.assertEqual(item['renewal_survey_responses'], 
                    self.swap_form_answer_id_for_text(
                        fixture.renewal_survey_answers))
        err.seek(0)
        self.assertEqual(err.read(), '')

    @enable_deployment('BRC')
    def test_get_renewal_survey_responses_csv(self):
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'renewal_survey_responses',
                     '--format=csv', 
                     '--allocation_period=Allowance Year 2024 - 2025', 
                     stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        out.seek(0)
        reader = DictReader(out.readlines())
        for index, item in enumerate(reader):
            project_name = item.pop('project_name')
            project_title = item.pop('project_title')
            project_pi = item.pop('project_pi')
            fixture = self.fixtures[index]
            self.assertEqual(project_title, fixture.pre_project.title)
            self.assertEqual(project_pi, fixture.pi.username)
            self.assertEqual(project_name, fixture.pre_project.name)
            self.assertEqual(len(item), len(fixture.renewal_survey_answers))
            sample = ('6. Based upon your overall experience using BRC '
                      'services, how likely are you to recommend Berkeley '
                      'Research Computing to others?')
            sample_answer = '6'
            self.assertEqual(item[sample], sample_answer)

        err.seek(0)
        self.assertEqual(err.read(), '')

    @enable_deployment('BRC')
    def test_get_renewal_survey_responses_allowance_type(self):
        out, err = StringIO(''), StringIO('')
        call_command('export_data', 'renewal_survey_responses',
                     '--format=json', 
                     '--allocation_period=Allowance Year 2024 - 2025', 
                     '--allowance_type=fc_', stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        out.seek(0)
        output = json.loads(''.join(out.readlines()))
        for index, item in enumerate(output):
            project_name = item.pop('project_name')
            fixture = self.filtered_fixtures[index]
            self.assertEqual(project_name, fixture.pre_project.name)
            self.assertEqual(item['renewal_survey_responses'], 
                self.swap_form_answer_id_for_text(
                    fixture.renewal_survey_answers))

        err.seek(0)
        self.assertEqual(err.read(), '')

    @staticmethod
    def swap_form_answer_id_for_text(survey):
        '''
        Takes a survey, a dict mapping survey question IDs to answer IDs.
        Uses DeprecatedProjectRenewalSurveyForm.
        Swaps answer IDs for answer text, then question IDs for question text.
        Returns the modified survey.

        Parameter
        ----------
        survey : survey to modify
        '''
        multiple_choice_fields = {}
        form = DeprecatedProjectRenewalSurveyForm()
        for k, v in form.fields.items():
            # Only ChoiceField or MultipleChoiceField 
            # (in this specific survey form) have choices 
            if (isinstance(v, (forms.MultipleChoiceField, forms.ChoiceField))):
                multiple_choice_fields[k] = {
                    _k: _v for _k, _v in form.fields[k].choices}
        for question, answer in survey.items():
            if question in multiple_choice_fields.keys():
                sub_map = multiple_choice_fields[question]
                if (isinstance(answer, list)):
                    # Multiple choice, array
                    survey[question] = [sub_map.get(i,i) for i in answer]
                elif answer != '':
                    # Single choice replacement 
                    survey[question] = sub_map[answer]
        # Change keys of survey (question IDs) to be the human-readable text
        for id, text in form.fields.items():
            survey[text.label] = survey.pop(id)
        return survey