import pytest

from unittest.mock import MagicMock
from unittest.mock import patch

from .conftest import MockUser
from .conftest import mock_look_up_user_by_email

from .utils import CACHE_KEY
from .utils import CACHE_MODULE
from .utils import LOOK_UP_FUNC_MODULE
from .utils import MockCache

from ....utils.data_sources.backends.cached import HardwareProcurementsCacheManager


class MockHardwareProcurement(dict):
    """A mock for HardwareProcurement."""

    def __init__(self, _id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

        self._id = _id
        self['pi_emails'] = kwargs.get('pi_emails', [])
        self['poc_emails'] = kwargs.get('poc_emails', [])

    def get_id(self):
        return self._id

    def is_user_associated(self, user_data):
        return True


@pytest.fixture
def mock_hardware_procurements():
    """Return a list of MockHardwareProcurements."""
    return [
        MockHardwareProcurement(
            _id='4fcd2992',
            pi_emails=['pi1@email.com'],
            poc_emails=['poc1@email.com']),
        MockHardwareProcurement(
            _id='586fcf26',
            pi_emails=['pi1@email.com'],
            poc_emails=['poc2@email.com']),
        MockHardwareProcurement(
            _id='f3920d70',
            pi_emails=['pi2@email.com'],
            poc_emails=['poc1@email.com']),
        MockHardwareProcurement(
            _id='947ff714',
            pi_emails=['pi2@email.com'],
            poc_emails=['poc2@email.com']),
        MockHardwareProcurement(
            _id='ba0dcb06',
            pi_emails=['pi3@email.com'],
            poc_emails=['poc3@email.com']),
    ]


@pytest.fixture
def mock_hardware_procurements_by_id(mock_hardware_procurements):
    """Return a dict mapping procurement IDs to MockHardwareProcurement
    objects, as defined in the `mock_hardware_procurements` fixture."""
    return {hp.get_id(): hp for hp in mock_hardware_procurements}


class TestHardwareProcurementsCacheManager(object):
    """Unit and component tests for HardwareProcurementsCacheManager."""

    def setup_method(self):
        self._cache_key = CACHE_KEY
        self._cache_module = CACHE_MODULE
        self._look_up_func_module = LOOK_UP_FUNC_MODULE

    def _populate_cache(self, mock_cache, cache_manager,
                        mock_hardware_procurements, mock_look_up_user_by_email):
        """Run the `populate_cache` method of the given CacheManager
        object, which is backed by the given MockCache, on the given
        list of MockHardwareProcurements, using the given mock function
        for looking up users by email."""
        with patch(self._cache_module, mock_cache):
            with patch(
                    self._look_up_func_module,
                    side_effect=mock_look_up_user_by_email):
                cache_manager.populate_cache(mock_hardware_procurements)

    @pytest.mark.unit
    def test_clear_cache(self):
        mock_cache = MockCache()
        mock_cache[self._cache_key] = {'key1': 'value1', 'key2': 'value2'}

        assert self._cache_key in mock_cache
        cache_value = mock_cache[self._cache_key]
        assert cache_value['key1'] == 'value1'
        assert cache_value['key2'] == 'value2'

        with patch(self._cache_module, mock_cache):
            cache_manager = HardwareProcurementsCacheManager(self._cache_key)
            cache_manager.clear_cache()

        assert self._cache_key not in mock_cache

    @pytest.mark.component
    def test_get_cached_procurements(self, mock_hardware_procurements,
                                     mock_hardware_procurements_by_id,
                                     mock_look_up_user_by_email):
        mock_cache = MockCache()
        cache_manager = HardwareProcurementsCacheManager(self._cache_key)
        self._populate_cache(
            mock_cache, cache_manager, mock_hardware_procurements,
            mock_look_up_user_by_email)

        # The cache should contain exactly the entries defined in
        # `mock_hardware_procurements_by_id`, and nothing else.
        with patch(self._cache_module, mock_cache):
            for hardware_procurement in cache_manager.get_cached_procurements():
                procurement_id = hardware_procurement.get_id()
                assert procurement_id in mock_hardware_procurements_by_id
                assert (
                    hardware_procurement ==
                    mock_hardware_procurements_by_id[procurement_id])
                mock_hardware_procurements_by_id.pop(procurement_id)

        assert not mock_hardware_procurements_by_id

    @pytest.mark.component
    @pytest.mark.parametrize(
        ['user_data', 'expected_procurement_ids'],
        [
            ({'id': 0}, {'ba0dcb06'}),
            ({'id': 1}, {'4fcd2992', '586fcf26'}),
            ({'id': 2}, {'f3920d70', '947ff714'}),
            ({'id': 3}, {'4fcd2992', 'f3920d70'}),
            ({'id': 4}, {'586fcf26', '947ff714'}),
        ]
    )
    def test_get_cached_procurements_by_user(self, mock_hardware_procurements,
                                             mock_hardware_procurements_by_id,
                                             mock_look_up_user_by_email,
                                             user_data,
                                             expected_procurement_ids):
        mock_cache = MockCache()
        cache_manager = HardwareProcurementsCacheManager(self._cache_key)
        self._populate_cache(
            mock_cache, cache_manager, mock_hardware_procurements,
            mock_look_up_user_by_email)

        # The cache should contain exactly the entries defined in
        # `mock_hardware_procurements_by_id` that have IDs in
        # `expected_procurement_ids`, and nothing else.
        with patch(self._cache_module, mock_cache):
            for hardware_procurement in \
                    cache_manager.get_cached_procurements_for_user(user_data):
                procurement_id = hardware_procurement.get_id()
                assert procurement_id in expected_procurement_ids
                assert (
                    hardware_procurement ==
                    mock_hardware_procurements_by_id[procurement_id])
                expected_procurement_ids.remove(procurement_id)

        assert not expected_procurement_ids

    @pytest.mark.component
    @pytest.mark.parametrize(
        'user_data',
        [
            {'id': 0},
            {'id': 1},
            {'id': 2},
            {'id': 3},
            {'id': 4},
        ]
    )
    def test_get_cached_procurements_by_user_omits_if_not_associated(self,
                                                                     mock_hardware_procurements,
                                                                     mock_look_up_user_by_email,
                                                                     user_data):
        mock_cache = MockCache()
        cache_manager = HardwareProcurementsCacheManager(self._cache_key)
        self._populate_cache(
            mock_cache, cache_manager, mock_hardware_procurements,
            mock_look_up_user_by_email)

        with patch.object(
                MockHardwareProcurement, 'is_user_associated',
                return_value=False):
            # Nothing should be returned because the method should double check
            # that the user is associated with the cached procurement before
            # yielding.
            with patch(self._cache_module, mock_cache):
                generator = cache_manager.get_cached_procurements_for_user(
                    user_data)
                with pytest.raises(StopIteration) as exc_info:
                    next(generator)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        'cache_key_input',
        [0, ['str'], ('str', 'str'), {'str': 'str'}, None, True, False]
    )
    def test_init_validates_cache_key_type(self, cache_key_input):
        with pytest.raises(AssertionError) as exc_info:
            HardwareProcurementsCacheManager(cache_key_input)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        ['mock_cache_data', 'expected_output'],
        [
            ({}, False),
            ({'cache_key': {}}, True),
            ({'not_cache_key': {'number': 1}}, False),
        ]
    )
    def test_is_cache_populated(self, mock_cache_data, expected_output):
        mock_cache = MockCache()
        for key, value in mock_cache_data.items():
            mock_cache.set(key, value)

        cache_manager = HardwareProcurementsCacheManager(self._cache_key)
        with patch(self._cache_module, mock_cache):
            assert cache_manager.is_cache_populated() == expected_output

    @pytest.mark.unit
    @pytest.mark.parametrize(
        ['hardware_procurement', 'sorted_expected_user_ids'],
        [
            (
                MockHardwareProcurement(
                    _id='edf11235',
                    pi_emails=['pi1@email.com', 'pi2@email.com']),
                [1, 2],
            ),
            (
                MockHardwareProcurement(
                    _id='56531c1e',
                    pi_emails=['pi1@email.com'],
                    poc_emails=['poc1@email.com']),
                [1, 3],
            ),
            (
                MockHardwareProcurement(
                    _id='d47af261',
                    pi_emails=['pi2@email.com'],
                    poc_emails=['poc2@email.com']),
                [2, 4],
            ),
            (
                MockHardwareProcurement(
                    _id='565210ac',
                    poc_emails=['poc1@email.com', 'poc2@email.com']),
                [3, 4],
            ),
            # An email address does not map to an existing user.
            (
                MockHardwareProcurement(
                    _id='f3f885da',
                    pi_emails=['pi3@email.com'],
                    poc_emails=['poc1@email.com']),
                [3],
            ),
            # None of the email addresses map to existing users. The nonexistent
            # user ID (0) should be returned.
            (
                MockHardwareProcurement(
                    _id='344140b8',
                    pi_emails=['pi3@email.com'],
                    poc_emails=['poc3@email.com']),
                [0],
            )
        ]
    )
    def test_lookup_associated_user_ids(self, hardware_procurement,
                                        sorted_expected_user_ids,
                                        mock_look_up_user_by_email):
        cache_manager = HardwareProcurementsCacheManager(self._cache_key)
        with patch(
                self._look_up_func_module,
                side_effect=mock_look_up_user_by_email):
            actual_user_ids = cache_manager._lookup_associated_user_ids(
                hardware_procurement)

        actual_user_ids.sort()
        assert actual_user_ids == sorted_expected_user_ids

    @pytest.mark.component
    def test_populate_cache(self, mock_hardware_procurements,
                            mock_hardware_procurements_by_id,
                            mock_look_up_user_by_email):
        mock_cache = MockCache()
        cache_manager = HardwareProcurementsCacheManager(self._cache_key)
        self._populate_cache(
            mock_cache, cache_manager, mock_hardware_procurements,
            mock_look_up_user_by_email)

        # The cache should contain exactly the given HardwareProcurement objects
        # for each user, and nothing else.
        expected_procurement_ids_by_user = {
            0: {'ba0dcb06'},
            1: {'4fcd2992', '586fcf26'},
            2: {'f3920d70', '947ff714'},
            3: {'4fcd2992', 'f3920d70'},
            4: {'586fcf26', '947ff714'},
        }

        for user_id, user_procurements_by_id in mock_cache[
                self._cache_key].items():
            assert user_id in expected_procurement_ids_by_user

            expected_procurement_ids = expected_procurement_ids_by_user[user_id]
            for procurement_id, procurement in user_procurements_by_id.items():
                assert procurement_id in expected_procurement_ids
                assert (
                    procurement ==
                    mock_hardware_procurements_by_id[procurement_id])
                expected_procurement_ids.remove(procurement_id)

            assert not expected_procurement_ids

            expected_procurement_ids_by_user.pop(user_id)

        assert not expected_procurement_ids_by_user
