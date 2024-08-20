import gspread
import json
from flags.state import flag_enabled

from django.conf import settings
from django.core.exceptions import ValidationError
from coldfront.core.project.utils_.renewal_survey_backend.backends.base import BaseRenewalSurveyBackend

class GoogleRenewalSurveyBackend(BaseRenewalSurveyBackend):
    """A backend that invokes gspread API which connects to Google Sheets
    to validate whether renewal survey was completed."""

    def validate_renewal_survey_completion(self, allocation_period_name, 
                                           project_name, pi_username):
        """Check whether the Google renewal survey has been completed. If not,
        raise an error."""
        try:
            survey_data = self._get_renewal_survey(allocation_period_name)

            # The wks_id will almost always be 0
            wks = self._get_gspread_wks(survey_data['sheet_id'], 0)
            periods_coor = self._gsheet_column_to_index(
                survey_data['sheet_data']['allocation_period_col'])
            pis_coor = self._gsheet_column_to_index(
                survey_data['sheet_data']['pi_username_col'])
            projects_coor = self._gsheet_column_to_index(
                survey_data['sheet_data']['project_name_col'])
            
            periods = wks.col_values(periods_coor)
            pis = wks.col_values(pis_coor)
            projects = wks.col_values(projects_coor)
            responses = zip(periods, pis, projects)

            key = (allocation_period_name, pi_username, 
                   project_name)
        except:
            raise ValidationError(
                f'Unknown backend issue. '
                f'Please contact administrator if this persists.')
        
        # TODO: Should checks be added for the requester?
        if key not in responses:
            raise ValidationError(
                f'Response for {pi_username}, {project_name}, '
                f'{allocation_period_name} not detected.')
    
    def get_renewal_survey_response(self, allocation_period_name, project_name, 
                            pi_username):
        """ Takes information from the request object and returns an
         iterable of tuples representing the requester's survey answers. If no
         answer is detected, return None. The format of the tuple:
         ( question: string, answer: string ).  """

        gform_info = self._get_renewal_survey(allocation_period_name)
        if gform_info == None:
            return None

        # The wks_id will almost always be 0
        wks = self._get_gspread_wks(gform_info['sheet_id'], 0)
        if wks == None:
            return None
        
        pis_column_coor = self._gsheet_column_to_index(
            gform_info["sheet_data"]["pi_username_col"])
        projs_column_coor = self._gsheet_column_to_index(
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
    
    def get_renewal_survey_url(self, allocation_period_name, pi, project_name, 
                               requester):
        """This function returns the unique link to a pre-filled form for the
          user to fill out."""
        
        gform_info = self._get_renewal_survey(allocation_period_name)
        if gform_info == None:
            return None

        # The wks_id will almost always be 0
        wks = self._get_gspread_wks(gform_info['sheet_id'], 0)
        if wks == None:
            return None
        
        BASE_URL_ONE = 'https://docs.google.com/forms/d/e/'
        BASE_URL_TWO = '/viewform?usp=pp_url'

        url = BASE_URL_ONE + gform_info['form_id'] + BASE_URL_TWO

        PARAMETER_BASE_ONE = '&entry.'
        PARAMETER_BASE_TWO = '='
        
        question_ids_dict = gform_info['form_question_ids']
        for question in question_ids_dict.keys():
            value = ''
            if question == 'allocation_period':
                value = allocation_period_name
            elif question == 'pi_name':
                value = pi.first_name + '+' + pi.last_name
            elif question == 'pi_username':
                value = pi.username
            elif question == 'project_name':
                value = project_name
            elif question == 'requester_name':
                value = requester.first_name + '+' + \
                    requester.last_name
            elif question == 'requester_username':
                value = requester.username
            value = value.replace(' ', '+')
            url += PARAMETER_BASE_ONE + question_ids_dict[question] + \
                PARAMETER_BASE_TWO + value
        return url
    
    def _gsheet_column_to_index(self, column_str):
        """Convert Google Sheets column (e.g., 'A', 'AA') to index number."""
        index = 0
        for char in column_str:
            index = index * 26 + (ord(char.upper()) - ord('A') + 1)
        return index
    
    def _get_gspread_wks(self, sheet_id, wks_id):
        """ Given the spreadsheet ID and worksheet ID of a Google Sheet, returns
        a sheet that is editable. """
        try:
            gc = gspread.service_account(filename='tmp/credentials.json')
        except:
            return None
        sh = gc.open_by_key(sheet_id)
        wks = sh.get_worksheet(wks_id)

        return wks
    
    def _get_renewal_survey(self, allocation_period_name):
        """ Given the name of the allocation period, returns Google Form
        Survey info depending on LRC/BRC. The information is a dict containing:
            deployment: 'BRC/LRC',
            sheet_id: string,
            form_id: string,
            allocation_period: string,
            sheet_data: {
                allocation_period_col: int,
                pi_username_col: int,
                project_name_col: int
            } 
        The sheet_data values refer to the column coordinates of information used
        to enforce automatic check/block for the renewal form."""

        # TODO: Change
        survey_data_path = settings.GOOGLE_RENEWAL_SURVEY_DATA_PATH
        if survey_data_path == '':
            return None
        
        with open(survey_data_path) as fp:
            data = json.load(fp)
            deployment = ''
            if flag_enabled('BRC_ONLY'):
                deployment = 'BRC'
            else:
                deployment = 'LRC'
            for elem in data:
                if elem["allocation_period"] == allocation_period_name and elem["deployment"] == deployment:
                    return elem
        return None
    