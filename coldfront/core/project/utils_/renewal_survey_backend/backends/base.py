from abc import ABC
from abc import abstractmethod

class BaseRenewalSurveyBackend(ABC):
    """An interface for accessing GSpread API using any of a number of 
    backends."""
    @abstractmethod
    def is_renewal_survey_completed(self, sheet_id, survey_data, key):
        """Return whether the Google renewal survey has been completed"""
        pass

    @abstractmethod
    def get_survey_response(self, allocation_period_name, project_name, 
                            pi_username):
        """Return the question and answers of a particular survey response."""
        pass

    @abstractmethod
    def get_survey_url(self, survey_data, parameters):
        """This function returns the unique link to a pre-filled form for the
          user to fill out."""
        pass
