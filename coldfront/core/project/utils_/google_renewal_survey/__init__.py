from django.conf import settings
from django.utils.module_loading import import_string

"""Methods relating to renewal survey completion validation."""


__all__ = [
    'get_backend',
    'is_renewal_survey_completed',
    'get_survey_response'
]

def get_backend(backend=None, **kwds):
    klass = import_string(backend or settings.GOOGLE_RENEWAL_SURVEY_BACKEND)
    return klass(**kwds)

def is_renewal_survey_completed(sheet_id, sheet_data, key):
    """TODO"""
    backend = get_backend()
    return backend.is_renewal_survey_completed(sheet_id, sheet_data, key)

def get_survey_response(allocation_period_name, project_name, pi_username):
    """TODO"""
    backend = get_backend()
    return backend.get_survey_response(
        allocation_period_name, project_name, pi_username)
