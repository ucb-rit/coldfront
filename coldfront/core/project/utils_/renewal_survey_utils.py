import gspread
import json
from flags.state import flag_enabled

from django.conf import settings


# Utility functions for google renewal survey functionality

def gsheet_column_to_index(column_str):
    """Convert Google Sheets column (e.g., 'A', 'AA') to index number."""
    index = 0
    for char in column_str:
        index = index * 26 + (ord(char.upper()) - ord('A') + 1)
    return index

def get_gspread_wks(sheet_id, wks_id):
    """ Given the spreadsheet ID and worksheet ID of a Google Sheet, returns
     a sheet that is editable. """
    try:
        gc = gspread.service_account(filename='tmp/credentials.json')
    except:
        return None
    sh = gc.open_by_key(sheet_id)
    wks = sh.get_worksheet(wks_id)

    return wks

def get_renewal_survey(allocation_period_name):
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

    # If a different survey solution is used in the future, a different 
    # survey data file would be opened. Right now, the only one is 
    # google_survey_data.json
    survey_data_path = settings.RENEWAL_SURVEY_DATA_PATH
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

def renewal_survey_answer_conversion(question, all_answers):
    """ This function helps convert on-site renewal answers to correctly
     formatted strings for Google Sheets. """
    new_answer = ''
    if question == 'timestamp':
        new_answer = str(all_answers.request_time)
    elif question == 'which_brc_services_used':
        brc_services_converter = {
            'savio_hpc': 'Savio High Performance Computing and consulting',
            'condo_storage': 'Condo storage on Savio',
            'srdc': 'Secure Research Data & Computing (SRDC)',
            'aeod': 'Analytic Environments on Demand',
            'cloud_consulting': 'Cloud consulting (e.g., Amazon, Google, ' 
                        'Microsoft, XSEDE, UCB\'s Cloud Working Group)',
            'other': 'Other BRC consulting (e.g. assessing the '
                        'computation platform or resources appropriate '
                        'for your research workflow)',
            'none': 'None of the above'
        }

        answer = all_answers.renewal_survey_answers[question]
        for service in answer:
            new_answer += brc_services_converter[service] + ', '
    elif question == 'how_important_to_research_is_brc':
        answer = all_answers.renewal_survey_answers[question]
        if answer == '1':
            new_answer = 'Not at all important'
        elif answer == '2':
            new_answer = 'Somewhat important'
        elif answer == '3':
            new_answer = 'Important' 
        elif answer == '4':
            new_answer = 'Very important'
        elif answer == '5':
            new_answer = 'Essential'
        elif answer == '6':
            new_answer = 'Not applicable'
    elif question == 'which_open_ondemand_apps_used':
        ondemand_apps_converter = {
            'desktop': 'Desktop',
            'matlab': 'Matlab',
            'jupyter_notebook': 'Jupyter Notebook/Lab',
            'vscode_server': 'VS Code Server',
            'none': 'None of the above',
            'other': 'Other'
        }

        answer = all_answers.renewal_survey_answers[question]
        for app in answer:
            new_answer += ondemand_apps_converter[app] + ', '
    elif question == 'indicate_topic_interests':
        topic_interests_converter = {
            'have_visited_rdmp_website': 'I have visited the Research Data '
                    'Management Program web site.',
            'have_had_rdmp_event_or_consultation': 'I have participated in a '
                    'Research Data Management Program event or consultation.',
            'want_to_learn_more_and_have_rdm_consult': 'I am interested in the '
                    'Research Data Management Program; please have an RDM '
                    'consultant follow up with me.',
            'want_to_learn_security_and_have_rdm_consult': 'I am interested in '
                    'learning more about securing research data and/or secure '
                    'computation; please have an RDM consultant follow up with '
                    'me.',
            'interested_in_visualization_services': 'I am interested in '
                    'resources or services that support visualization of '
                    'research data.',
            'none_of_the_above': 'None of the above.'
        }

        answer = all_answers.renewal_survey_answers[question]
        for interest in answer:
            new_answer += topic_interests_converter[interest] + ', '
    elif question == 'allocation_period':
        new_answer = all_answers.allocation_period.name
    elif question == 'pi_name':
        new_answer = f'{all_answers.pi.first_name} {all_answers.pi.last_name}'
    elif question == 'pi_username':
        new_answer = all_answers.pi.username
    elif question == 'project_name':
        new_answer = all_answers.post_project.name
    elif question == 'requester_name':
        new_answer = f'{all_answers.requester.first_name} ' \
                        f'{all_answers.requester.last_name}'
    elif question == 'requester_username':
        new_answer = all_answers.requester.username
    else:
        answer = all_answers.renewal_survey_answers[question]
        new_answer = str(answer)
    new_answer = new_answer.rstrip(', ')
    return new_answer
