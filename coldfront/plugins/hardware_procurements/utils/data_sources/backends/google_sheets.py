import gspread
import json
import os

from collections import defaultdict

from ... import HardwareProcurement
from .base import BaseDataSourceBackend


class GoogleSheetsDataSourceBackend(BaseDataSourceBackend):
    """A backend that fetches hardware procurement data from a Google
    Sheet."""

    def __init__(self, **kwargs):
        if 'config_file_path' in kwargs:
            config = self._load_config_from_file(kwargs['config_file_path'])
        else:
            config = kwargs

        self._credentials_file_path = config['credentials_file_path']
        self._sheet_id = config['sheet_id']
        self._sheet_tab = config['sheet_tab']
        self._sheet_columns = config['sheet_columns']
        self._header_row_index = config['header_row_index']

        # TODO: Validate.
        assert isinstance(self._credentials_file_path, str)
        assert isinstance(self._sheet_id, str)
        assert isinstance(self._sheet_tab, str)
        assert isinstance(self._sheet_columns, dict)
        assert isinstance(self._header_row_index, int)

    # TODO: Take more filters?
    def fetch_hardware_procurements(self, user_data=None, status=None):
        sheet_data = self._fetch_sheet_data()

        sheet_columns = self._sheet_columns

        if user_data is not None:
            user_emails = set(user_data['emails'])
        else:
            user_emails = {}

        # TODO: These should be canonical / consistent across backends.
        keys = [
            'status',
            'initial_inquiry_date',
            'pi_names',
            'pi_emails',
            'poc_names',
            'poc_emails',
            'hardware_type',
            'hardware_specification_details',
            'procurement_start_date',
            'jira_ticket',
            'order_received_date',
            'installed_date',
            'expected_retirement_date',
        ]

        # Maintain HardwareProcurement "copy numbers". Refer to the
        # HardwareProcurement class for more details.
        num_copies_by_identifier = defaultdict(int)

        for line in sheet_data:
            entry = {}
            for key in keys:
                value = line[
                    self._gsheet_column_to_index(
                        sheet_columns[f'{key}_col'])].strip()
                try:
                    cleaned_value = self._clean_sheet_value(key, value)
                except Exception as e:
                    cleaned_value = 'Unknown'
                entry[key] = cleaned_value

            # TODO: Move filtering into a function?
            if user_data is not None:
                is_user_a_pi = set.intersection(
                    user_emails, set(entry['pi_emails']))
                is_user_a_poc = set.intersection(
                    user_emails, set(entry['poc_emails']))
                if not (is_user_a_pi or is_user_a_poc):
                    continue
            if status is not None:
                if entry['status'] != status:
                    continue

            identifier = (
                ','.join(sorted(entry['pi_emails'])),
                entry['hardware_type'],
                entry['initial_inquiry_date'])
            hardware_procurement_obj = HardwareProcurement(
                *identifier, num_copies_by_identifier[identifier], entry)
            num_copies_by_identifier[identifier] += 1

            yield hardware_procurement_obj

    def _clean_sheet_value(self, column_name, value):
        """Clean the given value stored in the column with the given
        name. Currently-cleaned columns include:
            - status
            - pi_emails
            - poc_emails
        """
        if column_name == 'status':
            # TODO: Where are these canonical ones going to be stored so that
            #  forms can access them and avoid hard-coding?
            pending = 'Pending'
            complete = 'Complete'
            inactive = 'Inactive'
            retired = 'Retired'

            # A mapping from raw statuses in the spreadsheet to canonical
            # statuses in the web service. This accounts for typos, differences
            # in case, etc.
            raw_to_canonical = {
                'active': pending,
                'complete': complete,
                'completed': complete,
                'compelete': complete,
                'compeleted': complete,
                'inactive': inactive,
                'retired': retired,
            }
            raw_status = value.lower()
            if raw_status not in raw_to_canonical:
                raise ValueError(f'Unexpected status {raw_status}')
            return raw_to_canonical[raw_status]

        elif column_name == 'pi_emails' or column_name == 'poc_emails':
            return [email.strip() for email in value.split(',')]

        return value

    def _fetch_sheet_data(self):
        """Open the spreadsheet and specific tab, and return all values
        strictly after the header row."""
        credentials_file_path = self._credentials_file_path
        if not os.path.isfile(credentials_file_path):
            raise FileNotFoundError(
                f'Could not find credentials file: {credentials_file_path}.')

        gc = gspread.service_account(filename=credentials_file_path)
        sh = gc.open_by_key(self._sheet_id)
        wks = sh.worksheet(self._sheet_tab)

        return wks.get_all_values()[self._header_row_index:]

    @staticmethod
    def _gsheet_column_to_index(column_str):
        """Convert a Google Sheets column str (e.g., "A", "AA") the
        corresponding zero-indexed number."""
        index = 0
        for char in column_str:
            index = index * 26 + (ord(char.upper()) - ord('A') + 1)
        return index - 1

    def _load_config_from_file(self, config_file_path):
        """Read configuration from the given JSON file and return it as
        a dict."""
        with open(config_file_path, 'r') as f:
            return json.load(f)
