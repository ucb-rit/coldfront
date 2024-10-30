from .base import BaseDataSourceBackend


class DummyDataSourceBackend(BaseDataSourceBackend):
    """A backend for testing purposes."""

    # TODO: Return ... what?

    def fetch_departments(self):
        """TODO"""
        return []

    def fetch_departments_for_user(self, user_obj):
        """TODO"""
        return []
