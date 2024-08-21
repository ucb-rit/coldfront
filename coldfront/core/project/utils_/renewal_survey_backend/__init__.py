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
    klass = import_string(backend or settings.RENEWAL_SURVEY_BACKEND)
    return klass(**kwds)

def validate_renewal_survey_completion(allocation_period_name, project_name, 
                                    pi_username, chosen_backend=None):
    """Return whether the renewal survey has been completed. If not, raise 
    ValidationError"""
    backend = chosen_backend or get_backend()
    return backend.validate_renewal_survey_completion(allocation_period_name, 
                                                      project_name, pi_username)

def get_renewal_survey_response(allocation_period_name, project_name, pi_username,
                        chosen_backend=None):
    """Takes information from the request object and returns an
         iterable of tuples representing the requester's survey answers. If no
         answer is detected, return None. The format of the tuple:
         ( question: string, answer: string ). """
    backend = chosen_backend or get_backend()
    return backend.get_renewal_survey_response(
        allocation_period_name, project_name, pi_username)

def get_renewal_survey_url(allocation_period_name, pi, project_name, requester, 
                           chosen_backend=None):
    """This function returns the unique link to a pre-filled form for the user 
    to fill out."""
    backend = chosen_backend or get_backend()
    return backend.get_renewal_survey_url(allocation_period_name, pi, 
                                          project_name, requester)
