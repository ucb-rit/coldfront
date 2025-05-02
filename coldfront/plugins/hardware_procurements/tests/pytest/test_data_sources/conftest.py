import csv
import json
import os
import pytest

from .utils import MockUser


@pytest.fixture
def expected_hardware_procurements_data():
    """Return a list of dicts representing the expected output of the
    backend's fetch method, given the test data file as input, read from
    a JSON file."""
    test_dir_path = os.path.dirname(__file__)
    data_file_path = os.path.join(
        test_dir_path,
        'resources',
        'test_google_sheets_data_source_backend_expected_output_data.json')
    with open(data_file_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def google_sheet_data():
    """Return a list of lists containing test data, read from a TSV
    file, excluding the header."""
    test_dir_path = os.path.dirname(__file__)
    data_file_path = os.path.join(
        test_dir_path,
        'resources',
        'test_google_sheets_data_source_backend_data.tsv')
    with open(data_file_path, 'r') as f:
        reader = csv.reader(f, delimiter='\t')
        data = [row for row in reader]
    return data[1:]


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
