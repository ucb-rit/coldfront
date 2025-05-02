from datetime import datetime


# The cache key to be used.
CACHE_KEY = 'cache_key'

# The module path to the cache module to be mocked.
CACHE_MODULE = (
    'coldfront.plugins.hardware_procurements.utils.data_sources.backends.'
    'cached.cache')

# A dict of columns matching those in the test data file.
GOOGLE_SHEET_COLUMNS = {
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

# The module path to the function for looking up users to be mocked.
LOOK_UP_FUNC_MODULE = (
    'coldfront.plugins.hardware_procurements.utils.data_sources.backends.'
    'cached.look_up_user_by_email')


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


def assert_procurement_expected(actual, expected):
    """Given a HardwareProcurement object and an expected dict
    representation of it, assert that the object is as expected."""
    assert actual.get_id() == expected['id']
    actual_data = actual.get_data()
    for k, v in expected['data'].items():
        if k.endswith('_date') and v is not None:
            v = datetime.strptime(v, '%Y-%m-%d').date()
        assert v == actual_data[k]
