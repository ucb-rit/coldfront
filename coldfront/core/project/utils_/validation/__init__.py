from django.utils.module_loading import import_string

"""Methods relating to renewal survey completion validation."""


__all__ = [
    'get_validator',
    'is_renewal_survey_completed'
]


# def get_validator(backend=None, **kwds):
#     klass = import_string(backend or settings.BILLING_VALIDATOR_BACKEND)
#     return klass(**kwds)

def get_validator(backend=None, **kwds):
    # TODO: move this to settings
    DUMMY_VALIDATOR_BACKEND = \
        'coldfront.core.project.utils_.validation.backends.dummy.DummyValidatorBackend'
    REAL_VALIDATOR_BACKEND = \
        'coldfront.core.project.utils_.validation.backends.production_backend.ProductionValidatorBackend'
    klass = import_string(REAL_VALIDATOR_BACKEND)
    return klass(**kwds)

def is_renewal_survey_completed(sheet_id, sheet_data, key):
    
    validator = get_validator()
    return validator.is_renewal_survey_completed(sheet_id, sheet_data, key)