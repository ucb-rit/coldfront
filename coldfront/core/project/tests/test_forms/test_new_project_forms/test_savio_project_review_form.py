from coldfront.core.utils.tests.test_base import TestBase
from coldfront.core.project.forms_.new_project_forms.approval_forms import SavioProjectReviewSetupForm


class SavioProjectReviewSetupFormTest(TestBase):
    def test_form_with_pooling_true(self):
        """Test the form with a final_name length of 50 chars and pooling==True"""
        form_data = {
            'pooling': True,
            'project_pk': 1, #Just for testing
            'requested_name': 'a' * 50,
            'computing_allowance': 'test_allowance'
        }
        form = SavioProjectReviewSetupForm(**form_data)
        import pdb; pdb.set_trace()
        self.assertTrue(form.is_valid())

    def test_form_with_pooling_false(self):
        """Test the form with a final_name length of 50 chars and pooling==False"""
        form_data = {
            'pooling': False,
            'project_pk': 1,
            'requested_name': 'a' * 50,
            'computing_allowance': 'test_allowance',
            'status': 'Pending'
        }
        form = SavioProjectReviewSetupForm(**form_data)
        self.assertFalse(form.is_valid(), """Form should not be valid as 
                         final_name exceeds max_length of 15 when pooling is 
                         False""")