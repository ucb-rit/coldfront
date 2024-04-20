from flags.state import flag_enabled

from coldfront.core.utils.tests.test_base import TestBase
from coldfront.core.project.views_.new_project_views.approval_views import SavioProjectRequestMixin
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

    #def create_test_superuser(self):
    #    self.user = User.objects.create_superuser(username='testuser', 
    #                                         email='test@example.com', 
    #                                         password='password123') 
    #    return self.user
    

    def setUp(self):
        """Set up test data"""
        super().setUp()
        # Create a user and set as super user
        #self.create_test_superuser()
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


        ## setup object for mock data
        #form_data = {} 
    
        ## Are there functions in TestBase to do this? 
        ## Flag for pooling?
        #allocation_request = True
        #form_data['pooling'] = allocation_request
        ## Requested name
        #test_name = "name" * 20 
        #form_data['requested_name'] = f'pc_{test_name}'
        ## final_name
        #form_data['final_name'] = f'pc_{test_name}'
        ## justification
        ## timestamp
        ## Create a project so I can have a project pk
        ## This may change
        #form_data['project_pk'] = self.request_obj.project.pk

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
