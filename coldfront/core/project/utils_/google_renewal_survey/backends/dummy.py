from coldfront.core.project.utils_.google_renewal_survey.backends.base import BaseGoogleRenewalSurveyBackend

class DummyGoogleRenewalSurveyBackend(BaseGoogleRenewalSurveyBackend):
    """A backend for testing purposes."""

    def is_renewal_survey_completed(self, sheet_id, survey_data, key):
        """ Always returns without causing ValidationError """
        return

    def get_survey_response(self, allocation_period_name, project_name, 
                            pi_username):
        """ Return None """
        return None