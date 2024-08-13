from coldfront.core.project.utils_.renewal_survey_backend.backends.base import BaseRenewalSurveyBackend

class PermissiveRenewalSurveyBackend(BaseRenewalSurveyBackend):
    """A backend for testing purposes."""

    def is_renewal_survey_completed(self, sheet_id, survey_data, key):
        """ Always returns without causing ValidationError """
        return

    def get_survey_response(self, allocation_period_name, project_name, 
                            pi_username):
        """ Return None """
        return None
    
    def get_survey_url(self, survey_data, parameters):
        """Return None."""
        return None