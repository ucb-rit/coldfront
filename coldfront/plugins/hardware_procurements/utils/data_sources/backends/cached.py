from coldfront.core.account.utils.queries import look_up_user_by_email

from django.core.cache import cache
from django.utils.module_loading import import_string

from .base import BaseDataSourceBackend


class CachedDataSourceBackend(BaseDataSourceBackend):
    """A backend that pre-fetches and caches all hardware procurement
    data from the given underlying data source backend, if needed, in
    the Django cache, and serves it from the cache."""

    def __init__(self, cache_key=None, cached_data_source=None,
                 cached_data_source_options=None):

        # TODO: Validate?
        assert isinstance(cache_key, str)
        assert isinstance(cached_data_source, str)
        assert isinstance(cached_data_source_options, dict)

        self._cache_key = cache_key

        # Instantiate the underlying data source backend.
        klass = import_string(cached_data_source)
        self._backend = klass(**cached_data_source_options)

        # Ensure that the cache is populated.
        self._cache_manager = HardwareProcurementsCacheManager(self._cache_key)
        self.populate_cache_if_needed()

    def clear_cache(self):
        """Clear the cache."""
        self._cache_manager.clear_cache()

    def fetch_hardware_procurements(self, user_data=None, status=None):
        if user_data is None:
            hardware_procurement_generator = \
                self._cache_manager.get_cached_procurements()
        else:
            hardware_procurement_generator = \
                self._cache_manager.get_cached_procurements_for_user(
                    user_data)
        for hardware_procurement in hardware_procurement_generator:
            if status is not None:
                if hardware_procurement['status'] != status:
                    continue
            yield hardware_procurement

    def populate_cache_if_needed(self):
        """If the cache is not populated, fetch data using the
        underlying backend, and populate it."""
        hardware_procurement_generator = \
            self._backend.fetch_hardware_procurements()
        if not self._cache_manager.is_cache_populated():
            self._cache_manager.populate_cache(hardware_procurement_generator)


class HardwareProcurementsCacheManager(object):
    """A class that manages the caching of HardwareProcurement objects.

    The cache is designed to enabled fast lookup of procurements and
    procurement IDs associated with a specific user.

    The following assumptions are made:
        - The total amount of procurement data is small enough (a few
          hundred records, < 1 KB each) to be stored locally and loaded
          into memory.
        - User IDs are unique, non-zero integers (e.g., database primary
          keys). The zero ID is reserved for procurements that are not
          associated with any user.
        - Procurement IDs are strs, as defined in HardwareProcurement.
        - A procurement may be associated with more than one user.

    The cache entry is structured as follows:

        self._cache_key: {
            # Procurement IDs and objects associated with user 1.
            1: {
                'a1b2c3d4': HardwareProcurement,
                '1a2b3c4d': HardwareProcurement,
            },
            # Procurement IDs and objects associated with user 2.
            2: {
                'abcdefgh': HardwareProcurement,
                '1a2b3c4d': HardwareProcurement,
            },
            # ...
            # Procurement IDs and objects associated with user N.
            N: {
                'hgfedcba': HardwareProcurement,
                'd4c3b2a1': HardwareProcurement,
            },
            # Procurement IDs and objects not associated any user.
            self.NONEXISTENT_USER_ID: {
                '4d3c2b1a': HardwareProcurement,
            },
        }
    """

    # An ID value to use to store data about procurements that are not
    # associated with any user in the database.
    NONEXISTENT_USER_ID = 0

    def __init__(self, cache_key):
        assert isinstance(cache_key, str)
        self._cache_key = cache_key

    def get_cached_procurements(self):
        """Return a generator that yields HardwareProcurement objects
        across all users."""
        assert self.is_cache_populated()
        procurements_by_user_id = cache.get(self._cache_key)
        for _, user_procurements in procurements_by_user_id.items():
            for _, hardware_procurement in user_procurements.items():
                yield hardware_procurement

    def get_cached_procurements_for_user(self, user_data):
        """Return a generator that yields HardwareProcurement objects
        associated with the user represented by the given
        UserInfoDict."""
        assert self.is_cache_populated()
        user_id = user_data['id']
        if user_id in cache.get(self._cache_key):
            user_procurements = cache.get(self._cache_key)[user_id]
            for _, hardware_procurement in user_procurements.items():
                # Entries stored in a user's section should pertain to the user,
                # but double check.
                if not hardware_procurement.is_user_associated(user_data):
                    continue
                yield hardware_procurement

    def clear_cache(self):
        """Clear the cache entry stored under the cache key."""
        return cache.delete(self._cache_key)

    def populate_cache(self, hardware_procurement_generator):
        """Given a generator that yields HardwareProcurements, populate
        the cache entry with the expected structure."""
        procurements_by_user_id = {}
        for hardware_procurement in hardware_procurement_generator:
            procurement_id = hardware_procurement.get_id()
            associated_user_ids = self._lookup_associated_user_ids(
                hardware_procurement)
            for user_id in associated_user_ids:
                if user_id not in procurements_by_user_id:
                    procurements_by_user_id[user_id] = {}
                procurements_by_user_id[user_id][procurement_id] = \
                    hardware_procurement
        cache.set(self._cache_key, procurements_by_user_id)

    def is_cache_populated(self):
        """Return whether the cache is populated, indicated by whether
        the cache key is present in the cache."""
        return self._cache_key in cache

    def _lookup_associated_user_ids(self, hardware_procurement):
        """Give a HardwareProcurement, look up the IDs of the users
        associated with it, namely the PI and POC. If none are found,
        return the nonexistent user ID. Return a list of unique IDs."""
        try:
            pi_email = hardware_procurement['pi_email']
            pi_user = look_up_user_by_email(pi_email)
        except Exception as e:
            pi_user = None

        try:
            poc_email = hardware_procurement['poc_email']
            poc_user = look_up_user_by_email(poc_email)
        except Exception as e:
            poc_user = None

        associated_user_ids = set()
        if not (pi_user or poc_user):
            user_id = self.NONEXISTENT_USER_ID
            associated_user_ids.add(user_id)
        else:
            if pi_user is not None:
                user_id = pi_user.id
                associated_user_ids.add(user_id)
            if poc_user is not None:
                user_id = poc_user.id
                associated_user_ids.add(user_id)
        return list(associated_user_ids)
