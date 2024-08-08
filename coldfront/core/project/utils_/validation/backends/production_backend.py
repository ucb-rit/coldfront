from coldfront.core.project.utils_.validation.backends.base import BaseValidatorBackend
from coldfront.core.project.utils_.renewal_utils import get_gspread_wks

from django.core.exceptions import ValidationError

class ProductionValidatorBackend(BaseValidatorBackend):
    """A backend that invokes gspread API which connects to Google Sheets
    to validate whether renewal survey was completed."""

    def is_renewal_survey_completed(self, sheet_id, sheet_data, key):
        wks = get_gspread_wks(sheet_id, 0)
        if wks == None:
            raise ValidationError(
                f'Unknown backend issue. '
                f'Please contact administrator if this persists.')

        periods = wks.col_values(sheet_data['allocation_period_col'])
        pis = wks.col_values(sheet_data['pi_username_col'])
        projects = wks.col_values(sheet_data['project_name_col'])
        responses = zip(periods, pis, projects)

        # TODO: Should checks be added for the requester?
        if key not in responses:
            raise ValidationError(
                f'Response for {key[1]}, {key[2]}, {key[0]} not detected.')
