from coldfront.core.project.utils_.validation.backends.base import BaseValidatorBackend

class DummyValidatorBackend(BaseValidatorBackend):
    """A backend for testing purposes."""

    def is_renewal_survey_completed(self, sheet_id, survey_data, key):
        """ Always returns without causing ValidationError """
        return