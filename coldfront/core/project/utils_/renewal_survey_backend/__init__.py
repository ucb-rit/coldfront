from django.conf import settings
from django.utils.module_loading import import_string

"""Methods relating to renewal survey backend."""


__all__ = [
    'get_backend',
    'validate_renewal_survey_completion',
    'get_renewal_survey_response',
    'get_renewal_survey_url'
]

def get_backend(backend=None, **kwds):
    klass = import_string(backend or settings.RENEWAL_SURVEY['backend'])
    return klass(**kwds)

def validate_renewal_survey_completion(allocation_period_name, project_name, 
                                    pi_username, chosen_backend=None):
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
          - chosen_backend: Users can inject a backend rather than default to 
              the backend determined in the settings.

        - Output: None """
    backend = chosen_backend or get_backend()
    return backend.validate_renewal_survey_completion(allocation_period_name, 
                                                      project_name, pi_username)

def get_renewal_survey_response(allocation_period_name, project_name, pi_username,
                        chosen_backend=None):
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
          - chosen_backend: Users can inject a backend rather than default to 
              the backend determined in the settings.

        - Output:
          - Array of Tuples (question, response) """
    backend = chosen_backend or get_backend()
    return backend.get_renewal_survey_response(
        allocation_period_name, project_name, pi_username)

def get_renewal_survey_url(allocation_period_name, pi, project_name, requester, 
                           chosen_backend=None):
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
            - chosen_backend: Users can inject a backend rather than default to 
                the backend determined in the settings.

        - Output:
            - URL """
    backend = chosen_backend or get_backend()
    return backend.get_renewal_survey_url(allocation_period_name, pi, 
                                          project_name, requester)
