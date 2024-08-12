from coldfront.core.project.utils_.google_renewal_survey.backends.base import BaseGoogleRenewalSurveyBackend
from coldfront.core.project.utils_.renewal_utils import get_gspread_wks
from coldfront.core.project.utils_.renewal_utils import get_renewal_survey
from coldfront.core.project.utils_.renewal_utils import gsheet_column_to_index

from django.core.exceptions import ValidationError

class ProductionGoogleRenewalSurveyBackend(BaseGoogleRenewalSurveyBackend):
    """A backend that invokes gspread API which connects to Google Sheets
    to validate whether renewal survey was completed."""

    def is_renewal_survey_completed(self, sheet_id, sheet_data, key):
        wks = get_gspread_wks(sheet_id, 0)
        if wks == None:
            raise ValidationError(
                f'Unknown backend issue. '
                f'Please contact administrator if this persists.')

        periods_coor = gsheet_column_to_index(
            sheet_data['allocation_period_col'])
        pis_coor = gsheet_column_to_index(
            sheet_data['pi_username_col'])
        projects_coor = gsheet_column_to_index(
            sheet_data['project_name_col'])
        
        periods = wks.col_values(periods_coor)
        pis = wks.col_values(pis_coor)
        projects = wks.col_values(projects_coor)
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
        
        pis_column_coor = gsheet_column_to_index(
            gform_info["sheet_data"]["pi_username_col"])
        projs_column_coor = gsheet_column_to_index(
            gform_info["sheet_data"]["project_name_col"])
        
        pis = wks.col_values(pis_column_coor)
        projects = wks.col_values(projs_column_coor)

        all_responses = list(zip(pis, projects))
        key = (pi_username, project_name)

        if key not in all_responses:
            return None
        row_ind = all_responses.index(key) + 1

        questions = wks.row_values(1)
        response = wks.row_values(row_ind)

        return zip(questions, response)
