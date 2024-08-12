from coldfront.core.project.utils_.gspread.backends.base import BaseGSpreadBackend

class DummyGSpreadBackend(BaseGSpreadBackend):
    """A backend for testing purposes."""

    def is_renewal_survey_completed(self, sheet_id, survey_data, key):
        """ Always returns without causing ValidationError """
        return

    def get_survey_response(self, allocation_period_name, project_name, 
                            pi_username):
        """ Return None """
        return None