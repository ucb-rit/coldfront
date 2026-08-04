"""Component tests for generate_unsigned_mou_pdf() in coldfront.core.utils.mou.

Each test patches:
  - coldfront.core.utils.mou.make_director_kwargs  →  returns fake director kwargs
  - coldfront.lib.brc_mou_generator.MouGenerator._render  →  returns FAKE_PDF

This exercises the isinstance dispatch and model attribute extraction in
generate_unsigned_mou_pdf() without hitting the filesystem (no sig file needed)
or launching Playwright.
"""

from decimal import Decimal
from unittest.mock import patch

import pytest

from coldfront.lib.brc_mou_generator import MouGenerator

FAKE_PDF = b"fake-pdf-bytes"
FAKE_DIRECTOR_KWARGS = {
    "director_name": "Test Director",
    "director_title": "Director of Testing",
    "director_signature_b64": "ZmFrZQ==",
}

_patch_director = patch(
    "coldfront.core.utils.mou.make_director_kwargs",
    return_value=FAKE_DIRECTOR_KWARGS,
)

_patch_calculate_sus = patch(
    "coldfront.core.allocation.utils.calculate_service_units_to_allocate",
    return_value=Decimal("200000"),
)


def _call(request_obj):
    """Call generate_unsigned_mou_pdf with I/O mocked out.

    Returns (pdf_bytes, template_name).
    template_name is None when generate_unsigned_mou_pdf returns b"" directly.
    """
    from coldfront.core.utils.mou import generate_unsigned_mou_pdf

    template_name_seen = []

    def _capturing_render(self, context):
        template_name_seen.append(self._template_name)
        return FAKE_PDF

    with (
        _patch_director,
        _patch_calculate_sus,
        patch.object(MouGenerator, "_render", _capturing_render),
    ):
        result = generate_unsigned_mou_pdf(request_obj)

    template_name = template_name_seen[0] if template_name_seen else None
    return result, template_name


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def pi_user(db):
    from django.contrib.auth.models import User

    return User.objects.create_user(
        username="mou_test_pi",
        first_name="Jane",
        last_name="Smith",
        email="jane.smith@mou-test.example.com",
    )


@pytest.fixture
def requester_user(db):
    from django.contrib.auth.models import User

    return User.objects.create_user(
        username="mou_test_req",
        first_name="Bob",
        last_name="Jones",
        email="bob.jones@mou-test.example.com",
    )


@pytest.fixture
def project(db, create_active_project_with_pi, pi_user):
    return create_active_project_with_pi("ic_mou_test", pi_user)


@pytest.fixture
def ica_resource(db, allocation_period):
    from coldfront.core.resource.models import (
        Resource,
        ResourceAttributeType,
        TimedResourceAttribute,
    )
    from coldfront.core.resource.utils_.allowance_utils.computing_allowance import (
        ComputingAllowance,
    )

    resource = next(
        (r for r in Resource.objects.all() if ComputingAllowance(r).is_instructional()),
        None,
    )
    if resource is None:
        pytest.skip("No instructional computing allowance resource in test DB.")

    attr_type = ResourceAttributeType.objects.get(name="Service Units")
    TimedResourceAttribute.objects.get_or_create(
        resource_attribute_type=attr_type,
        resource=resource,
        start_date=allocation_period.start_date,
        end_date=allocation_period.end_date,
        defaults={"value": "200000"},
    )
    return resource


@pytest.fixture
def recharge_resource(db):
    from coldfront.core.resource.models import Resource
    from coldfront.core.resource.utils_.allowance_utils.computing_allowance import (
        ComputingAllowance,
    )

    resource = next(
        (r for r in Resource.objects.all() if ComputingAllowance(r).is_recharge()),
        None,
    )
    if resource is None:
        pytest.skip("No recharge computing allowance resource in test DB.")
    return resource


@pytest.fixture
def other_resource(db):
    """A computing allowance that is neither instructional nor recharge."""
    from coldfront.core.resource.models import Resource
    from coldfront.core.resource.utils_.allowance_utils.computing_allowance import (
        ComputingAllowance,
    )

    resource = next(
        (
            r
            for r in Resource.objects.all()
            if not ComputingAllowance(r).is_instructional()
            and not ComputingAllowance(r).is_recharge()
        ),
        None,
    )
    if resource is None:
        pytest.skip("No non-ICA, non-recharge computing allowance resource in test DB.")
    return resource


@pytest.fixture
def allocation_period(db):
    from coldfront.core.project.utils_.renewal_utils import (
        get_current_allowance_year_period,
    )

    period = get_current_allowance_year_period()
    if period is None:
        pytest.skip("No current allowance year period in test DB.")
    return period


@pytest.fixture
def request_status(db):
    from coldfront.core.project.models import ProjectAllocationRequestStatusChoice

    return ProjectAllocationRequestStatusChoice.objects.get(name="Under Review")


# ---------------------------------------------------------------------------
# SavioProjectAllocationRequest — instructional
# ---------------------------------------------------------------------------


@pytest.fixture
def ica_savio_request(
    db,
    pi_user,
    requester_user,
    project,
    ica_resource,
    allocation_period,
    request_status,
):
    from coldfront.core.project.models import (
        SavioProjectAllocationRequest,
        savio_project_request_ica_extra_fields_schema,
        savio_project_request_ica_state_schema,
    )

    extra = savio_project_request_ica_extra_fields_schema()
    extra.update(
        {
            "course_department": "EECS",
            "course_name": "CS 161",
            "point_of_contact": "Jane Smith",
            "num_students": 30,
        }
    )

    return SavioProjectAllocationRequest.objects.create(
        requester=requester_user,
        pi=pi_user,
        project=project,
        computing_allowance=ica_resource,
        allocation_period=allocation_period,
        status=request_status,
        survey_answers={},
        state=savio_project_request_ica_state_schema(),
        extra_fields=extra,
    )


@pytest.mark.component
@pytest.mark.django_db
class TestGenerateUnsignedMouPdf_IcaSavioRequest:
    def test_returns_pdf_bytes(self, ica_savio_request):
        result, _ = _call(ica_savio_request)
        assert result == FAKE_PDF

    def test_uses_instructional_template(self, ica_savio_request):
        _, template_name = _call(ica_savio_request)
        assert template_name == "instructional.html"


# ---------------------------------------------------------------------------
# SavioProjectAllocationRequest — recharge
# ---------------------------------------------------------------------------


@pytest.fixture
def recharge_savio_request(
    db,
    pi_user,
    requester_user,
    project,
    recharge_resource,
    allocation_period,
    request_status,
):
    from coldfront.core.project.models import (
        SavioProjectAllocationRequest,
        savio_project_request_recharge_extra_fields_schema,
        savio_project_request_recharge_state_schema,
    )

    extra = savio_project_request_recharge_extra_fields_schema()
    extra.update(
        {
            "num_service_units": "100000",
            "campus_chartstring": "13U00-FSSF-19900-0-0",
        }
    )

    return SavioProjectAllocationRequest.objects.create(
        requester=requester_user,
        pi=pi_user,
        project=project,
        computing_allowance=recharge_resource,
        allocation_period=allocation_period,
        status=request_status,
        survey_answers={},
        state=savio_project_request_recharge_state_schema(),
        extra_fields=extra,
    )


@pytest.mark.component
@pytest.mark.django_db
class TestGenerateUnsignedMouPdf_RechargeSavioRequest:
    def test_returns_pdf_bytes(self, recharge_savio_request):
        result, _ = _call(recharge_savio_request)
        assert result == FAKE_PDF

    def test_uses_recharge_template(self, recharge_savio_request):
        _, template_name = _call(recharge_savio_request)
        assert template_name == "recharge.html"


# ---------------------------------------------------------------------------
# SavioProjectAllocationRequest — other allowance type (b"" fallback)
# ---------------------------------------------------------------------------


@pytest.fixture
def other_savio_request(
    db,
    pi_user,
    requester_user,
    project,
    other_resource,
    allocation_period,
    request_status,
):
    from coldfront.core.project.models import SavioProjectAllocationRequest

    return SavioProjectAllocationRequest.objects.create(
        requester=requester_user,
        pi=pi_user,
        project=project,
        computing_allowance=other_resource,
        allocation_period=allocation_period,
        status=request_status,
        survey_answers={},
    )


@pytest.mark.component
@pytest.mark.django_db
class TestGenerateUnsignedMouPdf_OtherSavioRequest:
    def test_returns_empty_bytes(self, other_savio_request):
        result, _ = _call(other_savio_request)
        assert result == b""

    def test_render_not_called(self, other_savio_request):
        _, template_name = _call(other_savio_request)
        assert template_name is None


# ---------------------------------------------------------------------------
# AllocationAdditionRequest
# ---------------------------------------------------------------------------


@pytest.fixture
def allocation_addition_request(db, requester_user, project):
    from coldfront.core.allocation.models import (
        AllocationAdditionRequest,
        AllocationAdditionRequestStatusChoice,
    )

    return AllocationAdditionRequest.objects.create(
        requester=requester_user,
        project=project,
        status=AllocationAdditionRequestStatusChoice.objects.get(name="Under Review"),
        num_service_units=Decimal("100000.00"),
        extra_fields={"campus_chartstring": "13U00-FSSF-19900-0-0"},
    )


@pytest.mark.component
@pytest.mark.django_db
class TestGenerateUnsignedMouPdf_AllocationAdditionRequest:
    def test_returns_pdf_bytes(self, allocation_addition_request):
        result, _ = _call(allocation_addition_request)
        assert result == FAKE_PDF

    def test_uses_recharge_template(self, allocation_addition_request):
        _, template_name = _call(allocation_addition_request)
        assert template_name == "recharge.html"


# ---------------------------------------------------------------------------
# SecureDirRequest
# ---------------------------------------------------------------------------


@pytest.fixture
def secure_dir_request(db, pi_user, requester_user, project):
    from coldfront.core.allocation.models import (
        SecureDirRequest,
        SecureDirRequestStatusChoice,
    )

    return SecureDirRequest.objects.create(
        directory_name="test_dir",
        data_description="Test data for MOU unit tests.",
        department="Sociology",
        requester=requester_user,
        pi=pi_user,
        project=project,
        status=SecureDirRequestStatusChoice.objects.get(name="Under Review"),
    )


@pytest.mark.component
@pytest.mark.django_db
class TestGenerateUnsignedMouPdf_SecureDirRequest:
    def test_returns_pdf_bytes(self, secure_dir_request):
        result, _ = _call(secure_dir_request)
        assert result == FAKE_PDF

    def test_uses_secure_dir_template(self, secure_dir_request):
        _, template_name = _call(secure_dir_request)
        assert template_name == "secure_dir.html"
