import gspread
import os

from .base import BaseDataSourceBackend


# TODO: Introduce caching here, or in the caller?


class GoogleSheetsDataSourceBackend(BaseDataSourceBackend):
    """A backend that fetches hardware procurement data from a Google
    Sheet."""

    # TODO: Take more filters?
    def fetch_hardware_procurements(self, user_data=None, status=None):
        sheet_data = self._fetch_sheet_data()

        metadata = self._load_sheet_metadata()
        sheet_columns = metadata['sheet_columns']

        if user_data is not None:
            user_emails = set(user_data['emails'])
        else:
            user_emails = {}

        # TODO: These should be canonical / consistent across backends.
        keys = [
            'status',
            'initial_inquiry_date',
            'pi_name',
            'pi_email',
            'poc_name',
            'poc_email',
            'hardware_type',
            'hardware_specification_details',
            'procurement_start_date',
            'jira_ticket',
            'order_received_date',
            'installed_date',
            'qos_provisioned_date',
            'id',
        ]

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
                pi_email = entry['pi_email']
                poc_email = entry['poc_email']
                if pi_email not in user_emails and poc_email not in user_emails:
                    continue

            if status is not None:
                if entry['status'] != status:
                    continue

            yield entry

    def _clean_sheet_value(self, column_name, column_value):
        """TODO"""
        if column_name == 'status':
            # TODO: Where are these canonical ones going to be stored so that
            #  forms can access them?
            pending = 'Pending'
            complete = 'Complete'
            inactive = 'Inactive'

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
            }
            raw_status = column_value.lower()
            if raw_status not in raw_to_canonical:
                raise ValueError(f'Unexpected status {raw_status}')
            return raw_to_canonical[raw_status]

        return column_value

    def _fetch_sheet_data(self, *args, **kwargs):
        """TODO"""
        metadata = self._load_sheet_metadata()

        credentials_file_path = metadata['credentials_file_path']
        if not os.path.isfile(credentials_file_path):
            raise FileNotFoundError(
                f'Could not find credentials file: {credentials_file_path}.')

        gc = gspread.service_account(filename=credentials_file_path)

        sheet_id = metadata['sheet_id']
        sh = gc.open_by_key(sheet_id)

        sheet_tab = metadata['sheet_tab']
        wks = sh.worksheet(sheet_tab)

        return wks.get_all_values()[3:]

    @staticmethod
    def _gsheet_column_to_index(column_str):
        """Convert a Google Sheets column str (e.g., "A", "AA") the
        corresponding zero-indexed number."""
        index = 0
        for char in column_str:
            index = index * 26 + (ord(char.upper()) - ord('A') + 1)
        return index - 1

    def _load_sheet_metadata(self):
        """Return a dict containing metadata about the Google Sheet that
        stores hardware procurement data."""
        # TODO: Load this from conf.
        return {}
