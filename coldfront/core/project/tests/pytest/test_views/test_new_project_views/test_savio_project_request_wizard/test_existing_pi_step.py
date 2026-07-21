"""Component tests for the existing_pi step's disabled-choices behaviour
after backward navigation.

Regression tests for the cache-poisoning bug where going back from the
existing_pi step, changing a prior step, and advancing again failed to
disable ineligible PIs.

Root cause: disable_pi_choices() cached the disabled set under a flat
'disabled_pks' key. Condition functions (show_new_pi_form_condition, etc.)
call get_cleaned_data_for_step('existing_pi') during get_form_list(), which
fires before set_step_data() has written the new choice to the session.
That caused the form to be instantiated with stale data, populating the
cache with an empty disabled set that was then reused for the correct
(allowance, period) pair later in the same request.

Fix: cache key includes (resource.pk, allocation_period.pk) so each
(allowance, period) pair gets its own entry.

Two dimensions of the cache key are tested independently:

  TestAllowanceSwitch — changing the computing_allowance (resource.pk
      dimension).  Pass 1 uses RECHARGE (non-periodic, not one-per-PI) so
      the allocation_period step is skipped and no PIs are disabled; this
      avoids needing semester-based AllocationPeriod records that are absent
      from the shared test DB.

  TestPeriodSwitch — changing the allocation_period within the same FCA
      allowance (allocation_period.pk dimension).  Requires
      ALLOCATION_RENEWAL_FOR_NEXT_PERIOD_REQUESTABLE=True so both the
      current and next period appear in the form; the flag is forced on to
      keep the test calendar-independent.
"""

from copy import deepcopy
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse
import pytest

from coldfront.core.project.tests.utils import create_project_and_request
from coldfront.core.project.utils_.renewal_utils import (
    get_current_allowance_year_period,
    get_next_allowance_year_period,
)
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.utils.tests.test_base import enable_deployment

# ---------------------------------------------------------------------------
# Module-level fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def brc_deployment():
    """Enable the BRC deployment (BRC_ONLY=True) for the duration of a test."""
    with enable_deployment("BRC"):
        yield


@pytest.fixture
def wizard_user(db, password):
    """A test user who has signed the access agreement."""
    from coldfront.core.user.models import UserProfile
    from coldfront.core.utils.common import utc_now_offset_aware

    user = User.objects.create_user(
        username="wizard_test_user",
        email="wizard_test_user@email.com",
        first_name="Wizard",
        last_name="User",
        password=password,
    )
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.access_agreement_signed_date = utc_now_offset_aware()
    profile.save()
    return user


# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------

_WIZARD_URL = "new-project-request"
_VIEW_NAME = "savio_project_request_wizard"


class _WizardMixin:
    """Shared fixtures and helpers for wizard navigation tests."""

    @pytest.fixture(autouse=True)
    def _setup(self, client, wizard_user, password, brc_deployment):
        client.login(username=wizard_user.username, password=password)
        self.client = client
        self.user = wizard_user
        self.url = reverse(_WIZARD_URL)
        self.current_step_key = f"{_VIEW_NAME}-current_step"
        # Seed self.steps from the wizard's own form-name→step-number mapping
        # so test bodies reference steps by name and are immune to reordering.
        response = self.client.get(self.url)
        self.steps = response.context["view"].step_numbers_by_form_name

    def _post_step(self, form_name, fields):
        """POST the wizard step for form_name and return the response."""
        step = self.steps[form_name]
        data = {self.current_step_key: str(step)}
        data.update({f"{step}-{k}": v for k, v in fields.items()})
        return self.client.post(self.url, data)

    def _goto_step(self, form_name):
        """POST a wizard_goto_step request to navigate back to form_name."""
        self.client.post(self.url, {"wizard_goto_step": str(self.steps[form_name])})

    def _existing_pi_disabled_choices(self, response):
        """Return disabled_choices from the existing_pi form in the response."""
        return response.context["form"].fields["PI"].widget.disabled_choices


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.component
@pytest.mark.django_db
class TestAllowanceSwitch(_WizardMixin):
    """Disabled-choices are recomputed after switching the computing_allowance.

    Exercises the resource.pk dimension of the disable_pi_choices() cache key.
    """

    def test_switching_to_limited_allowance_updates_disabled_pis(self):
        """After going back from the existing_pi step and switching from a
        non-limited allowance (RECHARGE) to a one-per-PI allowance (FCA),
        the existing_pi step must disable PIs who already have an FCA
        request — not reuse the stale empty set cached during the RECHARGE
        pass.

        RECHARGE is non-periodic so the allocation_period step is skipped;
        posting computing_allowance (RECHARGE) renders existing_pi directly.
        """
        allocation_period = get_current_allowance_year_period()
        fca = Resource.objects.get(name=BRCAllowances.FCA)
        recharge = Resource.objects.get(name=BRCAllowances.RECHARGE)

        # Give self.user an Under Review FCA request this period so they
        # appear in pis_with_new_project_requests_pks() under FCA.
        create_project_and_request(
            "fc_test",
            "Denied",
            fca,
            allocation_period,
            self.user,
            self.user,
            "Under Review",
        )

        # --- Pass 1: RECHARGE (not one-per-PI, non-periodic) ---
        # RECHARGE skips allocation_period; posting computing_allowance
        # renders existing_pi directly.
        response = self._post_step(
            "computing_allowance", {"computing_allowance": recharge.pk}
        )

        assert response.status_code == HTTPStatus.OK
        # RECHARGE has no one-per-PI limit; self.user must NOT be disabled.
        assert self.user.pk not in self._existing_pi_disabled_choices(response)

        # --- Go back to computing_allowance ---
        self._goto_step("computing_allowance")

        # --- Pass 2: FCA (one-per-PI, periodic) ---
        self._post_step("computing_allowance", {"computing_allowance": fca.pk})
        response = self._post_step(
            "allocation_period", {"allocation_period": allocation_period.pk}
        )

        assert response.status_code == HTTPStatus.OK
        # FCA is one-per-PI and self.user has an Under Review request this
        # period; they MUST now be disabled.
        assert self.user.pk in self._existing_pi_disabled_choices(response)


@pytest.mark.component
@pytest.mark.django_db
class TestPeriodSwitch(_WizardMixin):
    """Disabled-choices are recomputed after switching the allocation_period.

    Exercises the allocation_period.pk dimension of the disable_pi_choices()
    cache key.
    """

    def test_switching_allocation_period_updates_disabled_pis(self):
        """After going back from the existing_pi step and switching FCA from
        the current period to the next, the disabled PI set must be
        recomputed — not reused from the current period's cache entry.

        Both periods are present in the form only when
        ALLOCATION_RENEWAL_FOR_NEXT_PERIOD_REQUESTABLE is True (the overlap
        window that allows requesting either period).  The flag is forced on
        here so the test is not calendar-dependent.
        """
        current_period = get_current_allowance_year_period()
        next_period = get_next_allowance_year_period()
        assert next_period is not None, (
            "Next allowance year period must exist in the shared test DB"
        )

        fca = Resource.objects.get(name=BRCAllowances.FCA)

        # Give self.user an Under Review FCA request for the current period
        # only — they should be disabled for that period, but NOT for next.
        create_project_and_request(
            "fc_test",
            "Denied",
            fca,
            current_period,
            self.user,
            self.user,
            "Under Review",
        )

        # Force the flag on so both periods appear in the allocation_period
        # form regardless of the current calendar date.
        flags = deepcopy(settings.FLAGS)
        flags["ALLOCATION_RENEWAL_FOR_NEXT_PERIOD_REQUESTABLE"] = [
            {"condition": "boolean", "value": True}
        ]

        with override_settings(FLAGS=flags):
            # --- Pass 1: FCA + current period → user disabled ---
            self._post_step("computing_allowance", {"computing_allowance": fca.pk})
            response = self._post_step(
                "allocation_period", {"allocation_period": current_period.pk}
            )

            assert response.status_code == HTTPStatus.OK
            assert self.user.pk in self._existing_pi_disabled_choices(response)

            # --- Go back to allocation_period ---
            self._goto_step("allocation_period")

            # --- Pass 2: FCA + next period → user NOT disabled ---
            response = self._post_step(
                "allocation_period", {"allocation_period": next_period.pk}
            )

            assert response.status_code == HTTPStatus.OK
            # self.user has no FCA request for the next period; cache must NOT
            # serve the stale disabled set from the current-period entry.
            assert self.user.pk not in self._existing_pi_disabled_choices(response)
