from django.conf import settings
from django.utils.module_loading import import_string

"""Methods relating to renewal survey backend."""


__all__ = [
    'get_backend',
    'is_renewal_survey_completed',
    'get_renewal_survey_response',
    'get_renewal_survey_url'
]


def get_backend(backend=None, **kwds):
    klass = import_string(backend or settings.RENEWAL_SURVEY['backend'])
    return klass(**kwds)


def is_renewal_survey_completed(allocation_period_name, project_name,
                                pi_username, backend=None):
    """Return whether a renewal survey has been completed for the
    given PI and project under the given AllocationPeriod.

    Parameters:
        - allocation_period_name (str): the name of the AllocationPeriod
          the allowance is being renewed under
        - project_name (str): the name of the Project the allowance is
          being renewed under
        - pi_username (str): the username of the PI whose allowance is
          being renewed
        - backend (BaseRenewalSurveyBackend): an optional renewal survey
          backend to use (default to the one defined in settings)

    Returns:
        - bool

    Raises:
        - Exception, if any errors occur.
    """
    backend = backend or get_backend()
    return backend.is_renewal_survey_completed(
        allocation_period_name, project_name, pi_username)


def get_renewal_survey_response(allocation_period_name, project_name, pi_username,
                        backend=None):
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
          - backend: Users can inject a backend rather than default to
              the backend determined in the settings.

        - Output:
          - Array of Tuples (question, response) """
    backend = backend or get_backend()
    return backend.get_renewal_survey_response(
        allocation_period_name, project_name, pi_username)


def get_renewal_survey_url(allocation_period_name, pi, project_name, requester, 
                           backend=None):
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
            - backend: Users can inject a backend rather than default to
                the backend determined in the settings.

        - Output:
            - URL """
    backend = backend or get_backend()
    return backend.get_renewal_survey_url(
        allocation_period_name, pi, project_name, requester)
