from coldfront.core.project.utils_.renewal_survey_backend.backends.base import BaseRenewalSurveyBackend

class PermissiveRenewalSurveyBackend(BaseRenewalSurveyBackend):
    """A backend for development purposes."""

    def validate_renewal_survey_completion(self, allocation_period_name, 
                                           project_name, pi_username):
        """ Always returns without raising Exception """
        return

    def get_renewal_survey_response(self, allocation_period_name, project_name, 
                            pi_username):
        """ Return None """
        return None
    
    def get_renewal_survey_url(self, allocation_period_name, pi, project_name, 
                               requester):
        """ Return None """
        return None
    