from coldfront.core.project.utils_.renewal_survey.backends.base import BaseRenewalSurveyBackend


class PermissiveRenewalSurveyBackend(BaseRenewalSurveyBackend):
    """A backend that always reports that a survey has been
    completed."""

    def is_renewal_survey_completed(self, allocation_period_name, project_name,
                                    pi_username):
        """Always report that a survey has been completed."""
        return True

    def get_renewal_survey_response(self, allocation_period_name, project_name, 
                                    pi_username):
        """Return an empty list of responses."""
        return []

    def get_renewal_survey_url(self, allocation_period_name, pi, project_name,
                               requester):
        """Return an empty string."""
        return ''
