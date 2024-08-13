from django.conf import settings
from django.utils.module_loading import import_string

"""Methods relating to renewal survey completion validation."""


__all__ = [
    'get_backend',
    'is_renewal_survey_completed',
    'get_survey_response',
    'get_survey_url'
]

def get_backend(backend=None, **kwds):
    klass = import_string(backend or settings.RENEWAL_SURVEY_BACKEND)
    return klass(**kwds)

def is_renewal_survey_completed(sheet_id, sheet_data, key):
    """A backend that invokes gspread API which connects to Google Sheets
    to validate whether renewal survey was completed."""
    backend = get_backend()
    return backend.is_renewal_survey_completed(sheet_id, sheet_data, key)

def get_survey_response(allocation_period_name, project_name, pi_username):
    """Takes information from the request object and returns an
         iterable of tuples representing the requester's survey answers. If no
         answer is detected, return None. The format of the tuple:
         ( question: string, answer: string ). """
    backend = get_backend()
    return backend.get_survey_response(
        allocation_period_name, project_name, pi_username)

def get_survey_url(survey_data, parameters):
    """This function returns the unique link to a pre-filled form for the user 
    to fill out."""
    backend = get_backend()
    return backend.get_survey_url(survey_data, parameters)
