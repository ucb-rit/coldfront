from coldfront.core.utils.tests.test_base import TestBase
from coldfront.core.project.forms_.new_project_forms.approval_forms import SavioProjectReviewSetupForm


class SavioProjectReviewSetupFormTest(TestBase):
    def setUp(self):
        super().setUp()
        self.requested_name =  f"""rc_{'a'*50}""",
        self.computing_allowance =  'test_allowance'

    def test_form_with_pooling_true(self):
        """Test the form with a final_name length of 50 chars and pooling==True"""
        form_data = {
            'requested_name': self.requested_name,
            'project_pk': 1,
            'computing_allowance': self.computing_allowance,
            'pooling':True,
         }
        form = SavioProjectReviewSetupForm(**form_data) 
        import pdb; pdb.set_trace()
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