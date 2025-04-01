from abc import ABC
from abc import abstractmethod


class BaseDataSourceBackend(ABC):
    """An interface for fetching hardware procurement data using any of
    a number of backends."""

    @abstractmethod
    def fetch_hardware_procurements(self, user_data=None, status=None):
        """Return a generator that yields procurements (dicts),
        optionally filtering by user (dict) or status (str)."""
        raise NotImplementedError
