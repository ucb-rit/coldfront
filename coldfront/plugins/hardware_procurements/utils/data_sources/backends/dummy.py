from .base import BaseDataSourceBackend


class DummyDataSourceBackend(BaseDataSourceBackend):
    """A backend for testing purposes."""

    # TODO: Yield test data.

    def fetch_hardware_procurements(self, user_data=None, status=None):
        yield from ()
