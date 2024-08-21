from abc import ABC
from abc import abstractmethod

class BaseRenewalSurveyBackend(ABC):
    """An interface for accessing renewal survey responses using any of a number 
    of backends."""

    @abstractmethod
    def validate_renewal_survey_completion(self, allocation_period_name, 
                                           project_name, pi_username):
        """Check whether the renewal survey has been completed. If not,
        raise an Exception."""
        pass

    @abstractmethod
    def get_renewal_survey_response(self, allocation_period_name, project_name, 
                            pi_username):
        """Return the question and answers of a particular survey response."""
        pass

    @abstractmethod
    def get_renewal_survey_url(self, allocation_period_name, pi, project_name, 
                               requester):
        """This function returns the unique link to a pre-filled form for the
          user to fill out."""
        pass
