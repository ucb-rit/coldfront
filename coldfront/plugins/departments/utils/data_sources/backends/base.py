from abc import ABC
from abc import abstractmethod


class BaseDataSourceBackend(ABC):
    """An interface for fetching department data using any of a number
    of backends."""

    @abstractmethod
    def fetch_departments(self):
        """Return a generator of all departments as tuples of the form
        (department identifier (str), department description (str))."""
        pass

    @abstractmethod
    def fetch_departments_for_user(self, user_data):
        """Return a generator of departments associated with the given
        dict, which represents a user, as tuples of the form (department
        identifier (str), department description (str))."""
        pass
