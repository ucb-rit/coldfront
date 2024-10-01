from abc import ABC
from abc import abstractmethod


class BaseRenewalSurveyBackend(ABC):
    """An interface for supporting a renewal survey hosted on any of a
    number of backends."""

    @abstractmethod
    def is_renewal_survey_completed(self, allocation_period_name, project_name,
                                    pi_username):
        """Return whether a survey has been completed for the given
        project and PI for the given allocation period.

        Parameters:
            - allocation_period_name (str): the name of an AllocationPeriod
            - project_name (str): the name of a Project
            - pi_username (str): the username of a PI of the Project

        Returns:
            - boolean

        Raises:
            - Exception, if any errors occur.
        """
        pass

    @abstractmethod
    def get_renewal_survey_response(self, allocation_period_name, project_name, 
                                    pi_username):
        """Return a list of (question, answer) tuples for the survey
        response from the given project and PI for the given allocation
        period. If there is no response, return None.

        Parameters
            - allocation_period_name (str): the name of an AllocationPeriod
            - project_name (str): the name of a Project
            - pi_username (str): the username of a PI of the Project

        Returns:
            - list of tuples (str, str), if there is a response
            - None, if there is no response

        Raises:
            - Exception, if any errors occur.
        """
        pass

    @abstractmethod
    def get_renewal_survey_url(self, allocation_period_name, pi, project_name, 
                               requester):
        """Return a unique link to the survey to be filled out by the
        given requesting user on behalf of the given project and PI for
        the given allocation period.

        Parameters:
            - allocation_period_name (str): the name of an AllocationPeriod
            - pi (User): the PI of the Project
            - project_name (str): the name of a Project
            - requester (User): the user making the renewal request and
              filling out the survey

        Returns:
            - str

        Raises:
            - Exception, if any errors occur.
        """
        pass
