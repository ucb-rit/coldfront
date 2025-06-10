import json
import pytest

from .utils import get_resource_absolute_file_path
from .utils import get_tsv_data
from .utils import MockUser


@pytest.fixture
def brc_expected_hardware_procurements_data():
    """Return a list of dicts representing the expected output of the
    backend's fetch method, given the BRC test data file as input, read
    from a JSON file."""
    data_file_path = get_resource_absolute_file_path(
        'test_brc_google_sheets_data_source_backend_expected_output_data.json')
    with open(data_file_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def brc_google_sheet_data():
    """Return a list of lists containing BRC test data, read from a TSV
    file, excluding the header."""
    data_file_path = get_resource_absolute_file_path(
        'test_brc_google_sheets_data_source_backend_data.tsv')
    return get_tsv_data(data_file_path)


@pytest.fixture
def lrc_expected_hardware_procurements_data():
    """Return a list of dicts representing the expected output of the
    backend's fetch method, given the LRC test data file as input, read
    from a JSON file."""
    data_file_path = get_resource_absolute_file_path(
        'test_lrc_google_sheets_data_source_backend_expected_output_data.json')
    with open(data_file_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def lrc_google_sheet_data():
    """Return a list of lists containing LRC test data, read from a TSV
    file, excluding the header."""
    data_file_path = get_resource_absolute_file_path(
        'test_lrc_google_sheets_data_source_backend_data.tsv')
    return get_tsv_data(data_file_path)


@pytest.fixture
def mock_look_up_user_by_email():
    """Return a function that returns a MockUser associated with a given
    email address."""
    users_by_email = {
        'pi1@email.com': MockUser(1),
        'pi2@email.com': MockUser(2),
        'poc1@email.com': MockUser(3),
        'poc2@email.com': MockUser(4),
    }

    def look_up(email):
        return users_by_email.get(email, None)

    return look_up
