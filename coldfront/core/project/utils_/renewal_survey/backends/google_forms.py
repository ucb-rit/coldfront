import gspread
import json
import logging
import os

from django.conf import settings
from django.core.cache import cache

from coldfront.core.project.utils_.renewal_survey.backends.base import BaseRenewalSurveyBackend


logger = logging.getLogger(__name__)


class GoogleFormsRenewalSurveyBackend(BaseRenewalSurveyBackend):
    """A backend that supports a renewal survey hosted on Google
    Forms."""

    def is_renewal_survey_completed(self, allocation_period_name, project_name,
                                    pi_username):
        """Return whether there is a response for the given project and
        PI in the Google Sheet for the period."""

        # TODO: The current assumption is that the sheet only contains responses
        #  pertaining to one period, so it does not need to be checked,
        #  conserving a read request to the Google Sheets API. If this
        #  assumption changes (i.e., a sheet may be shared amongst multiple
        #  periods), restore the check.

        survey_data = self._load_renewal_survey_metadata(allocation_period_name)

        wks = self._get_gspread_wks(survey_data['sheet_id'])
        # periods_coor = self._gsheet_column_to_index(
        #     survey_data['sheet_data']['allocation_period_col'])
        pis_coor = self._gsheet_column_to_index(
            survey_data['sheet_data']['pi_username_col'])
        projects_coor = self._gsheet_column_to_index(
            survey_data['sheet_data']['project_name_col'])

        # periods = wks.col_values(periods_coor)
        pis = wks.col_values(pis_coor)
        projects = wks.col_values(projects_coor)
        # responses = list(zip(periods, pis, projects))
        responses = list(zip(pis, projects))

        # key = (allocation_period_name, pi_username, project_name)
        key = (pi_username, project_name)
        # Search later responses first.
        for i in range(len(responses) - 1, 0, -1):
            if responses[i] == key:
                return True

        return False

    def get_renewal_survey_response(self, allocation_period_name, project_name,
                                    pi_username):
        """Fetch the response for the given project and PI in the Google
        Sheet for the period. Return None if there is no response."""
        gform_info = self._load_renewal_survey_metadata(allocation_period_name)
        if gform_info is None:
            return None

        wks = self._get_gspread_wks(gform_info['sheet_id'])
        if wks is None:
            return None

        pis_column_coor = self._gsheet_column_to_index(
            gform_info['sheet_data']['pi_username_col'])
        projs_column_coor = self._gsheet_column_to_index(
            gform_info['sheet_data']['project_name_col'])

        pis = wks.col_values(pis_column_coor)
        projects = wks.col_values(projs_column_coor)

        all_responses = list(zip(pis, projects))
        key = (pi_username, project_name)

        row_ind = None
        # Search later responses first.
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
        """Return a pre-filled link to the Google Form for the period,
        wherein the following are pre-filled:
            - The name of the AllocationPeriod
            - The name and username of the PI (User object)
            - The name of the project
            - The name and username of the requester (User object)
        """
        gform_info = self._load_renewal_survey_metadata(allocation_period_name)
        if gform_info is None:
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
    def _get_gspread_wks(sheet_id, wks_id=0):
        """Given the spreadsheet ID and worksheet ID (default 0) of a
        Google Sheet, return a sheet that is editable.

        Raises:
            - FileNotFoundError
        """
        credentials_file_path = settings.RENEWAL_SURVEY.get(
            'details', {}).get('credentials_file_path', '')
        assert isinstance(credentials_file_path, str)
        if not os.path.isfile(credentials_file_path):
            raise FileNotFoundError(
                f'Could not find credentials file: {credentials_file_path}.')

        gc = gspread.service_account(filename=credentials_file_path)
        sh = gc.open_by_key(sheet_id)
        wks = sh.get_worksheet(wks_id)

        return wks

    @staticmethod
    def _gsheet_column_to_index(column_str):
        """Convert Google Sheets column (e.g., 'A', 'AA') to index number."""
        index = 0
        for char in column_str:
            index = index * 26 + (ord(char.upper()) - ord('A') + 1)
        return index

    def _load_renewal_survey_metadata(self, allocation_period_name):
        """Return a dict containing metadata about the Google Form and
        Google Sheet pertaining to the AllocationPeriod with the given
        name.

        The dict should be of the form:

            {
                # The ID of the Google Sheet linked to the Google Form.
                "sheet_id": "str",

                # The ID of the Google Form.
                "form_id": "str",

                # The name of the AllocationPeriod.
                "allocation_period": "str",

                # Indices (e.g., "X", "AC") of columns in which specific
                # form answers are stored in the sheet.
                "sheet_data": {
                    "allocation_period_col": "str",
                    "pi_username_col": "str",
                    "project_name_col": "str",
                },

                # The IDs of form questions, used to pre-fill answers.
                "form_question_ids": {
                    "allocation_period": "str",
                    "pi_name": "str",
                    "pi_username": "str",
                    "project_name": "str",
                    "requester_name": "str",
                    "requester_username": "str",
                },
            }

        These dicts are stored in a file on local disk, and cached in
        Django's caching mechanism.

        Raises:
            - FileNotFoundError
            - ValueError
        """
        renewal_survey_details = settings.RENEWAL_SURVEY.get('details', {})
        cache_key = renewal_survey_details.get('survey_data_cache_key', None)
        if cache_key is None:
            logger.error(
                'Failed to retrieve cache key from settings.RENEWAL_SURVEY.')

        cache_value = {}
        if cache_key is not None and cache_key in cache:
            cache_value = cache.get(cache_key)
            if allocation_period_name in cache_value:
                return cache_value[allocation_period_name]

        metadata = self._load_survey_metadata_from_file(allocation_period_name)

        cache_value[allocation_period_name] = metadata
        cache.set(cache_key, cache_value)

        return metadata

    @staticmethod
    def _load_survey_metadata_from_file(allocation_period_name):
        """Return a dict containing metadata about the Google Form and
        Google Sheet pertaining to the AllocationPeriod with the given
        name, sourced from a file on local disk.

        Raises:
            - FileNotFoundError
            - ValueError
        """
        renewal_survey_details = settings.RENEWAL_SURVEY.get('details', {})
        metadata_file_path = renewal_survey_details.get(
            'survey_data_file_path', None)
        if not os.path.isfile(metadata_file_path):
            raise FileNotFoundError(
                f'Could not find renewal survey data file: '
                f'{metadata_file_path}.')

        metadata = None
        with open(metadata_file_path, 'r') as f:
            metadata_dicts = json.load(f)
            for metadata_dict in metadata_dicts:
                if metadata_dict['allocation_period'] == allocation_period_name:
                    metadata = metadata_dict
                    break

        if metadata is None:
            raise ValueError(
                'Failed to load survey data for AllocationPeriod from file.')

        return metadata
