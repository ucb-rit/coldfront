import gspread
import json
import os

from abc import abstractmethod
from collections import defaultdict
from datetime import date
from datetime import datetime

from ... import HardwareProcurement
from .base import BaseDataSourceBackend


class GoogleSheetsDataSourceBackend(BaseDataSourceBackend):
    """An interface that fetches hardware procurement data from a Google
    Sheet."""

    DATE_FORMAT = '%m/%d/%Y'

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
            'order_received_date',
            'installed_date',
            'expected_retirement_date',
        ]

        for key in self._extra_columns:
            keys.append(key)

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

            if self._should_exclude_procurement(entry):
                continue

            pi_emails_str = ','.join(sorted(entry['pi_emails']))
            hardware_type_str = entry['hardware_type']
            initial_inquiry_date_str = (
                entry['initial_inquiry_date'].strftime(self.DATE_FORMAT)
                if isinstance(entry['initial_inquiry_date'], date)
                else '')
            identifier = (
                pi_emails_str, hardware_type_str, initial_inquiry_date_str)

            hardware_procurement_obj = HardwareProcurement(
                *identifier, num_copies_by_identifier[identifier], entry)
            num_copies_by_identifier[identifier] += 1

            # TODO: Move filtering into a function?
            # Note: Filtering must occur *after* the instantiation of the
            # HardwareProcurement so that the number of copies is static, and,
            # consequently, the ID does not change.
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

            yield hardware_procurement_obj

    def _clean_sheet_value(self, column_name, value):
        """Clean the given value stored in the column with the given
        name. Currently-cleaned columns include:
            - expected_retirement_date
            - initial_inquiry_date
            - installed_date
            - order_received_data
            - pi_emails
            - poc_emails
            - procurement_start_date
            - status
        """
        date_fields = (
            'expected_retirement_date',
            'initial_inquiry_date',
            'installed_date',
            'order_received_date',
            'procurement_start_date',
        )

        value = value.strip()

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
            return [
                email.strip() for email in value.split(',') if email.strip()]

        elif column_name in date_fields:
            try:
                return datetime.strptime(value, self.DATE_FORMAT).date()
            except Exception as e:
                return None

        return value

    @property
    @abstractmethod
    def _extra_columns(self):
        """Return a tuple of strs denoting the names of extra columns
        specific to the deployment."""
        pass

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

    @abstractmethod
    def _should_exclude_procurement(self, procurement):
        """Return whether the given cleaned dict representing a
        procurement fetched from the sheet should be excluded."""
        pass


class BRCGoogleSheetsDataSourceBackend(GoogleSheetsDataSourceBackend):
    """A backend that fetches hardware procurement data from a Google
    Sheet, specifically for BRC."""

    @property
    def _extra_columns(self):
        return (
            'jira_ticket',
        )

    def _should_exclude_procurement(self, procurement):
        return False


class LRCGoogleSheetsDataSourceBackend(GoogleSheetsDataSourceBackend):
    """A backend that fetches hardware procurement data from a Google
    Sheet, specifically for LRC."""

    @property
    def _extra_columns(self):
        return (
            'buyer',
            'project_id',
            'requisition_id',
            'po_pcard',
        )

    def _should_exclude_procurement(self, procurement):
        if procurement['buyer'] != 'PI':
            return True
        return False
