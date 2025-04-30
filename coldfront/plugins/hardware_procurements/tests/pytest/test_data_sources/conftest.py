import csv
import json
import os
import pytest

from datetime import datetime


def assert_procurement_expected(actual, expected):
    """Given a HardwareProcurement object and an expected dict
    representation of it, assert that the object is as expected."""
    assert actual.get_id() == expected['id']
    actual_data = actual.get_data()
    for k, v in expected['data'].items():
        if k.endswith('_date') and v is not None:
            v = datetime.strptime(v, '%Y-%m-%d').date()
        assert v == actual_data[k]


@pytest.fixture
def cache_key():
    """Return the cache key to be used."""
    return 'cache_key'


@pytest.fixture
def cache_module():
    """Return the module path to the cache module to be mocked."""
    return (
        'coldfront.plugins.hardware_procurements.utils.data_sources.'
        'backends.cached.cache')


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
def look_up_func_module():
    """Return the module path to the function for looking up users by
    email to be mocked."""
    return (
        'coldfront.plugins.hardware_procurements.utils.data_sources.'
        'backends.cached.look_up_user_by_email')


class MockCache(object):
    """A mock for Django's cache."""

    def __init__(self):
        self._store = {}

    def get(self, key, default=None):
        return self._store.get(key, default)

    def set(self, key, value, timeout=None):
        self._store[key] = value

    def delete(self, key):
        if key in self._store:
            del self._store[key]

    def clear(self):
        self._store.clear()

    def __contains__(self, key):
        return key in self._store

    def __getitem__(self, key):
        if key in self._store:
            return self._store[key]
        raise KeyError(key)

    def __setitem__(self, key, value):
        self.set(key, value)


class MockUser(object):
    """A mock for Django's User object."""

    def __init__(self, user_id):
        self.id = user_id


@pytest.fixture
def users_by_email():
    """Return a dict mapping email addresses to MockUser objects that
    have IDs."""
    return {
        'pi1@email.com': MockUser(1),
        'pi2@email.com': MockUser(2),
        'poc1@email.com': MockUser(3),
        'poc2@email.com': MockUser(4),
    }


@pytest.fixture
def mock_look_up_user_by_email(users_by_email):
    """Return a function that returns a MockUser associated with a given
    email address, as defined in the `users_by_email` fixture."""

    def look_up(email):
        return users_by_email.get(email, None)

    return look_up
