from coldfront.core.project.utils_.gspread.backends.base import BaseGSpreadBackend
from coldfront.core.project.utils_.renewal_utils import get_gspread_wks
from coldfront.core.project.utils_.renewal_utils import get_renewal_survey

from django.core.exceptions import ValidationError

class ProductionGSpreadBackend(BaseGSpreadBackend):
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
    
    def get_survey_response(self, allocation_period_name, project_name, 
                            pi_username):
        """ Takes information from the request object and returns an
         iterable of tuples representing the requester's survey answers. If no
         answer is detected, return None. The format of the tuple:
         ( question: string, answer: string ).  """

        gform_info = get_renewal_survey(allocation_period_name)
        if gform_info == None:
            return None

        wks = get_gspread_wks(gform_info['sheet_id'], 0)
        if wks == None:
            return None
        
        pis = wks.col_values(gform_info["sheet_data"]["pi_username_col"])
        projects = wks.col_values(gform_info["sheet_data"]["project_name_col"])

        all_responses = list(zip(pis, projects))
        key = (pi_username, project_name)

        if key not in all_responses:
            return None
        row_ind = all_responses.index(key) + 1

        questions = wks.row_values(1)
        response = wks.row_values(row_ind)

        return zip(questions, response)
