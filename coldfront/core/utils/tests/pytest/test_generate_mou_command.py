"""Unit/component tests for the generate_mou management command."""

from decimal import Decimal
import tempfile
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
import pytest

FAKE_PDF = b"fake-pdf-bytes"

# Patch the function in its source module. The command imports it lazily with
# `from coldfront.core.utils.mou import generate_unsigned_mou_pdf` inside
# handle(), so at call time it resolves the name from the source module —
# patching the source is the correct target.
_patch_generate = patch(
    "coldfront.core.utils.mou.generate_unsigned_mou_pdf",
    return_value=FAKE_PDF,
)


# ---------------------------------------------------------------------------
# Unit tests — no DB needed
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGenerateMouCommand_NonExistentPk:
    def test_new_project_raises_command_error(self, db):
        from coldfront.core.project.models import SavioProjectAllocationRequest

        nonexistent_pk = (
            SavioProjectAllocationRequest.objects.order_by("-pk")
            .values_list("pk", flat=True)
            .first()
        )
        nonexistent_pk = (nonexistent_pk or 0) + 9999
        with pytest.raises(CommandError, match="does not exist"):
            call_command(
                "generate_mou",
                request_type="new-project",
                pk=nonexistent_pk,
                output="/dev/null",
            )

    def test_secure_dir_raises_command_error(self, db):
        from coldfront.core.allocation.models import SecureDirRequest

        nonexistent_pk = (
            SecureDirRequest.objects.order_by("-pk")
            .values_list("pk", flat=True)
            .first()
        )
        nonexistent_pk = (nonexistent_pk or 0) + 9999
        with pytest.raises(CommandError, match="does not exist"):
            call_command(
                "generate_mou",
                request_type="secure-dir",
                pk=nonexistent_pk,
                output="/dev/null",
            )

    def test_service_units_purchase_raises_command_error(self, db):
        from coldfront.core.allocation.models import AllocationAdditionRequest

        nonexistent_pk = (
            AllocationAdditionRequest.objects.order_by("-pk")
            .values_list("pk", flat=True)
            .first()
        )
        nonexistent_pk = (nonexistent_pk or 0) + 9999
        with pytest.raises(CommandError, match="does not exist"):
            call_command(
                "generate_mou",
                request_type="service-units-purchase",
                pk=nonexistent_pk,
                output="/dev/null",
            )


@pytest.mark.unit
class TestGenerateMouCommand_EmptyPdfRaisesError:
    def test_raises_command_error_when_pdf_is_empty(
        self, db, create_active_project_with_pi
    ):
        """generate_unsigned_mou_pdf returning b"" should raise CommandError."""
        from django.contrib.auth.models import User

        from coldfront.core.allocation.models import (
            AllocationAdditionRequest,
            AllocationAdditionRequestStatusChoice,
        )

        pi = User.objects.create_user(username="cmd_test_pi_empty", email="x@x.com")
        project = create_active_project_with_pi("cmd_empty_test", pi)
        req = AllocationAdditionRequest.objects.create(
            requester=pi,
            project=project,
            status=AllocationAdditionRequestStatusChoice.objects.get(
                name="Under Review"
            ),
            num_service_units=Decimal("1000.00"),
        )

        with (
            patch(
                "coldfront.core.utils.mou.generate_unsigned_mou_pdf",
                return_value=b"",
            ),
            pytest.raises(CommandError, match="No MOU generator available"),
        ):
            call_command(
                "generate_mou",
                request_type="service-units-purchase",
                pk=req.pk,
                output="/dev/null",
            )


# ---------------------------------------------------------------------------
# Component tests — write real output file
# ---------------------------------------------------------------------------


@pytest.fixture
def pi_user(db):
    from django.contrib.auth.models import User

    return User.objects.create_user(
        username="cmd_test_pi",
        first_name="Jane",
        last_name="Smith",
        email="jane.smith@cmd-test.example.com",
    )


@pytest.fixture
def addition_request(db, pi_user, create_active_project_with_pi):
    from coldfront.core.allocation.models import (
        AllocationAdditionRequest,
        AllocationAdditionRequestStatusChoice,
    )

    project = create_active_project_with_pi("cmd_mou_test", pi_user)
    return AllocationAdditionRequest.objects.create(
        requester=pi_user,
        project=project,
        status=AllocationAdditionRequestStatusChoice.objects.get(name="Under Review"),
        num_service_units=Decimal("100000.00"),
        extra_fields={"campus_chartstring": "13U00-FSSF-19900-0-0"},
    )


@pytest.mark.component
@pytest.mark.django_db
class TestGenerateMouCommand_WritesOutput:
    def test_pdf_written_to_output_path(self, addition_request):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        with _patch_generate:
            call_command(
                "generate_mou",
                request_type="service-units-purchase",
                pk=addition_request.pk,
                output=tmp_path,
            )

        with open(tmp_path, "rb") as f:
            content = f.read()

        assert content == FAKE_PDF

    def test_correct_request_obj_passed_to_generator(self, addition_request):
        """The command should look up the model by PK and pass the right object."""
        from coldfront.core.allocation.models import AllocationAdditionRequest

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        with _patch_generate as mock_gen:
            call_command(
                "generate_mou",
                request_type="service-units-purchase",
                pk=addition_request.pk,
                output=tmp_path,
            )

        called_with = mock_gen.call_args[0][0]
        assert isinstance(called_with, AllocationAdditionRequest)
        assert called_with.pk == addition_request.pk
