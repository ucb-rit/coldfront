"""Component tests for complete wizard submission paths.

Each test walks through the full SavioProjectRequestWizard flow for one
allowance type and verifies that the resulting DB objects are correct.

Step layout (BRC, no departments plugin):

  0  ComputingAllowanceForm            always
  1  SavioProjectAllocationPeriodForm  periodic allowances (FCA, ICA, PCA)
  2  SavioProjectExistingPIForm        always
  3  SavioProjectNewPIForm             when no existing PI selected
  4  SavioProjectICAExtraFieldsForm    ICA only
  5  SavioProjectRechargeExtraFieldsForm  RECHARGE only
  6  SavioProjectPoolAllocationsForm   poolable allowances (FCA, PCA)
  7  SavioProjectPooledProjectSelectionForm  when pool=True
  8  SavioProjectDetailsForm           when not pooling
  9  BillingIDValidationForm           LRC_ONLY (never shown here)
  10 SavioProjectSurveyForm            always → redirects on success

Paths covered:

  TestFCASubmission    — FCA, existing PI, no pooling
                         active forms: computing_allowance → allocation_period
                           → existing_pi → pool_allocations → details → survey
  TestRECHARGESubmission — RECHARGE, existing PI
                         active forms: computing_allowance → existing_pi
                           → recharge_extra_fields → details → survey
                         (allocation_period and pool_allocations skipped;
                          non-periodic, non-poolable)
"""

from copy import deepcopy
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse
import pytest

from coldfront.core.project.models import (
    Project,
    SavioProjectAllocationRequest,
)
from coldfront.core.project.utils_.renewal_utils import (
    get_current_allowance_year_period,
)
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.utils.tests.test_base import enable_deployment

# ---------------------------------------------------------------------------
# Module-level fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def brc_deployment():
    """Enable the BRC deployment without the departments plugin.

    USER_DEPARTMENTS_ENABLED is forced off so the wizard exposes the clean
    11-step layout (indices 0-10) documented in this module's docstring.
    """
    flags = deepcopy(settings.FLAGS)
    flags["USER_DEPARTMENTS_ENABLED"] = [{"condition": "boolean", "value": False}]
    with enable_deployment("BRC"):
        with override_settings(FLAGS=flags):
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

# Minimum-valid survey data (both fields require at least 10 chars).
_SURVEY = {
    "scope_and_intent": "b" * 20,
    "computational_aspects": "c" * 20,
}

# Minimum-valid project details (name suffix fed to the form; the form
# prepends the allowance code prefix automatically).
_DETAILS = {
    "name": "testproj",
    "title": "Test project title",
    "description": "a" * 20,
}


class _WizardMixin:
    """Shared fixtures and helpers for wizard submission tests."""

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


# ---------------------------------------------------------------------------
# FCA — existing PI, no pooling
# ---------------------------------------------------------------------------


@pytest.mark.component
@pytest.mark.django_db
class TestFCASubmission(_WizardMixin):
    """Full FCA wizard flow: existing PI, no pooling.

    Active forms: computing_allowance → allocation_period → existing_pi →
                  pool_allocations (pool=False) → details → survey → redirect
    """

    def test_creates_request_and_project(self):
        """A successful FCA submission creates a SavioProjectAllocationRequest
        and Project with the expected attributes."""
        allocation_period = get_current_allowance_year_period()
        fca = Resource.objects.get(name=BRCAllowances.FCA)

        self._post_step("computing_allowance", {"computing_allowance": fca.pk})
        self._post_step(
            "allocation_period", {"allocation_period": allocation_period.pk}
        )
        self._post_step("existing_pi", {"PI": self.user.pk})
        self._post_step("pool_allocations", {"pool": False})
        self._post_step("details", _DETAILS)
        response = self._post_step("survey", _SURVEY)

        assert response.status_code == HTTPStatus.FOUND

        request = SavioProjectAllocationRequest.objects.get(requester=self.user)
        assert request.pi == self.user
        assert request.computing_allowance == fca
        assert request.allocation_period == allocation_period
        assert request.status.name == "Under Review"
        assert not request.pool
        assert Project.objects.filter(pk=request.project.pk).exists()

    def test_survey_answers_stored(self):
        """Survey answers are saved verbatim on the request."""
        allocation_period = get_current_allowance_year_period()
        fca = Resource.objects.get(name=BRCAllowances.FCA)

        self._post_step("computing_allowance", {"computing_allowance": fca.pk})
        self._post_step(
            "allocation_period", {"allocation_period": allocation_period.pk}
        )
        self._post_step("existing_pi", {"PI": self.user.pk})
        self._post_step("pool_allocations", {"pool": False})
        self._post_step("details", _DETAILS)
        self._post_step("survey", _SURVEY)

        request = SavioProjectAllocationRequest.objects.get(requester=self.user)
        assert request.survey_answers["scope_and_intent"] == _SURVEY["scope_and_intent"]
        assert (
            request.survey_answers["computational_aspects"]
            == _SURVEY["computational_aspects"]
        )


# ---------------------------------------------------------------------------
# RECHARGE — existing PI
# ---------------------------------------------------------------------------


@pytest.mark.component
@pytest.mark.django_db
class TestRECHARGESubmission(_WizardMixin):
    """Full RECHARGE wizard flow: existing PI.

    RECHARGE is non-periodic (allocation_period skipped) and non-poolable
    (pool_allocations skipped).  It requires extra billing fields.

    Active forms: computing_allowance → existing_pi → recharge_extra_fields →
                  details → survey → redirect
    """

    # Minimum-valid recharge extra fields.
    _RECHARGE_EXTRA = {
        "num_service_units": 100,
        "campus_chartstring": "a" * 15,
        "chartstring_account_type": "Research account",
        "chartstring_contact_name": "Finance Contact",
        "chartstring_contact_email": "finance@example.com",
    }

    def test_creates_request_and_project(self):
        """A successful RECHARGE submission creates a
        SavioProjectAllocationRequest with no allocation_period."""
        recharge = Resource.objects.get(name=BRCAllowances.RECHARGE)

        self._post_step("computing_allowance", {"computing_allowance": recharge.pk})
        self._post_step("existing_pi", {"PI": self.user.pk})
        self._post_step("recharge_extra_fields", self._RECHARGE_EXTRA)
        self._post_step("details", _DETAILS)
        response = self._post_step("survey", _SURVEY)

        assert response.status_code == HTTPStatus.FOUND

        request = SavioProjectAllocationRequest.objects.get(requester=self.user)
        assert request.pi == self.user
        assert request.computing_allowance == recharge
        assert request.allocation_period is None
        assert request.status.name == "Under Review"
        assert Project.objects.filter(pk=request.project.pk).exists()

    def test_recharge_extra_fields_validation_rejects_bad_service_units(self):
        """The recharge_extra_fields step rejects a num_service_units value
        that is not a positive multiple of 100."""
        recharge = Resource.objects.get(name=BRCAllowances.RECHARGE)

        self._post_step("computing_allowance", {"computing_allowance": recharge.pk})
        self._post_step("existing_pi", {"PI": self.user.pk})

        bad_extra = dict(self._RECHARGE_EXTRA, num_service_units=150)
        response = self._post_step("recharge_extra_fields", bad_extra)

        # Wizard re-renders the same step on validation failure.
        assert response.status_code == HTTPStatus.OK
        assert response.context["wizard"]["steps"].current == str(
            self.steps["recharge_extra_fields"]
        )
        assert not SavioProjectAllocationRequest.objects.filter(
            requester=self.user
        ).exists()
