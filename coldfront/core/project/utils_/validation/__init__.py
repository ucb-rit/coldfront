from django.conf import settings
from django.utils.module_loading import import_string

"""Methods relating to renewal survey completion validation."""


__all__ = [
    'get_validator',
    'is_renewal_survey_completed'
]

def get_validator(backend=None, **kwds):
    klass = import_string(settings.RENEWAL_SURVEY_VALIDATOR_BACKEND)
    return klass(**kwds)

def is_renewal_survey_completed(sheet_id, sheet_data, key):
    """TODO"""
    validator = get_validator()
    return validator.is_renewal_survey_completed(sheet_id, sheet_data, key)