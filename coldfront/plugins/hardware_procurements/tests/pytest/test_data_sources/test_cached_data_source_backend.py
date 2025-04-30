import pytest

from unittest.mock import patch

from .conftest import assert_procurement_expected
from .conftest import cache_key
from .conftest import cache_module
from .conftest import expected_hardware_procurements_data
from .conftest import google_sheet_columns
from .conftest import google_sheet_data
from .conftest import look_up_func_module
from .conftest import MockCache
from .conftest import MockUser
from .conftest import mock_look_up_user_by_email
from .conftest import users_by_email

from ....utils.data_sources.backends.cached import CachedDataSourceBackend
from ....utils.data_sources.backends.cached import HardwareProcurementsCacheManager
from ....utils.data_sources.backends.google_sheets import GoogleSheetsDataSourceBackend


@pytest.fixture
def cached_data_source_kwargs(cache_key, google_sheet_columns):
    klass = GoogleSheetsDataSourceBackend
    cached_data_source = f'{klass.__module__}.{klass.__qualname__}'
    cached_data_source_options = {
        'credentials_file_path': '',
        'sheet_id': '',
        'sheet_tab': '',
        'sheet_columns': google_sheet_columns,
        'header_row_index': 1,
    }
    return {
        'cache_key': cache_key,
        'cached_data_source': cached_data_source,
        'cached_data_source_options': cached_data_source_options,
    }


@pytest.fixture
def cached_google_sheets_backend(cache_module, look_up_func_module, mock_cache,
                                 mock_look_up_user_by_email, google_sheet_data,
                                 cached_data_source_kwargs):
    """Return a CachedDataSourceBackend that caches data from a
    GoogleSheetsDataSourceBackend (with the given columns and data)
    under the given cache key. Mock the cache and a the function for
    looking up users.
    """
    with patch.object(
            GoogleSheetsDataSourceBackend, '_fetch_sheet_data',
            return_value=google_sheet_data):
        with patch('os.path.isfile', return_value=True) as mock_isfile:
            with patch(cache_module, mock_cache):
                with patch(look_up_func_module, mock_look_up_user_by_email):
                    cached_backend = CachedDataSourceBackend(
                        **cached_data_source_kwargs)
    return cached_backend


@pytest.fixture
def expected_hardware_procurements_data_by_id(expected_hardware_procurements_data):
    """Return a dict mapping procurement IDs to the procurements
    returned by the `expected_hardware_procurements_data` fixture."""
    procurement_data_by_id = {}
    for procurement_dict in expected_hardware_procurements_data:
        _id = procurement_dict['id']
        procurement_data_by_id[_id] = procurement_dict
    return procurement_data_by_id


@pytest.fixture
def mock_cache():
    """Return an instance of MockCache."""
    return MockCache()


class TestCachedDataSourceBackend(object):

    def _assert_fetch_output(self, cache_module, mock_cache,
                             look_up_func_module, mock_look_up_user_by_email,
                             backend, expected_hardware_procurements_data_by_id,
                             expected_ids, status=None, user_data=None):
        """Assert that the given backend's `fetch_hardware_procurements`
        method returns entries with the expected IDs from the given
        expected output data. Mock the cache and a the function for
        looking up users."""
        num_expected = len(expected_ids)
        expected_index = 0

        with patch(cache_module, mock_cache):
            with patch(look_up_func_module, mock_look_up_user_by_email):
                hardware_procurements = backend.fetch_hardware_procurements(
                    user_data=user_data, status=status)
                for hardware_procurement in hardware_procurements:
                    assert expected_index < num_expected
                    _id = hardware_procurement.get_id()
                    expected_hardware_procurement = \
                        expected_hardware_procurements_data_by_id[_id]
                    assert_procurement_expected(
                        hardware_procurement, expected_hardware_procurement)
                    expected_index += 1

        assert expected_index == num_expected

    @pytest.mark.component
    def test_init_instantiates_underlying_backend(self,
                                                  cached_google_sheets_backend):
        google_sheets_backend = cached_google_sheets_backend._backend
        assert isinstance(google_sheets_backend, GoogleSheetsDataSourceBackend)

        assert google_sheets_backend._credentials_file_path == ''
        assert google_sheets_backend._header_row_index == 1

    @pytest.mark.component
    def test_init_instantiates_cache_manager(self,
                                             cache_key,
                                             cached_google_sheets_backend):
        cache_manager = cached_google_sheets_backend._cache_manager
        assert isinstance(cache_manager, HardwareProcurementsCacheManager)
        assert cache_manager._cache_key == cache_key

    @pytest.mark.component
    def test_init_populates_cache(self, cache_module, mock_cache,
                                  cached_google_sheets_backend,
                                  expected_hardware_procurements_data_by_id):
        cache_manager = cached_google_sheets_backend._cache_manager
        with patch(cache_module, mock_cache):
            for hardware_procurement in cache_manager.get_cached_procurements():
                _id = hardware_procurement.get_id()
                assert _id in expected_hardware_procurements_data_by_id
                expected_hardware_procurement = \
                    expected_hardware_procurements_data_by_id.pop(_id)
                assert_procurement_expected(
                    hardware_procurement, expected_hardware_procurement)
        assert not expected_hardware_procurements_data_by_id

    @pytest.mark.component
    def test_init_skips_cache_populate_if_not_needed(self, cache_module,
                                                     mock_cache,
                                                     cached_data_source_kwargs):
        with patch.object(
                HardwareProcurementsCacheManager,
                'populate_cache') as mock_populate_cache:
            with patch.object(
                    HardwareProcurementsCacheManager, 'is_cache_populated',
                    return_value=True):
                with patch(cache_module, mock_cache):
                    cached_backend = CachedDataSourceBackend(
                        **cached_data_source_kwargs)
            assert mock_populate_cache.call_count == 0
            assert not cached_backend._cache_manager.is_cache_populated()

    @pytest.mark.component
    def test_clear_cache(self, cache_module, mock_cache,
                         cached_google_sheets_backend):
        cache_manager = cached_google_sheets_backend._cache_manager
        with patch(cache_module, mock_cache):
            assert cache_manager.is_cache_populated()
            cached_google_sheets_backend.clear_cache()
            assert not cache_manager.is_cache_populated()

    @pytest.mark.component
    @pytest.mark.parametrize(
        ['status', 'user_data', 'expected_ids'],
        [
            ('Complete', {'id': 1, 'emails': ['pi1@email.com']}, []),
            ('Pending', {'id': 3, 'emails': ['poc1@email.com']}, ['9b8aaee5']),
            ('Pending', {'id': 4, 'emails': ['poc2@email.com']}, ['7b79f48f']),
            ('Inactive', {'id': 1, 'emails': ['pi1@email.com']}, ['160d5698']),
            ('Inactive', {'id': 2, 'emails': ['pi2@email.com']}, ['160d5698']),
            ('Inactive', {'id': 3, 'emails': ['poc1@email.com']}, []),
            ('Retired', {'id': 3, 'emails': ['poc1@email.com']}, ['cc32e9da']),
            ('Retired', {'id': 4, 'emails': ['poc2@email.com']}, ['cc32e9da']),
        ]
    )
    def test_fetch_hardware_procurements_multiple_filters(self,
                                                          cache_module,
                                                          mock_cache,
                                                          look_up_func_module,
                                                          mock_look_up_user_by_email,
                                                          cached_google_sheets_backend,
                                                          expected_hardware_procurements_data_by_id,
                                                          status, user_data,
                                                          expected_ids):
        self._assert_fetch_output(
            cache_module,
            mock_cache,
            look_up_func_module,
            mock_look_up_user_by_email,
            cached_google_sheets_backend,
            expected_hardware_procurements_data_by_id,
            expected_ids,
            status=status,
            user_data=user_data)

    @pytest.mark.component
    def test_fetch_hardware_procurements_no_filters(self, cache_module,
                                                    mock_cache,
                                                    look_up_func_module,
                                                    mock_look_up_user_by_email,
                                                    cached_google_sheets_backend,
                                                    expected_hardware_procurements_data_by_id):
        expected_ids = expected_hardware_procurements_data_by_id.keys()
        self._assert_fetch_output(
            cache_module,
            mock_cache,
            look_up_func_module,
            mock_look_up_user_by_email,
            cached_google_sheets_backend,
            expected_hardware_procurements_data_by_id,
            expected_ids)

    @pytest.mark.component
    @pytest.mark.parametrize(
        ['status', 'expected_ids'],
        [
            ('Complete', ['a4eecf6e']),
            ('Inactive', ['160d5698']),
            ('Pending', ['9b8aaee5', '7b79f48f']),
            ('Retired', ['cc32e9da']),
        ]
    )
    def test_fetch_hardware_procurements_status_filter(self, cache_module,
                                                       mock_cache,
                                                       look_up_func_module,
                                                       mock_look_up_user_by_email,
                                                       cached_google_sheets_backend,
                                                       expected_hardware_procurements_data_by_id,
                                                       status, expected_ids):
        self._assert_fetch_output(
            cache_module,
            mock_cache,
            look_up_func_module,
            mock_look_up_user_by_email,
            cached_google_sheets_backend,
            expected_hardware_procurements_data_by_id,
            expected_ids,
            status=status)

    @pytest.mark.component
    @pytest.mark.parametrize(
        ['user_data', 'expected_ids'],
        [
            (
                {'id': 1, 'emails': ['pi1@email.com']},
                ['9b8aaee5', '7b79f48f', '160d5698'],
            ),
            (
                {'id': 2, 'emails': ['pi2@email.com']},
                ['a4eecf6e', '160d5698', 'cc32e9da'],
            ),
            (
                {'id': 3, 'emails': ['poc1@email.com']},
                ['9b8aaee5', 'cc32e9da'],
            ),
            (
                {'id': 4, 'emails': ['poc2@email.com']},
                ['7b79f48f', 'cc32e9da'],
            )
        ]
    )
    def test_fetch_hardware_procurements_user_data_filter(self, cache_module,
                                                          mock_cache,
                                                          look_up_func_module,
                                                          mock_look_up_user_by_email,
                                                          cached_google_sheets_backend,
                                                          expected_hardware_procurements_data_by_id,
                                                          user_data,
                                                          expected_ids):
        self._assert_fetch_output(
            cache_module,
            mock_cache,
            look_up_func_module,
            mock_look_up_user_by_email,
            cached_google_sheets_backend,
            expected_hardware_procurements_data_by_id,
            expected_ids,
            user_data=user_data)
