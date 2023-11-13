from io import BytesIO
from coldfront.core.project.tests.test_views.test_renewal_views.utils import TestRenewalViewsMixin
from coldfront.core.resource.models import Resource
from coldfront.core.resource.models import ResourceAttribute
from coldfront.core.resource.models import ResourceAttributeType
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.mou import get_mou_filename
from coldfront.core.utils.tests.test_base import TestBase
from coldfront.core.utils.tests.test_base import enable_deployment
from coldfront.core.allocation.models import AllocationAdditionRequest, AllocationAdditionRequestStatusChoice, AllocationRenewalRequest, SecureDirRequest, SecureDirRequestStatusChoice
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.project.models import Project, ProjectAllocationRequestStatusChoice, SavioProjectAllocationRequest, savio_project_request_ica_extra_fields_schema, savio_project_request_ica_state_schema
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.utils.common import utc_now_offset_aware
from django.urls import reverse
from django.contrib.auth.models import User
from django.test import Client
from django.core import mail
from django.core.files import File
from decimal import Decimal
from http import HTTPStatus

class MOUTestBase(TestBase):

    @enable_deployment('BRC')
    def setUp(self):
        """Setup test data"""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)
        
        self.admin_user = User.objects.create(
            email='admin@email.com',
            first_name='Admin',
            last_name='User',
            username='admin',
            is_superuser=True,
            is_staff=True,)
        self.admin_user.set_password('admin')
        self.admin_user.save()
        self.admin_client = Client()
        self.admin_client.login(username='admin', password='admin')
        self.request = None

    @staticmethod
    def review_notify_url(pk, request_type):
        return reverse(f'{request_type}-request-notify-pi', kwargs={'pk': pk})

    @staticmethod
    def download_unsigned_mou_url(pk, request_type):
        return reverse(f'{request_type}-request-download-unsigned-mou', kwargs={'pk': pk, 'request_type': request_type})

    @staticmethod
    def upload_mou_url(pk, request_type):
        return reverse(f'{request_type}-request-upload-mou', kwargs={'pk': pk, 'request_type': request_type})

    @staticmethod
    def download_mou_url(pk, request_type):
        return reverse(f'{request_type}-request-download-mou', kwargs={'pk': pk, 'request_type': request_type})
    
    def _test_download_upload_download(self, request_type):
        url = self.download_unsigned_mou_url(self.request.pk, request_type)
        response = self.client.get(url)
        filename = get_mou_filename(self.request)
        self.assertEqual(response.get('Content-Disposition'),
                         f'attachment; filename="{filename}"')

        url = self.upload_mou_url(self.request.pk, request_type)
        self.assert_has_access(url, self.user)
        self.client.login(username=self.user.username, password=self.password)
        self.request.mou_file = File(BytesIO(b'abc'), 'mou.pdf')
        self.request.save()
        self.request.refresh_from_db()

        url = self.download_mou_url(self.request.pk, request_type)
        response = self.client.get(url)
        self.assertEqual(next(response.streaming_content), b'abc')

class TestNewProjectMOUNotifyUploadDownload(MOUTestBase):

    @enable_deployment('BRC')
    def setUp(self):
        """Setup test data"""
        super().setUp()

        computing_allowance = Resource.objects.get(name='Instructional Computing Allowance')
        ResourceAttribute.objects.create(
            resource_attribute_type=ResourceAttributeType.objects.get(name='Service Units'),
            resource=computing_allowance,
            value=Decimal(100000)).save()
            
        self.project, self.request = self.create_project_and_request(
            'ic_testproject',
            computing_allowance,
            self.user)

    @staticmethod
    def create_project_and_request(project_name, computing_allowance,
                                   requester_and_pi):
        """Create an active Project with the given name and computing
        allowance, add the given user to it, and create an
        AllocationRenewalRequest with 'Under Review' status. Return both."""
        active_project_status = ProjectStatusChoice.objects.get(name='New')
        project = Project.objects.create(
            name=project_name,
            title=project_name,
            status=active_project_status)
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        ProjectUser.objects.create(
            project=project,
            role=pi_role,
            status=active_project_user_status,
            user=requester_and_pi)
        allocation_period = get_current_allowance_year_period()
        under_review_request_status = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Under Review')
        project_request = SavioProjectAllocationRequest.objects.create(
            requester=requester_and_pi,
            pi=requester_and_pi,
            computing_allowance=computing_allowance,
            allocation_period=allocation_period,
            status=under_review_request_status,
            project=project,
            request_time=utc_now_offset_aware(),
            survey_answers={'abcd': 'bcda'},
            state=savio_project_request_ica_state_schema(),
            extra_fields=savio_project_request_ica_extra_fields_schema()
            )
        return project, project_request
    
    @staticmethod
    def eligibility_url(pk):
        return reverse(f'new-project-request-review-eligibility', kwargs={'pk': pk})

    @staticmethod
    def readiness_url(pk):
        return reverse(f'new-project-request-review-readiness', kwargs={'pk': pk})
    
    @enable_deployment('BRC')
    def test_new_project(self):
        """Test that the MOU notification task, MOU upload, and MOU download
        features work as expected."""
        eligibility = { 'status': 'Approved' }
        readiness = { 'status': 'Approved' }
        extra_fields = {
            'course_name': 'TEST 101',
            'course_department': 'Dept. of Testing',
            'point_of_contact': 'Test User',
            'num_students': 10,
            'num_gsis': 10,
            'manager_experience_description': 'a' * 100,
            'student_experience_description': 'a' * 100,
            'max_simultaneous_jobs': 10,
            'max_simultaneous_nodes': 10,
        }

        request_type = 'new-project'

        url = self.eligibility_url(self.request.pk)
        response = self.admin_client.post(url, data=eligibility)
        url = self.readiness_url(self.request.pk)
        response = self.admin_client.post(url, data=readiness)
        url = self.review_notify_url(self.request.pk, request_type)
        response = self.admin_client.post(url, data=extra_fields)

        self.request.refresh_from_db()
        self.assertEqual(self.request.state['eligibility']['status'], 'Approved')
        self.assertEqual(self.request.state['readiness']['status'], 'Approved')
        self.assertEqual(self.request.state['notified']['status'], 'Complete')
        self.assertEqual(self.request.extra_fields['course_name'], 'TEST 101')
        self.assertEqual(self.request.extra_fields['course_department'], 'Dept. of Testing')
        self.assertEqual(self.request.extra_fields['point_of_contact'], 'Test User')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, '[MyBRC-User-Portal] Savio Project Request Ready To Be Signed')

        self._test_download_upload_download(request_type)

class TestAllocationAdditionMOUNotifyUploadDownload(MOUTestBase):

    @enable_deployment('BRC')
    def setUp(self):
        """Setup test data"""
        super().setUp()
        self.project = self.create_active_project_with_pi('ac_testproject', self.user)
        self.request = self.create_addition_request(self.project, self.user)


    @staticmethod
    def create_addition_request(project, requester):
        """Create an 'Under Review' request for the given Project by the
        given requester."""
        return AllocationAdditionRequest.objects.create(
            requester=requester,
            project=project,
            status=AllocationAdditionRequestStatusChoice.objects.get(
                name='Under Review'),
            num_service_units=Decimal('1000.00'))

    @enable_deployment('BRC')
    def test_allocation_addition(self):
        """Test that the MOU notification task, MOU upload, and MOU download
        features work as expected."""
        request_type = 'service-units-purchase'
        eligibility = { 'status': 'Approved' }
        readiness = { 'status': 'Approved' }
        extra_fields = {
            'num_service_units': '100000',
            'campus_chartstring': 'TEST-TEST-TEST-TEST-TEST',
            'chartstring_account_type': 'TEST',
            'chartstring_contact_name': 'Test User',
            'chartstring_contact_email': 'test@email.com',
        }
        url = self.review_notify_url(self.request.pk, request_type)
        self.admin_client.post(url, data=extra_fields)

        self.request.refresh_from_db()
        self.assertEqual(self.request.state['notified']['status'], 'Complete')
        self.assertEqual(self.request.extra_fields['num_service_units'], 100000)
        self.assertEqual(self.request.extra_fields['chartstring_contact_name'], 'Test User')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, '[MyBRC-User-Portal] Service Units Purchase Request Ready To Be Signed')

        self._test_download_upload_download(request_type)

class SecureDirMOUNotifyUploadDownload(MOUTestBase):

    @enable_deployment('BRC')
    def setUp(self):
        """Setup test data"""
        super().setUp()
        self.project = self.create_active_project_with_pi('fc_testproject', self.user)
        self.request = self.create_secure_dir_request(self.project, self.user)


    @staticmethod
    def create_secure_dir_request(project, requester):
        """Create an 'Under Review' request for the given Project by the
        given requester."""
        return SecureDirRequest.objects.create(
            directory_name = 'test_dir',
            data_description = 'test description',
            requester=requester,
            project=project,
            status=SecureDirRequestStatusChoice.objects.get(
                name='Under Review'))
    @staticmethod
    def rdm_consultation_url(pk):
        return reverse('secure-dir-request-review-rdm-consultation', kwargs={'pk': pk})

    @enable_deployment('BRC')
    def test_allocation_addition(self):
        """Test that the MOU notification task, MOU upload, and MOU download
        features work as expected."""
        request_type = 'secure-dir'
        rdm_consultation = { 'status': 'Approved' }
        department = { 'department': 'Dept. of Testing', }

        url = self.rdm_consultation_url(pk=self.request.pk)
        self.admin_client.post(url, data=rdm_consultation)
        url = self.review_notify_url(self.request.pk, request_type)
        self.admin_client.post(url, data=department)

        self.request.refresh_from_db()
        self.assertEqual(self.request.state['notified']['status'], 'Complete')
        self.assertEqual(self.request.department, 'Dept. of Testing')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, '[MyBRC-User-Portal] Secure Directory Request Ready To Be Signed')

        self._test_download_upload_download(request_type)
