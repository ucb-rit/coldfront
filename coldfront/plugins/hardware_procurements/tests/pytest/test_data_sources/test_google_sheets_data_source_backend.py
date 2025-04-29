import csv
import json
import os
import pytest

from datetime import date
from datetime import datetime

from unittest.mock import MagicMock
from unittest.mock import mock_open
from unittest.mock import patch

from ....utils import HardwareProcurement
from ....utils.data_sources.backends.google_sheets import GoogleSheetsDataSourceBackend


@pytest.fixture
def backend_from_google_sheet_columns(google_sheet_columns):
    """Return a GoogleSheetsDataSourceBackend based on the columns
    defined in `google_sheet_columns`, and with a header row index of
    1."""
    backend = GoogleSheetsDataSourceBackend(
        credentials_file_path='',
        sheet_id='',
        sheet_tab='',
        sheet_columns=google_sheet_columns,
        header_row_index=1)
    return backend


@pytest.fixture
def google_sheet_data():
    """Return a list of lists containing test data, read from a TSV
    file, excluding the header."""
    test_dir_path = os.path.dirname(__file__)
    data_file_path = os.path.join(
        test_dir_path,
        'test_google_sheets_data_source_backend_data.tsv')
    with open(data_file_path, 'r') as f:
        reader = csv.reader(f, delimiter='\t')
        data = [row for row in reader]
    return data[1:]


@pytest.fixture
def google_sheet_columns():
    """Return a dict of columns matching those in the test data file."""
    return {
        'status_col': 'A',
        'initial_inquiry_date_col': 'B',
        'pi_names_col': 'C',
        'pi_emails_col': 'D',
        'poc_names_col': 'E',
        'poc_emails_col': 'F',
        'hardware_type_col': 'G',
        'hardware_specification_details_col': 'H',
        'procurement_start_date_col': 'I',
        'jira_ticket_col': 'J',
        'order_received_date_col': 'K',
        'installed_date_col': 'L',
        'expected_retirement_date_col': 'M',
    }


@pytest.fixture
def expected_hardware_procurements_data():
    """Return a list of dicts representing the expected output of the
    backend's fetch method, given the test data file as input, read from
    a JSON file."""
    test_dir_path = os.path.dirname(__file__)
    data_file_path = os.path.join(
        test_dir_path,
        'test_google_sheets_data_source_backend_expected_output_data.json')
    with open(data_file_path, 'r') as f:
        return json.load(f)


@pytest.mark.component
class TestGoogleSheetsDataSourceBackendComponent(object):
    """Component tests for GoogleSheetsDataSourceBackend."""

    @staticmethod
    def _assert_procurement_expected(actual, expected):
        """Given a HardwareProcurement object and an expected dict
        representation of it, assert that the object is as
        expected."""
        assert actual.get_id() == expected['id']
        actual_data = actual.get_data()
        for k, v in expected['data'].items():
            if k.endswith('_date') and v is not None:
                v = datetime.strptime(v, '%Y-%m-%d').date()
            assert v == actual_data[k]

    def _assert_fetch_output(self, input_data, backend, expected_output_data,
                             expected_ids=None, status=None, user_data=None):
        """Assert that, given the input data and optional status and/or
        user_data filters, the given backend's
        `fetch_hardware_procurements` method returns entries with the
        expected IDs from the given expected output data. If no expected
        IDs are given, assert that all expected output is fetched."""
        with patch.object(
                backend, '_fetch_sheet_data', return_value=input_data):
            if expected_ids is not None:
                num_expected = len(expected_ids)
            else:
                num_expected = len(expected_output_data)
            expected_index = 0

            for hardware_procurement in backend.fetch_hardware_procurements(
                    user_data=user_data, status=status):
                assert expected_index < num_expected
                if expected_ids is not None:
                    expected_hardware_procurement = \
                        next(
                            hp
                            for hp in expected_output_data
                            if hp['id'] == expected_ids[expected_index])
                else:
                    expected_hardware_procurement = expected_output_data[
                        expected_index]
                self._assert_procurement_expected(
                    hardware_procurement, expected_hardware_procurement)
                expected_index += 1

            assert expected_index == num_expected

    @pytest.mark.parametrize(
        ['status', 'user_data', 'expected_ids'],
        [
            ('Complete', {'emails': ['pi1@email.com']}, []),
            ('Pending', {'emails': ['poc1@email.com']}, ['9b8aaee5']),
            ('Pending', {'emails': ['poc2@email.com']}, ['7b79f48f']),
            ('Inactive', {'emails': ['pi1@email.com']}, ['160d5698']),
            ('Inactive', {'emails': ['pi2@email.com']}, ['160d5698']),
            ('Inactive', {'emails': ['poc1@email.com']}, []),
            ('Retired', {'emails': ['poc1@email.com']}, ['cc32e9da']),
            ('Retired', {'emails': ['poc2@email.com']}, ['cc32e9da']),
        ]
    )
    def test_fetch_hardware_procurements_multiple_filters(self, google_sheet_data,
                                                          backend_from_google_sheet_columns,
                                                          expected_hardware_procurements_data,
                                                          status, user_data,
                                                          expected_ids):
        self._assert_fetch_output(
            google_sheet_data,
            backend_from_google_sheet_columns,
            expected_hardware_procurements_data,
            expected_ids=expected_ids,
            status=status,
            user_data=user_data)

    def test_fetch_hardware_procurements_no_filters(self, google_sheet_data,
                                                    backend_from_google_sheet_columns,
                                                    expected_hardware_procurements_data):
        self._assert_fetch_output(
            google_sheet_data,
            backend_from_google_sheet_columns,
            expected_hardware_procurements_data)

    @pytest.mark.parametrize(
        ['status', 'expected_ids'],
        [
            ('Complete', ['a4eecf6e']),
            ('Inactive', ['160d5698']),
            ('Pending', ['9b8aaee5', '7b79f48f']),
            ('Retired', ['cc32e9da']),
        ]
    )
    def test_fetch_hardware_procurements_status_filter(self, google_sheet_data,
                                                       backend_from_google_sheet_columns,
                                                       expected_hardware_procurements_data,
                                                       status, expected_ids):
        self._assert_fetch_output(
            google_sheet_data,
            backend_from_google_sheet_columns,
            expected_hardware_procurements_data,
            expected_ids=expected_ids,
            status=status)

    @pytest.mark.parametrize(
        ['user_data', 'expected_ids'],
        [
            (
                {'emails': ['pi1@email.com']},
                ['9b8aaee5', '7b79f48f', '160d5698'],
            ),
            (
                {'emails': ['pi2@email.com']},
                ['a4eecf6e', '160d5698', 'cc32e9da'],
            ),
            (
                {'emails': ['poc1@email.com']},
                ['9b8aaee5', 'cc32e9da'],
            ),
            (
                {'emails': ['poc2@email.com']},
                ['7b79f48f', 'cc32e9da'],
            )
        ]
    )
    def test_fetch_hardware_procurements_user_data_filter(self,
                                                          google_sheet_data,
                                                          backend_from_google_sheet_columns,
                                                          expected_hardware_procurements_data,
                                                          user_data,
                                                          expected_ids):
        self._assert_fetch_output(
            google_sheet_data,
            backend_from_google_sheet_columns,
            expected_hardware_procurements_data,
            expected_ids=expected_ids,
            user_data=user_data)


@pytest.mark.unit
class TestGoogleSheetsDataSourceBackendUnit(object):
    """Unit tests for GoogleSheetsDataSourceBackend."""

    @pytest.mark.parametrize(
        ['column_name', 'value', 'expected_cleaned_value'],
        [
            ('expected_retirement_date', '01/01/1970', date(1970, 1, 1)),
            # Whitespace should be stripped.
            ('initial_inquiry_date', '  01/01/1970  ', date(1970, 1, 1)),
            ('installed_date', '01/01/1970', date(1970, 1, 1)),
            ('order_received_date', '01/01/1970', date(1970, 1, 1)),
            ('procurement_start_date', '01/01/1970', date(1970, 1, 1)),
            # A field not in the list of expected date fields should not be
            # transformed.
            ('unexpected_date', '01/01/1970', '01/01/1970'),
            # Malformed dates should result in None.
            ('expected_retirement_date', '01-01-1970', None),
        ]
    )
    def test_clean_sheet_value_dates(self, column_name, value,
                                     expected_cleaned_value):
        kwargs = self._get_backend_kwargs()
        backend = GoogleSheetsDataSourceBackend(**kwargs)
        cleaned_value = backend._clean_sheet_value(column_name, value)
        assert cleaned_value == expected_cleaned_value

    @pytest.mark.parametrize(
        ['column_name', 'value', 'expected_cleaned_value'],
        [
            # Whitespace should be stripped.
            (
                'pi_emails',
                '  pi1@email.com,pi2@email.com  ',
                ['pi1@email.com', 'pi2@email.com']
            ),
            (
                'poc_emails',
                'poc1@email.com  ,  poc2@email.com',
                ['poc1@email.com', 'poc2@email.com']
            ),
        ]
    )
    def test_clean_sheet_value_emails(self, column_name, value,
                                      expected_cleaned_value):
        kwargs = self._get_backend_kwargs()
        backend = GoogleSheetsDataSourceBackend(**kwargs)
        cleaned_value = backend._clean_sheet_value(column_name, value)
        assert cleaned_value == expected_cleaned_value

    @pytest.mark.parametrize(
        ['column_name', 'value', 'expected_cleaned_value'],
        [
            ('status', 'active', 'Pending'),
            # Statuses should be case-insensitive.
            ('status', 'ACTIVE', 'Pending'),
            # Typos and variations in the sheet should be accounted for.
            ('status', 'complete', 'Complete'),
            ('status', 'completed', 'Complete'),
            ('status', 'compelete', 'Complete'),
            ('status', 'compeleted', 'Complete'),
            # Whitespace should be stripped.
            ('status', '  inactive', 'Inactive'),
            ('status', 'retired  ', 'Retired'),
        ]
    )
    def test_clean_sheet_value_status(self, column_name, value,
                                      expected_cleaned_value):
        kwargs = self._get_backend_kwargs()
        backend = GoogleSheetsDataSourceBackend(**kwargs)
        cleaned_value = backend._clean_sheet_value(column_name, value)
        assert cleaned_value == expected_cleaned_value

    def test_clean_sheet_value_status_unexpected(self):
        kwargs = self._get_backend_kwargs()
        backend = GoogleSheetsDataSourceBackend(**kwargs)
        with pytest.raises(ValueError, match='Unexpected status') as exc_info:
            backend._clean_sheet_value('status', 'unknown')

    def test_fetch_sheet_data_file_not_found(self):
        backend = GoogleSheetsDataSourceBackend(
            credentials_file_path='nonexistent.json',
            sheet_id='mock_sheet_id',
            sheet_tab='mock_tab',
            sheet_columns={},
            header_row_index=1)

        with pytest.raises(
                FileNotFoundError, match='Could not find credentials file'):
            backend._fetch_sheet_data()

    def test_fetch_sheet_data_returned_values(self):
        with patch('os.path.isfile', return_value=True) as mock_isfile:
            with patch('gspread.service_account') as mock_service_account:
                mock_gspread = MagicMock()
                mock_service_account.return_value = mock_gspread
                mock_sheet = mock_gspread.open_by_key.return_value
                mock_worksheet = mock_sheet.worksheet.return_value
                mock_worksheet.get_all_values.return_value = [
                    ['Header1', 'Header2'],
                    ['Value1', 'Value2'],
                ]

                credentials_file_path = 'mock_credentials.json'
                sheet_id = 'mock_sheet_id'
                sheet_tab = 'mock_tab'
                backend = GoogleSheetsDataSourceBackend(
                    credentials_file_path=credentials_file_path,
                    sheet_id=sheet_id,
                    sheet_tab=sheet_tab,
                    sheet_columns={},
                    header_row_index=1,
                )

                result = backend._fetch_sheet_data()
                # The header row is skipped.
                assert result == [['Value1', 'Value2']]

                mock_service_account.assert_called_once_with(
                    filename=credentials_file_path)
                mock_gspread.open_by_key.assert_called_once_with(sheet_id)
                mock_sheet.worksheet.assert_called_once_with(sheet_tab)
                mock_worksheet.get_all_values.assert_called_once()

            mock_isfile.assert_called_once_with(credentials_file_path)

    @pytest.mark.parametrize(
        ['column_str', 'expected_index'],
        [
            ('A', 0),
            ('B', 1),
            ('C', 2),
            ('Z', 25),
            ('AA', 26),
            ('AB', 27),
            ('AZ', 51),
            ('BA', 52),
            ('ZZ', 701),
        ]
    )
    def test_gsheet_column_to_index(self, column_str, expected_index):
        kwargs = self._get_backend_kwargs()
        backend = GoogleSheetsDataSourceBackend(**kwargs)
        index = backend._gsheet_column_to_index(column_str)
        assert index == expected_index

    def test_init_from_file_sets_attributes(self):
        mock_config_file_path = 'mock_config.json'
        mock_config = {
            'credentials_file_path': 'mock_credentials.json',
            'sheet_id': 'mock_sheet_id',
            'sheet_tab': 'mock_tab',
            'sheet_columns': {},
            'header_row_index': 1,
        }

        with patch('builtins.open', mock_open(read_data='')) as mock_file:
            with patch('json.load', return_value=mock_config) as mock_json_load:
                backend = GoogleSheetsDataSourceBackend(
                    config_file_path=mock_config_file_path)
                assert (
                    backend._credentials_file_path ==
                    mock_config['credentials_file_path'])
                assert backend._sheet_id == mock_config['sheet_id']
                assert backend._sheet_tab == mock_config['sheet_tab']
                assert backend._sheet_columns == mock_config['sheet_columns']
                assert (
                    backend._header_row_index ==
                    mock_config['header_row_index'])

                mock_json_load.assert_called_once()
            mock_file.assert_called_once_with(mock_config_file_path, 'r')

    @pytest.mark.parametrize(
        'kwarg',
        [
            'credentials_file_path',
            'sheet_id',
            'sheet_tab',
            'sheet_columns',
            'header_row_index',
        ]
    )
    def test_init_kwarg_missing(self, kwarg):
        kwargs = self._get_backend_kwargs()
        del kwargs[kwarg]
        with pytest.raises(KeyError):
            GoogleSheetsDataSourceBackend(**kwargs)

    @pytest.mark.parametrize(
        ['kwarg', 'value'],
        [
            ('credentials_file_path', 123),
            ('sheet_id', 123),
            ('sheet_tab', 123),
            ('sheet_columns', 123),
            ('header_row_index', '123'),
        ]
    )
    def test_init_kwarg_type_unexpected(self, kwarg, value):
        kwargs = self._get_backend_kwargs()
        kwargs[kwarg] = value
        with pytest.raises(AssertionError):
            GoogleSheetsDataSourceBackend(**kwargs)

    def test_init_sets_attributes(self):
        kwargs = self._get_backend_kwargs()
        backend = GoogleSheetsDataSourceBackend(**kwargs)
        assert backend._credentials_file_path == kwargs['credentials_file_path']
        assert backend._sheet_id == kwargs['sheet_id']
        assert backend._sheet_tab == kwargs['sheet_tab']
        assert backend._sheet_columns == kwargs['sheet_columns']
        assert backend._header_row_index == kwargs['header_row_index']

    @staticmethod
    def _get_backend_kwargs(credentials_file_path='',
                           sheet_id='', sheet_tab='',
                           sheet_columns=None, header_row_index=0):
        return {
            'credentials_file_path': credentials_file_path,
            'sheet_id': sheet_id,
            'sheet_tab': sheet_tab,
            'sheet_columns': sheet_columns or {},
            'header_row_index': header_row_index,
        }
