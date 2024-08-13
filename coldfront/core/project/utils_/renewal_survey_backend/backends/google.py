from coldfront.core.project.utils_.renewal_survey_backend.backends.base import BaseRenewalSurveyBackend
from coldfront.core.project.utils_.renewal_utils import get_gspread_wks
from coldfront.core.project.utils_.renewal_utils import get_renewal_survey
from coldfront.core.project.utils_.renewal_utils import gsheet_column_to_index

from django.core.exceptions import ValidationError

class GoogleRenewalSurveyBackend(BaseRenewalSurveyBackend):
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
    
    def get_survey_url(self, survey_data, parameters):
        """This function returns the unique link to a pre-filled form for the
          user to fill out."""
        BASE_URL_ONE = 'https://docs.google.com/forms/d/e/'
        BASE_URL_TWO = '/viewform?usp=pp_url'
        url = BASE_URL_ONE + survey_data['form_id'] + BASE_URL_TWO

        PARAMETER_BASE_ONE = '&entry.'
        PARAMETER_BASE_TWO = '='

        question_ids_dict = survey_data['form_question_ids']
        for parameter in question_ids_dict.keys():
            value = ''
            if parameter == 'allocation_period':
                value = parameters['allocation_period'].name
            elif parameter == 'pi_name':
                value = parameters['PI'].user.first_name + '+' + \
                    parameters['PI'].user.last_name
            elif parameter == 'pi_username':
                value = parameters['PI'].user.username
            elif parameter == 'project_name':
                value = parameters['project_name']
            elif parameter == 'requester_name':
                value = parameters['requester'].first_name + '+' + \
                    parameters['requester'].last_name
            elif parameter == 'requester_username':
                value = parameters['requester'].username
            value = value.replace(' ', '+')
            url += PARAMETER_BASE_ONE + question_ids_dict[parameter] + \
                PARAMETER_BASE_TWO + value
        return url
    

def make_form_url(self, survey_data, dictionary):
        """ This function creates the Google Form URL with appropriate
         pre-filled parameters. """
        BASE_URL_ONE = 'https://docs.google.com/forms/d/e/'
        BASE_URL_TWO = '/viewform?usp=pp_url'
        url = BASE_URL_ONE + survey_data['form_id'] + BASE_URL_TWO

        PARAMETER_BASE_ONE = '&entry.'
        PARAMETER_BASE_TWO = '='

        question_ids_dict = survey_data['form_question_ids']
        for parameter in question_ids_dict.keys():
            value = ''
            if parameter == 'allocation_period':
                value = dictionary['allocation_period'].name
            elif parameter == 'pi_name':
                value = dictionary['PI'].user.first_name + '+' + \
                    dictionary['PI'].user.last_name
            elif parameter == 'pi_username':
                value = dictionary['PI'].user.username
            elif parameter == 'project_name':
                value = self.project_obj.name
            elif parameter == 'requester_name':
                value = self.request.user.first_name + '+' + \
                    self.request.user.last_name
            elif parameter == 'requester_username':
                value = self.request.user.username
            value = value.replace(' ', '+')
            url += PARAMETER_BASE_ONE + question_ids_dict[parameter] + \
                PARAMETER_BASE_TWO + value
        return url
