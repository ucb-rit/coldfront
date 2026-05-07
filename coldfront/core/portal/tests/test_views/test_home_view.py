from coldfront.core.utils.tests.test_base import TestBase


class TestHomeBase(TestBase):
    """A base class for testing functionality on the home view."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.client.login(username=self.user.username, password=self.password)
