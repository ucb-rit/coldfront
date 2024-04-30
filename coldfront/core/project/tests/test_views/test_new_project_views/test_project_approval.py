from flags.state import flag_enabled

from coldfront.core.utils.tests.test_base import TestBase
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectPooledProjectSelectionForm
from coldfront.core.project.models import SavioProjectAllocationRequest

from coldfront.core.utils.tests.test_base import enable_deployment

from coldfront.core.project.models import Project
#from coldfront.core.project.views_.new_project_views import SavioProjectReviewSetupView
#from django.contrib.auth.mixins import LoginRequiredMixin
#from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.views.generic.edit import FormView
from coldfront.core.project.models import ProjectUserStatusChoice
from http import HTTPStatus

from django.conf import settings
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse

from flags.state import flag_enabled

from coldfront.api.statistics.utils import create_project_allocation
from coldfront.core.billing.models import BillingActivity
from coldfront.core.billing.models import BillingProject
from coldfront.core.project.tests.utils import create_project_and_request
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.project.utils_.renewal_utils import get_next_allowance_year_period
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.constants import LRCAllowances
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.common import display_time_zone_current_date
from coldfront.core.utils.common import format_date_month_name_day_year
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase
from decimal import Decimal

class TestSavioProjectReviewSetupViewNoPooling(TestBase,  
                                             FormView):
    """A class for testing SavioProjectReviewSetupView without pooling"""
    def setUp(self):
        super().setUp()
        self.user = self.create_test_user()
        self.user.is_superuser=True

        if flag_enabled('LRC_ONLY'):
            self.user.email = 'test_user@lbl.gov'
            self.user.save()

        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

        self.interface = ComputingAllowanceInterface()

        # Create a Project and a corresponding new project request.
        computing_allowance = self.get_predominant_computing_allowance()
        prefix = self.interface.code_from_name(computing_allowance.name)
        allocation_period = get_current_allowance_year_period()
        self.project, self.new_project_request = \
            create_project_and_request(
                f'{prefix}_project', 'New', computing_allowance,
                allocation_period, self.user, self.user,
                'Approved - Processing')

        self.new_project_request.billing_activity = \
            BillingActivity.objects.create(
                billing_project=BillingProject.objects.create(
                    identifier='000000'),
                identifier='000')
        self.new_project_request.save() 

    @staticmethod
    def review_view_url(pk):
        """Return the URL for the detail view for the 
        SavioProjectReviewSetupView with the given primary key"""
        return reverse('new-project-request-review-setup', kwargs={'pk': pk})

    def test_approval_no_pooling(self):
        """Test approval when the name is under the maximum characters and no pooling"""
        self.user.is_superuser = True
        self.user.save()

        # Set the request's state
        new_project_request = self.new_project_request
        new_project_request.state['eligibility']['status'] = 'Approved' 
        new_project_request.state['readiness']['status'] = 'Approved'
        new_project_request.state['setup']['status'] = 'Pending'
        new_project_request.save()

        url = self.review_view_url(new_project_request.pk)
        #long_name = 50*'name'
        long_name = "pc_hello"
        justification = 25 * 'lol'
        data = {'requested_name': long_name,
                'final_name': long_name,
                'justification': justification,
                 'status':"Complete" }
        
        response = self.client.post(url,data)
        # Will pass this test with no message since expected response to correct name is 302. 
        self.assertEqual(response.status_code, 302)

        long_name = 50*'name'
        data = {'requested_name': long_name,
                'final_name': long_name,
                'justification': justification,
                 'status':"Complete" }
        response = self.client.post(url,data)
        self.assertFalse(response.context['form'].is_valid())

    
    def test_no_approval_no_pooling(self):
        """Test non-approval after a name that exceeds max_length"""

        #self.user.is_superuser = True
        #self.user.save()

        # Set the request's state
        new_project_request = self.new_project_request
        new_project_request.state['eligibility']['status'] = 'Approved' 
        new_project_request.state['readiness']['status'] = 'Approved'
        new_project_request.state['setup']['status'] = 'Pending'
        new_project_request.save()

        url = self.review_view_url(new_project_request.pk)
        long_name = 50*'name'
        justification = 25 * 'lol'
        data = {'requested_name': long_name,
                'final_name': long_name,
                'justification': justification,
                 'status':"Complete" }
        
        response = self.client.post(url,data)
        self.assertFalse(response.context['form'].is_valid(), """Should not create
                         project because final_name exceeds max_length
                         """)
        

class TestSavioProjectReviewSetupViewWithPooling(TestBase,  
                                             FormView):
    """A class for testing SavioProjectReviewSetupView with pooling"""
    def create_base_project(self):
        """Creating a project to be pooled with"""
        interface = ComputingAllowanceInterface()
        if flag_enabled('BRC_ONLY'):
            computing_allowance_name = BRCAllowances.FCA
        elif flag_enabled('LRC_ONLY'):
            computing_allowance_name = LRCAllowances.PCA
        else:
            raise ImproperlyConfigured
        prefix = interface.code_from_name(computing_allowance_name)

        active_name = f'{prefix}_active_project_with_ultra_long_name'
        active_status = ProjectStatusChoice.objects.get(name='Active')
        active_project = Project.objects.create(
            name=active_name, title=active_name, status=active_status)
        form = SavioProjectPooledProjectSelectionForm(
            computing_allowance=Resource.objects.get(
                name=computing_allowance_name))
        project_field_choices = form.fields['project'].queryset
        self.assertEqual(len(project_field_choices), 1)
        self.assertEqual(project_field_choices[0], active_project)
        return active_name
        
    
    def create_pooled_project(self, existing_project_name, new_project_name):
        """Creating a new pooled project, pooled with an existing project"""
        
        return 
    
    def setUp(self):
        super.setUp()
        # Create project user
        self.create_test_user()
        self.user.is_superuser = True

        if flag_enabled('LRC_ONLY'):
            self.user.email = 'test_user@lbl.gov'
            self.user.save()

        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

        self.interface = ComputingAllowanceInterface()

        # Create a Project and a corresponding new project request.
        computing_allowance = self.get_predominant_computing_allowance()
        prefix = self.interface.code_from_name(computing_allowance.name)
        allocation_period = get_current_allowance_year_period()
        self.project, self.new_project_request = \
            create_project_and_request(
                f'{prefix}_project', 'New', computing_allowance,
                allocation_period, self.user, self.user,
                'Approved - Processing')

        self.new_project_request.billing_activity = \
            BillingActivity.objects.create(
                billing_project=BillingProject.objects.create(
                    identifier='000000'),
                identifier='000')
        self.new_project_request.save() 

class TestSavioProjectRequestWizard(TestBase):
    """A class for testing SavioProjectRequestWizard."""

    @enable_deployment('BRC')
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

        self.interface = ComputingAllowanceInterface()

        # Create old project with long name
        if flag_enabled('BRC_ONLY'):
            computing_allowance_name = BRCAllowances.FCA
        elif flag_enabled('LRC_ONLY'):
            computing_allowance_name = LRCAllowances.PCA
        else:
            raise ImproperlyConfigured
        prefix = self.interface.code_from_name(
            computing_allowance_name)
        self.long_name = f'{prefix}{50 * "a"}'
        import pdb; pdb.set_trace()
        active_status = ProjectStatusChoice.objects.get(name='Active')
        active_project = Project.objects.create(
            name=self.long_name, 
            title='longtest', 
            status=active_status)

    @staticmethod
    def request_url():
        """Return the URL for requesting to create a new Savio
        project."""
        return reverse('new-project-request')

    @enable_deployment('BRC')
    def test_post_creates_request(self):
        """Test that a POST request creates a
        SavioProjectAllocationRequest."""
        self.assertEqual(SavioProjectAllocationRequest.objects.count(), 0)
        #self.assertEqual(Project.objects.count(), 0)

        computing_allowance = self.get_predominant_computing_allowance()
        allocation_period = get_current_allowance_year_period()

        view_name = 'savio_project_request_wizard'
        current_step_key = f'{view_name}-current_step'
        computing_allowance_form_data = {
            '0-computing_allowance': computing_allowance.pk,
            current_step_key: '0',
        }
        allocation_period_form_data = {
            '1-allocation_period': allocation_period.pk,
            current_step_key: '1',
        }
        existing_pi_form_data = {
            '2-PI': self.user.pk,
            current_step_key: '2',
        }
        pool_allocations_data = {
            '6-pool': True,
            current_step_key: '6',
        }
        project = {
            '7-project': f'{self.long_name} ()',
            current_step_key: '7'
        }
        details_data = {
            '8-name': 'name',
            '8-title': 'title',
            '8-description': 'a' * 20,
            current_step_key: '8',
        }
        survey_data = {
            '10-scope_and_intent': 'b' * 20,
            '10-computational_aspects': 'c' * 20,
            current_step_key: '10',
        }
        form_data = [
            computing_allowance_form_data,
            allocation_period_form_data,
            existing_pi_form_data,
            pool_allocations_data,
            project,
            details_data,
            survey_data,

        ]
        url = self.request_url()
        for i, data in enumerate(form_data):
            if data == project: 
                import pdb; pdb.set_trace()
            response = self.client.post(url, data)
            if i == len(form_data) - 1:
                self.assertRedirects(response, reverse('home'))
            else:
                self.assertEqual(response.status_code, HTTPStatus.OK)

        requests = SavioProjectAllocationRequest.objects.all()
        self.assertEqual(requests.count(), 1)
        projects = Project.objects.all()
        self.assertEqual(projects.count(), 1)

        request = requests.first()
        project = projects.first()
        self.assertEqual(request.requester, self.user)
        self.assertEqual(
            request.allocation_type,
            self.interface.name_short_from_name(computing_allowance.name))
        self.assertEqual(request.computing_allowance, computing_allowance)
        self.assertEqual(request.allocation_period, allocation_period)
        self.assertEqual(request.pi, self.user)
        self.assertEqual(request.project, project)
        self.assertEqual(project.name, f'fc_{details_data["8-name"]}')
        self.assertEqual(project.title, details_data['8-title'])
        self.assertEqual(project.description, details_data['8-description'])
        self.assertFalse(request.pool)
        self.assertEqual(
            request.survey_answers['scope_and_intent'],
            survey_data['10-scope_and_intent'])
        self.assertEqual(
            request.survey_answers['computational_aspects'],
            survey_data['10-computational_aspects'])
        self.assertEqual(request.status.name, 'Under Review')

    # TODO
