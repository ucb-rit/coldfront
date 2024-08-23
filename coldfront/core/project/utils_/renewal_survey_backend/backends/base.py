from abc import ABC
from abc import abstractmethod

class BaseRenewalSurveyBackend(ABC):
    """An interface for accessing renewal survey responses using any of a number 
    of backends."""

    @abstractmethod
    def validate_renewal_survey_completion(self, allocation_period_name, 
                                           project_name, pi_username):
        """ Validate whether the renewal survey has been completed for the 
        requested project, PI, and allocation period. If not, an exception is 
        raised. If an error occurs with the third-party service, no exception is 
        raised the requester is allowed to progress through the form. 
        
        - Inputs: 
          - allocation_period_name: Name of the allocation period the project 
              is being renewed under. Required to identify a specific response.
          - project_name: Name of the project being renewed. Required to 
              identify a specific response.
          - pi_username: Name of the PI whose allowance is being renewed. 
              Required to identify a specific response.

        - Output: None """
        pass

    @abstractmethod
    def get_renewal_survey_response(self, allocation_period_name, project_name, 
                            pi_username):
        """ Takes the identifying information for a response and finds the 
        specific survey response. Each question is then paired with its answer 
        in a tuple and the array of tuples in correct order are returned. If no 
        response is detected, return None. The format of the tuple: 
        ( question: string, answer: string ). 
        
        - Inputs:
          - Identifying information:
            - allocation_period_name
            - project_name
            - pi_username

        - Output:
          - Array of Tuples (question, response) """
        pass

    @abstractmethod
    def get_renewal_survey_url(self, allocation_period_name, pi, project_name, 
                               requester):
        """ This function returns the unique link to a pre-filled form for the
          user to fill out.
          
          - Inputs:
            - allocation_period_name: Name of the allocation period the project 
                is being renewed under. This is pre-filled into the Allocation 
                Period question on the form.
            - pi: The `User` object (from `django.contrib.auth.models`) for the 
                PI whose allowance is being renewed. The PI’s name and username 
                are pre-filled into the form.
            - project_name: Name of the project being renewed. This is 
                pre-filled into the Project Name question on the form.
            - requester: The `User` object (from `django.contrib.auth.models`) 
                for the user filling out the renewal request form. The 
                requester’s name and username are pre-filled into the form.

        - Output:
            - URL """
        pass
