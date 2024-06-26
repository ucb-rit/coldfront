import copy

from django.urls import reverse
from http import HTTPStatus

from coldfront.core.project.models import *
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase
from coldfront.core.statistics.models import Job

from django.contrib.auth.models import User
from django.utils import timezone


class TestJobBase(TestBase):
    """A base class for testing job views."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Create a normal users
        self.user1 = User.objects.create(
            email='user1@email.com',
            first_name='Normal',
            last_name='User1',
            username='user1')

        self.user2 = User.objects.create(
            email='user2@email.com',
            first_name='Normal',
            last_name='User2',
            username='user2')

        self.pi = User.objects.create(
            email='pi@email.com',
            first_name='PI',
            last_name='PI',
            username='pi'
        )

        self.manager = User.objects.create(
            email='manager@email.com',
            first_name='Manager',
            last_name='Manager',
            username='manager'
        )

        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        self.active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        self.pending_remove = ProjectUserStatusChoice.objects.get(
            name='Pending - Remove')

        user_project_role = ProjectUserRoleChoice.objects.get(
            name='User')

        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')

        manager_role = ProjectUserRoleChoice.objects.get(
            name='Manager')

        # Create Projects.
        self.project1 = Project.objects.create(
            name='project1', status=active_project_status)

        self.project2 = Project.objects.create(
            name='project2', status=active_project_status)

        self.project1_user1 = ProjectUser.objects.create(
            user=self.user1,
            project=self.project1,
            role=user_project_role,
            status=self.active_project_user_status)

        self.project1_user2 = ProjectUser.objects.create(
            user=self.user2,
            project=self.project1,
            role=user_project_role,
            status=self.active_project_user_status)

        self.project2_user1 = ProjectUser.objects.create(
            user=self.user1,
            project=self.project2,
            role=user_project_role,
            status=self.active_project_user_status)

        self.project1_pi = ProjectUser.objects.create(
            user=self.pi,
            project=self.project1,
            role=pi_role,
            status=self.active_project_user_status)

        self.project1_manager = ProjectUser.objects.create(
            user=self.manager,
            project=self.project1,
            role=manager_role,
            status=self.active_project_user_status)

        # create admin and staff users
        self.admin = User.objects.create(
            email='admin@email.com',
            first_name='admin',
            last_name='admin',
            username='admin')
        self.admin.is_superuser = True
        self.admin.save()

        self.staff = User.objects.create(
            email='staff@email.com',
            first_name='staff',
            last_name='staff',
            username='staff')
        self.staff.is_staff = True
        self.staff.save()

        self.password = 'password'

        for user in User.objects.all():
            user_profile = UserProfile.objects.get(user=user)
            user_profile.access_agreement_signed_date = utc_now_offset_aware()
            user_profile.save()

            user.set_password(self.password)
            user.save()

        # create test jobs
        self.current_time = datetime.datetime.now(tz=timezone.utc)

        self.job1 = Job.objects.create(jobslurmid='12345',
                                       submitdate=self.current_time - datetime.timedelta(days=5),
                                       startdate=self.current_time - datetime.timedelta(days=4),
                                       enddate=self.current_time - datetime.timedelta(days=3),
                                       userid=self.user1,
                                       accountid=self.project1,
                                       jobstatus='COMPLETING',
                                       partition='test_partition1')

        self.job2 = Job.objects.create(jobslurmid='98765',
                                       submitdate=self.current_time - datetime.timedelta(days=6),
                                       startdate=self.current_time - datetime.timedelta(days=5),
                                       enddate=self.current_time - datetime.timedelta(days=4),
                                       userid=self.user1,
                                       accountid=self.project2,
                                       jobstatus='COMPLETING',
                                       partition='test_partition2')

    def assert_has_access(self, user, has_access, url):
        self.client.login(username=user.username, password=self.password)
        response = self.client.get(url)
        status_code = HTTPStatus.OK if has_access else HTTPStatus.FORBIDDEN
        self.assertEqual(response.status_code, status_code)

    def get_response(self, user, url):
        self.client.login(username=user.username, password=self.password)
        response = self.client.get(url)

        return response


class TestSlurmJobListView(TestJobBase):
    """A class for testing SlurmJobListView"""

    def setUp(self):
        """Set up test data."""
        super().setUp()

    def test_user_list_view_access(self):
        url = reverse('slurm-job-list')
        self.assert_has_access(self.user1, True, url)
        self.assert_has_access(self.user2, True, url)
        self.assert_has_access(self.pi, True, url)
        self.assert_has_access(self.manager, True, url)

    def test_user_list_view_content(self):
        """Testing content when users access SlurmJobListView"""
        url = reverse('slurm-job-list')

        # user1 should be able to see both jobs
        response = self.get_response(self.user1, url)
        self.assertContains(response, self.job1.jobslurmid)
        self.assertContains(response, self.job2.jobslurmid)
        self.assertContains(response, '<span class="badge badge-success">COMPLETED</span>')
        self.assertNotContains(response, '<span class="badge badge-success">COMPLETING</span>')
        self.assertNotContains(response, 'Show All Jobs')
        self.assertNotContains(response, 'div_id_username')

        # user2 should not be able to see job2
        response = self.get_response(self.user2, url)
        self.assertNotContains(response, self.job1.jobslurmid)
        self.assertNotContains(response, self.job2.jobslurmid)
        self.assertNotContains(response, 'Show All Jobs')
        self.assertNotContains(response, 'Username')

    def test_pi_manager_list_view_content(self):
        """Testing content when users access SlurmJobListView"""
        url = reverse('slurm-job-list')

        response = self.get_response(self.pi, url)
        self.assertContains(response, self.job1.jobslurmid)
        self.assertContains(response, 'div_id_username')
        self.assertNotContains(response, self.job2.jobslurmid)
        self.assertNotContains(response, 'Show All Jobs')

        response = self.get_response(self.manager, url)
        self.assertContains(response, self.job1.jobslurmid)
        self.assertContains(response, 'div_id_username')
        self.assertNotContains(response, self.job2.jobslurmid)
        self.assertNotContains(response, 'Show All Jobs')

    def test_admin_list_view_access(self):
        url = reverse('slurm-job-list')
        self.assert_has_access(self.admin, True, url)
        self.assert_has_access(self.staff, True, url)

    def test_admin_list_view_content(self):
        """Testing content when admins access SlurmJobListView"""
        # both admin and staff should see no jobs until selecting Show All Jobs
        def test_admin_contents(user):
            url = reverse('slurm-job-list')
            response = self.get_response(user, url)
            self.assertNotContains(response, self.job1.jobslurmid)
            self.assertNotContains(response, self.job2.jobslurmid)
            self.assertContains(response, 'Show All Jobs')
            self.assertContains(response, 'Viewing only jobs belonging to')
            self.assertContains(response, 'div_id_username')
            self.assertNotContains(response, 'Viewing all jobs.')
            self.assertNotContains(response, 'Viewing your jobs and the jobs')

            response = self.get_response(user, url + '?show_all_jobs=on')
            self.assertContains(response, self.job1.jobslurmid)
            self.assertContains(response, self.job2.jobslurmid)
            self.assertContains(response, 'Show All Jobs')
            self.assertContains(response, 'Show All Jobs')
            self.assertContains(response, 'div_id_username')
            self.assertNotContains(response, 'Viewing only jobs belonging to')
            self.assertContains(response, 'Viewing all jobs.')
            self.assertNotContains(response, 'Viewing your jobs and the jobs')

        test_admin_contents(self.admin)
        test_admin_contents(self.staff)

    def test_pagination(self):
        """Testing pagination of list view"""

        url = reverse('slurm-job-list') + '?show_all_jobs=on'
        response = self.get_response(self.admin, url)
        self.assertNotContains(response, 'Page')
        self.assertNotContains(response, 'Next')
        self.assertNotContains(response, 'Previous')

        for i in range(1000):
            Job.objects.create(jobslurmid=i)

        response = self.get_response(self.admin, url)
        self.assertContains(response, 'Page 1 of 34')
        self.assertContains(response, 'Next')
        self.assertContains(response, 'Previous')

    def test_status_colors(self):
        """Test different status colors"""

        def helper_test_status_colors(status_list, status_type):
            url = reverse('slurm-job-list') + '?show_all_jobs=on'
            for status in status_list:
                self.job1.jobstatus = status
                self.job1.save()
                self.job1.refresh_from_db()
                self.assertEqual(self.job1.jobstatus, status)

                response = self.get_response(self.admin, url)

                if status == 'CANCEL':
                    self.assertContains(response,
                                        '<span class="badge badge-danger">CANCELLED</span>')
                elif status == 'COMPLETING':
                    self.assertContains(response,
                                        '<span class="badge badge-success">COMPLETED</span>')
                else:
                    self.assertContains(response,
                                        f'<span class="badge badge-{status_type}">{status}</span>')

        self.job2.delete()

        status_danger_list = ['NODE_FAIL',
                              'CANCEL',
                              'FAILED',
                              'OUT_OF_MEMORY',
                              'TIMEOUT']
        helper_test_status_colors(status_danger_list, 'danger')
        helper_test_status_colors(['PREEMPTED', 'REQUEUED'], 'warning')
        helper_test_status_colors(['COMPLETING'], 'success')
        helper_test_status_colors(['RUNNING'], 'primary')

    def test_search_form_validation_errors(self):
        """Testing error messages raised from JobSearchForm validation"""

        def test_error_message(tag, throw_error, date=True):
            url = reverse('slurm-job-list') + '?show_all_jobs=on' + tag
            response = self.get_response(self.admin, url)

            if throw_error:
                if date:
                    self.assertContains(response,
                                        'When filtering on a date, you must '
                                        'select both a modifier and a date.')
                else:
                    self.assertContains(response,
                                        'When filtering on Service Units, '
                                        'you must select both a modifier and '
                                        'an amount.')
            else:
                self.assertNotContains(response,
                                       'When filtering on Service Units, '
                                       'you must select both a modifier and '
                                       'an amount.')
                self.assertNotContains(response,
                                       'When filtering on a date, you must '
                                       'select both a modifier and a date.')

        test_error_message('&submit_modifier=Before', True)
        test_error_message('&start_modifier=Before', True)
        test_error_message('&end_modifier=Before', True)
        test_error_message('&submitdate=01%2F05%2F2022', True)
        test_error_message('&startdate=01%2F05%2F2022', True)
        test_error_message('&enddate=01%2F05%2F2022', True)
        test_error_message('&end_modifier=Before&enddate=01%2F05%2F2022', False)

        test_error_message(
            '&end_modifier=Before&enddate=01%2F05%2F2022&start_modifier=Before',
            True)

        test_error_message('&amount=100', True, False)
        test_error_message('&amount_modifier=leq', True, False)

        test_error_message('&amount=100&amount_modifier=leq', False, False)


class TestSlurmJobDetailView(TestJobBase):
    """A class for testing SlurmJobDetailView"""

    def setUp(self):
        """Set up test data."""
        super().setUp()

    def test_user_access(self):
        """Testing user access to job detail view"""

        url = reverse('slurm-job-detail', kwargs={'pk': self.job1.pk})
        self.assert_has_access(self.user1, True, url)
        self.assert_has_access(self.user2, False, url)

        url = reverse('slurm-job-detail', kwargs={'pk': self.job2.pk})
        self.assert_has_access(self.user1, True, url)
        self.assert_has_access(self.user2, False, url)

    def test_pi_manager_access(self):
        """Testing PI/manager access to job detail view"""

        url = reverse('slurm-job-detail', kwargs={'pk': self.job1.pk})
        self.assert_has_access(self.pi, True, url)
        self.assert_has_access(self.manager, True, url)

        url = reverse('slurm-job-detail', kwargs={'pk': self.job2.pk})
        self.assert_has_access(self.pi, False, url)
        self.assert_has_access(self.manager, False, url)

    def test_admin_access(self):
        """Testing staff and admin access to job detail view"""
        url = reverse('slurm-job-detail', kwargs={'pk': self.job1.pk})
        self.assert_has_access(self.admin, True, url)
        self.assert_has_access(self.staff, True, url)

        url = reverse('slurm-job-detail', kwargs={'pk': self.job2.pk})
        self.assert_has_access(self.admin, True, url)
        self.assert_has_access(self.staff, True, url)


class ExportJobListView(TestJobBase):
    """A class for testing SlurmJobDetailView"""

    def setUp(self):
        """Set up test data."""
        super().setUp()

    def test_access(self):
        url = reverse('export-job-list')

        self.assert_has_access(self.user1, False, url)
        self.assert_has_access(self.user2, False, url)
        self.assert_has_access(self.admin, True, url)
        self.assert_has_access(self.staff, False, url)

    def test_job_list_view(self):
        """Testing if 'Export Job List to CSV' button appears"""
        url = reverse('slurm-job-list')
        response = self.get_response(self.user1, url)
        self.assertNotContains(response, 'Export Job List to CSV')

        response = self.get_response(self.staff, url)
        self.assertNotContains(response, 'Export Job List to CSV')

        response = self.get_response(self.admin, url)
        self.assertContains(response, 'Export Job List to CSV')

    def test_job_list_saves_session(self):
        """Testing if cleaned form data is saved in session"""
        url = reverse('slurm-job-list') + '?show_all_jobs=on&username=user1&partition=testpartition'
        self.get_response(self.admin, url)

        self.assertEqual(self.client.session.get('job_search_form_data')['username'],
                         self.user1.username)
        self.assertEqual(self.client.session.get('job_search_form_data')['partition'],
                         'testpartition')

    def create_job_csv_line(self, job):
        job_line = f'{job.jobslurmid},{job.userid.username},' \
                   f'{job.accountid.name},{job.partition},' \
                   f'{job.jobstatus},{job.submitdate},' \
                   f'{job.startdate},{job.enddate},' \
                   f'{job.amount}'

        return job_line

    def test_exported_csv_no_filtering(self):
        """Testing if exported CSV file has correct data"""

        url = reverse('export-job-list')
        self.client.login(username=self.admin.username, password=self.password)

        session = self.client.session
        session['job_search_form_data'] = {'status': '',
                                           'jobslurmid': '',
                                           'project_name': '',
                                           'username': '',
                                           'partition': '',
                                           'submitdate': None,
                                           'submit_modifier': '',
                                           'startdate': None,
                                           'start_modifier': '',
                                           'enddate': None,
                                           'end_modifier': '',
                                           'show_all_jobs': True}
        session.save()

        response = self.client.get(url)

        csv_lines = copy.deepcopy(list(response.streaming_content))

        self.assertIn(f'jobslurmid,username,project_name,partition,'
                      f'jobstatus,submitdate,startdate,enddate',
                      csv_lines[0].decode('utf-8'))

        job1_line = self.create_job_csv_line(self.job1)
        job2_line = self.create_job_csv_line(self.job2)

        self.assertIn(job1_line, csv_lines[1].decode('utf-8'))
        self.assertIn(job2_line, csv_lines[2].decode('utf-8'))
        self.assertEqual(len(csv_lines), 3)

    def test_exported_csv_with_filtering(self):
        """Testing if exported CSV file has correct data"""

        url = reverse('export-job-list')
        self.client.login(username=self.admin.username, password=self.password)

        session = self.client.session
        session['job_search_form_data'] = {'status': '',
                                           'jobslurmid': '',
                                           'project_name': '',
                                           'username': '',
                                           'partition': 'test_partition1',
                                           'submitdate': None,
                                           'submit_modifier': '',
                                           'startdate': None,
                                           'start_modifier': '',
                                           'enddate': None,
                                           'end_modifier': '',
                                           'show_all_jobs': True}
        session.save()

        response = self.client.get(url)

        csv_lines = copy.deepcopy(list(response.streaming_content))

        self.assertIn(f'jobslurmid,username,project_name,partition,'
                      f'jobstatus,submitdate,startdate,enddate,service_units',
                      csv_lines[0].decode('utf-8'))

        job1_line = self.create_job_csv_line(self.job1)

        self.assertIn(job1_line, csv_lines[1].decode('utf-8'))
        self.assertEqual(len(csv_lines), 2)
