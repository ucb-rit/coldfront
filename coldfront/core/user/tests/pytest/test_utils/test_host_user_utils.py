"""Tests for coldfront.core.user.utils_.host_user_utils."""

from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
import pytest

from coldfront.core.user.utils_.host_user_utils import lbl_employees


@pytest.mark.component
@pytest.mark.django_db
class TestLblEmployees:
    """Tests for lbl_employees()."""

    def _make_user(self, username, email):
        return User.objects.create_user(username=username, email=email)

    def _make_email_address(self, user, email, verified=True):
        return EmailAddress.objects.create(
            user=user, email=email, verified=verified, primary=False
        )

    def test_includes_user_with_lbl_primary_email(self):
        user = self._make_user("lbl_user", "lbl_user@lbl.gov")
        assert user in lbl_employees()

    def test_includes_user_with_verified_lbl_email_address(self):
        """A user whose primary email is not @lbl.gov, but who has a
        verified EmailAddress that is, should be included."""
        user = self._make_user("external", "external@example.com")
        self._make_email_address(user, "external@lbl.gov", verified=True)
        assert user in lbl_employees()

    def test_excludes_user_with_no_lbl_email(self):
        user = self._make_user("non_lbl", "user@example.com")
        assert user not in lbl_employees()

    def test_excludes_user_with_unverified_lbl_email_address(self):
        """An unverified @lbl.gov EmailAddress does not qualify."""
        user = self._make_user("unverified", "unverified@example.com")
        self._make_email_address(user, "unverified@lbl.gov", verified=False)
        assert user not in lbl_employees()

    def test_deduplicates_user_matching_both_conditions(self):
        """A user with both a primary @lbl.gov email and a verified
        @lbl.gov EmailAddress should appear exactly once."""
        user = self._make_user("double", "double@lbl.gov")
        self._make_email_address(user, "double_alt@lbl.gov", verified=True)
        results = lbl_employees().filter(pk=user.pk)
        assert results.count() == 1

    def test_returns_all_qualifying_users(self):
        """All three inclusion paths should be returned together."""
        by_primary = self._make_user("by_primary", "by_primary@lbl.gov")
        by_verified = self._make_user("by_verified", "by_verified@example.com")
        self._make_email_address(by_verified, "by_verified@lbl.gov", verified=True)
        non_lbl = self._make_user("non_lbl", "non_lbl@example.com")

        qs = lbl_employees()
        assert by_primary in qs
        assert by_verified in qs
        assert non_lbl not in qs
