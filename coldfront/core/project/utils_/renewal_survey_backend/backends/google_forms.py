import gspread
import json
import logging
import os

from django.conf import settings

from flags.state import flag_enabled

from coldfront.core.project.utils_.renewal_survey_backend.backends.base import BaseRenewalSurveyBackend


logger = logging.getLogger(__name__)


class GoogleFormsRenewalSurveyBackend(BaseRenewalSurveyBackend):
    """A backend that invokes which connects to Google Sheets to validate 
    whether renewal survey was completed. If there are issues connecting to 
    Google Sheets then the error is logged and no Exception is raised."""

    def validate_renewal_survey_completion(self, allocation_period_name, 
                                           project_name, pi_username):
        """Check whether the Google renewal survey has been completed. If not,
        raise an Exception."""
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
            responses = list(zip(periods, pis, projects))

        except Exception as e:
            message = (f'Something went wrong with connecting to Google Sheets.'
                        f' Allowing user to progress past step. Details:\n{e}')
            logger.exception(message)
            return
        
        # TODO: Should checks be added for the requester?
        key = (allocation_period_name, pi_username, 
                project_name)
        
        for i in range(len(responses) - 1, 0, -1):
            if key == responses[i]:
                return
        
        # Reaches here if a response was not found.
        raise Exception(
                f'Response for {pi_username}, {project_name}, '
                f'{allocation_period_name} not detected.')
    
    def get_renewal_survey_response(self, allocation_period_name, project_name, 
                            pi_username):
        """ Takes the identifying information for a response and finds the 
        specific survey response. Each question is then paired with its answer 
        in a tuple and the array of tuples in correct order are returned. If no 
        response is detected, return None. The format of the tuple: 
        ( question: string, answer: string ). """

        gform_info = self._get_renewal_survey(allocation_period_name)
        if gform_info is None:
            return None

        # The wks_id will almost always be 0
        wks = self._get_gspread_wks(gform_info['sheet_id'], 0)
        if wks is None:
            return None
        
        pis_column_coor = self._gsheet_column_to_index(
            gform_info["sheet_data"]["pi_username_col"])
        projs_column_coor = self._gsheet_column_to_index(
            gform_info["sheet_data"]["project_name_col"])
        
        pis = wks.col_values(pis_column_coor)
        projects = wks.col_values(projs_column_coor)

        all_responses = list(zip(pis, projects))
        key = (pi_username, project_name)

        row_ind = None
        for i in range(len(all_responses) - 1, 0, -1):
            if all_responses[i] == key:
                # Correct for Google Sheets not being zero-indexed
                row_ind = i + 1
                break

        if row_ind is None:
            return None

        questions = wks.row_values(1)
        response = wks.row_values(row_ind)

        return zip(questions, response)
    
    def get_renewal_survey_url(self, allocation_period_name, pi, project_name, 
                               requester):
        """ This function returns the unique link to a pre-filled form for the
          user to fill out. """
        
        gform_info = self._get_renewal_survey(allocation_period_name)
        if gform_info is None:
            return None

        # The wks_id will almost always be 0
        wks = self._get_gspread_wks(gform_info['sheet_id'], 0)
        if wks is None:
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

    @staticmethod
    def _gsheet_column_to_index(column_str):
        """Convert Google Sheets column (e.g., 'A', 'AA') to index number."""
        index = 0
        for char in column_str:
            index = index * 26 + (ord(char.upper()) - ord('A') + 1)
        return index

    @staticmethod
    def _get_gspread_wks(sheet_id, wks_id):
        """Given the spreadsheet ID and worksheet ID of a Google Sheet,
        returns a sheet that is editable."""
        credentials_file_path = settings.RENEWAL_SURVEY.get(
            'details', {}).get('credentials_file_path', '')
        assert isinstance(credentials_file_path, str)
        if not os.path.isfile(credentials_file_path):
            # TODO: Consider raising an Exception instaed.
            return None

        try:
            gc = gspread.service_account(filename=credentials_file_path)
        except:
            return None

        sh = gc.open_by_key(sheet_id)
        wks = sh.get_worksheet(wks_id)

        return wks

    @staticmethod
    def _get_renewal_survey(allocation_period_name):
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
        survey_data_path = settings.RENEWAL_SURVEY.get(
            'details', {}).get('survey_data_file_path', '')
        assert isinstance(survey_data_path, str)
        if not os.path.isfile(survey_data_path):
            # TODO: Consider raising an exception instead.
            return None

        with open(survey_data_path) as fp:
            data = json.load(fp)
            deployment = ''
            if flag_enabled('BRC_ONLY'):
                deployment = 'BRC'
            else:
                deployment = 'LRC'
            for elem in data:
                if (elem['allocation_period'] == allocation_period_name and
                        elem['deployment'] == deployment):
                    return elem
        return None
