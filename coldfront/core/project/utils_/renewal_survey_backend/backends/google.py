from coldfront.core.project.utils_.renewal_survey_backend.backends.base import BaseRenewalSurveyBackend
from coldfront.core.project.utils_.renewal_survey_utils import get_gspread_wks
from coldfront.core.project.utils_.renewal_survey_utils import get_renewal_survey
from coldfront.core.project.utils_.renewal_survey_utils import gsheet_column_to_index

from django.core.exceptions import ValidationError

class GoogleRenewalSurveyBackend(BaseRenewalSurveyBackend):
    """A backend that invokes gspread API which connects to Google Sheets
    to validate whether renewal survey was completed."""

    def validate_renewal_survey_completion(self, allocation_period_name, 
                                           project_name, pi_username):
        """Check whether the Google renewal survey has been completed. If not,
        raise an error."""
        try:
            survey_data = get_renewal_survey(allocation_period_name)

            # The wks_id will almost always be 0
            wks = get_gspread_wks(survey_data['sheet_id'], 0)
            periods_coor = gsheet_column_to_index(
                survey_data['sheet_data']['allocation_period_col'])
            pis_coor = gsheet_column_to_index(
                survey_data['sheet_data']['pi_username_col'])
            projects_coor = gsheet_column_to_index(
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

        gform_info = get_renewal_survey(allocation_period_name)
        if gform_info == None:
            return None

        # The wks_id will almost always be 0
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
    
    def get_renewal_survey_url(self, allocation_period_name, pi, project_name, 
                               requester):
        """This function returns the unique link to a pre-filled form for the
          user to fill out."""
        
        gform_info = get_renewal_survey(allocation_period_name)
        if gform_info == None:
            return None

        # The wks_id will almost always be 0
        wks = get_gspread_wks(gform_info['sheet_id'], 0)
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
    