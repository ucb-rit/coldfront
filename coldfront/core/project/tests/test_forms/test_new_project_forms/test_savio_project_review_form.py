from django.core.exceptions import ImproperlyConfigured

from flags.state import flag_enabled
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.forms_.new_project_forms.approval_forms import SavioProjectReviewSetupForm
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.constants import LRCAllowances
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.utils.tests.test_base import TestBase
from coldfront.core.utils.common import utc_now_offset_aware
from datetime import timedelta


class SavioProjectReviewSetupFormTest(TestBase):
    def setUp(self):
        super().setUp()

        # Create a request.
        # TO DO create a name. 
        computing_allowance = self.get_predominant_computing_allowance()
        interface = ComputingAllowanceInterface()
        self.request_obj = SavioProjectReviewSetupForm.objects.create(

        )
        self.request_obj = SavioProjectAllocationRequest.objects.create(
            requester=self.requester,
            allocation_type=interface.name_short_from_name(
                computing_allowance.name),
            computing_allowance=computing_allowance,
            allocation_period=self.allocation_period,
            pi=self.pi,
            project=self.project,
            pool=False,
            survey_answers={},
            status=ProjectAllocationRequestStatusChoice.objects.get(
                name='Approved - Processing'),
            request_time=utc_now_offset_aware() - timedelta(days=1))

    def test_form_with_pooling_true(self):
        """Test the form with a final_name length of 50 chars and pooling==True"""
        initial = {
            'requested_name': self.requested_name,
            'computing_allowance': self.computing_allowance,
            'project_pk':1,
         }
                    

        form = SavioProjectReviewSetupForm(data=initial, pooling=True)
        print(f"Form is bound: {form.is_bound}")
        if not form.is_valid():
            print(form.errors) 
        self.assertTrue(form.is_valid()), "Form should be valid when pooling is true and final name exceeds 15 characters "

    def test_form_with_pooling_false(self):
        """Test the form with a final_name length of 50 chars and pooling==False"""
        form_data = {
            'pooling': False,
            'requested_name': self.requested_name,
            'project_pk': 1,
            'computing_allowance': 'test_allowance',
        }
        form = SavioProjectReviewSetupForm(**form_data)
        self.assertFalse(form.is_valid(), """Form should not be valid as 
                         final_name exceeds max_length of 15 when pooling is 
                         False""")