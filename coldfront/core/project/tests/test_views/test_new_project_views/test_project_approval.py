from decimal import Decimal
from http import HTTPStatus

from coldfront.api.statistics.utils import create_project_allocation
from coldfront.core.billing.models import BillingActivity, BillingProject
from coldfront.core.project.models import (Project, ProjectStatusChoice,
                                           SavioProjectAllocationRequest)
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.constants import LRCAllowances 
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface

from coldfront.core.project.tests.utils import create_project_and_request
from coldfront.core.project.utils_.renewal_utils import \
    get_current_allowance_year_period
from coldfront.core.utils.tests.test_base import TestBase, enable_deployment
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.views.generic.edit import FormView
from flags.state import flag_enabled


class TestSavioProjectReviewSetupViewNoPooling(TestBase,  
                                             FormView):
    """A class for testing SavioProjectReviewSetupView without pooling"""
    def setUp(self):
        """Creates the test project"""
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

    def set_status(self, new_project_request):
        """Set the request's state"""
        new_project_request.state['eligibility']['status'] = 'Approved' 
        new_project_request.state['readiness']['status'] = 'Approved'
        new_project_request.state['setup']['status'] = 'Pending'
        new_project_request.save()
        return new_project_request

    @staticmethod 
    def post_approval_data(self, 
                           url,
                           requested_name,
                           final_name,
                           justification,):
        data = {'requested_name': requested_name,
                'final_name': final_name,
                'justification': justification,
                 'status':"Complete" }
        response = self.client.post(url, data)
        return response

    def test_approval_no_pooling_compliant_name(self):
        """Test approval when the name is under the maximum characters and no pooling"""
        self.user.is_superuser = True
        self.user.save()
        # Set the request's state
        breakpoint()
        new_project_request = self.set_status(self.new_project_request)
        url = self.review_view_url(new_project_request.pk)
        compliant_name= "pc_hello"
        justification = 25 * 'lol'
        response = self.post_approval_data(url=url,
                                           requested_name=compliant_name,
                                           final_name=compliant_name,
                                           justification=justification)
        # Will pass this test with no message since expected response to correct name is 302. 
        self.assertEqual(response.status_code, 302)

    def test_approval_no_pooling_long_name(self):
        """Test that no approval happens when there is no pooling and the final name exceeds 15 chars"""
        self.user.is_superuser = True
        self.user.save()
        # Set the request's state
        new_project_request = self.set_status()
        long_name = 50*'name'
        justification = 'a' * 20
        url = self.review_view_url(new_project_request.pk)
        # Make request to approval
        response = self.post_approval_data(url=url,
                                           requested_name='test',
                                           final_name=long_name,
                                           justification=justification)
        
        self.assertFalse(response.context['form'].is_valid())

    
    def test_no_approval_no_pooling(self):
        """Test non-approval after a name that exceeds max_length"""
        self.user.is_superuser = True
        self.user.save()
        # Set the request's state
        new_project_request = self.set_status()
        url = self.review_view_url(new_project_request.pk)
        long_name = 50*'name'
        justification = 25 * 'lol'
        response = self.post_approval_data(url=url,
                                           requested_name='test',
                                           final_name=long_name,
                                           justification=justification) 
        self.assertFalse(response.context['form'].is_valid(), """Should not create
                         project because final_name exceeds max_length
                         """)
        

class TestSavioProjectReviewSetupViewWithPooling(TestBase,  
                                             FormView):
    """A class for testing SavioProjectReviewSetupView with pooling"""
    @enable_deployment('BRC')
    def setUp(self):
        """Set up test data, the initial project with a 15 chars+ name."""
        super().setUp()
        self.user = self.create_test_user()
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
        active_status = ProjectStatusChoice.objects.get(name='Active')
        active_project = Project.objects.create(
            name=self.long_name, 
            title='longtest', 
            status=active_status)
        allocation = Decimal('1000.0')
        self.alloc_obj = create_project_allocation(active_project, allocation)

    @staticmethod
    def request_url():
        """Return the URL for requesting to create a new Savio
        project."""
        return reverse('new-project-request')


    def user_request(self, form_data, url):
        for i, data in enumerate(form_data):
            response = self.client.post(url, data)
            if i == len(form_data) - 1:
                self.assertRedirects(response, reverse('home'))
            else:
                self.assertEqual(response.status_code, HTTPStatus.OK)


    @enable_deployment('BRC')
    def test_post_creates_request_pool_short_name(self):
        """Test that a POST request creates a
        SavioProjectAllocationRequest where the existing project to be pooled 
        with has a name that exceeds 15 chars, but the new project has a short name."""
        self.assertEqual(SavioProjectAllocationRequest.objects.count(), 0)

        computing_allowance = self.get_predominant_computing_allowance()
        allocation_period = get_current_allowance_year_period()

        view_name = 'savio_project_request_wizard'
        current_step_key = f'{view_name}-current_step'
        requested_name = 'test'
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
            '7-project': Project.objects.prefetch_related()[0].pk,
            current_step_key: '7'
        }
        details_data = {
            '8-name': requested_name, 
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
        # Mock user form requests 
        url = self.request_url()
        self.user_request(url=url, form_data=form_data)
        # Set user to superuser to submit approval form
        self.user.is_superuser = True
        self.user.save()
        # Set the request's state
        poolTool = TestSavioProjectReviewSetupViewNoPooling()
        new_project_request = poolTool.set_status()
        review_url = self.review_view_url(new_project_request.pk)
        requested_name = 'test' 
        justification = 25 * 'lol'
        response =poolTool.post_approval_data(\
            requested_name=requested_name,
            url=review_url,
            final_name=requested_name,
            justification=justification
        )
        # Will pass this test with no message since expected response to correct name is 302. 
        self.assertEqual(response.status_code, 302)
        
    
    @enable_deployment('BRC')
    def test_post_creates_request_pool_long_name(self):
        """Test that a POST request creates a
        SavioProjectAllocationRequest where the existing project to be pooled 
        with has a name that exceeds 15 chars, as does the new project"""
        self.assertEqual(SavioProjectAllocationRequest.objects.count(), 0)

        computing_allowance = self.get_predominant_computing_allowance()
        allocation_period = get_current_allowance_year_period()

        view_name = 'savio_project_request_wizard'
        current_step_key = f'{view_name}-current_step'
        requested_name = 'test'  
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
            '7-project': Project.objects.prefetch_related()[0].pk,
            current_step_key: '7'
        }
        details_data = {
            '8-name': requested_name, 
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
        self.user_request(url=url, form_data=form_data)
        # Set user to superuser to submit approval form
        self.user.is_superuser = True
        self.user.save()
        # Set the request's state
        poolTool = TestSavioProjectReviewSetupViewNoPooling()
        new_project_request = poolTool.set_status()
        review_url = self.review_view_url(new_project_request.pk)
        final_name = requested_name * 5
        justification = 'a' * 20
        response = poolTool.post_approval_data(\
            requested_name=requested_name,
            url=review_url,
            final_name=final_name,
            justification=justification
        )
        # Will pass this test with no message since expected response to correct name is 302. 
        self.assertEqual(response.status_code, 302)
        # 
