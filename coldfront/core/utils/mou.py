import base64
import datetime

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models.fields.files import FieldFile


def upload_to_func(instance, filename):
    from coldfront.core.allocation.models import (
        AllocationAdditionRequest,
        SecureDirRequest,
    )
    from coldfront.core.project.models import SavioProjectAllocationRequest

    fs = settings.FILE_STORAGE
    path = ""
    if isinstance(instance, SavioProjectAllocationRequest):
        path += fs["details"]["NEW_PROJECT_REQUEST_MOU"]["location"]
    elif isinstance(instance, AllocationAdditionRequest):
        path += fs["details"]["SERVICE_UNITS_PURCHASE_REQUEST_MOU"]["location"]
    elif isinstance(instance, SecureDirRequest):
        path += fs["details"]["SECURE_DIRECTORY_REQUEST_MOU"]["location"]

    date = datetime.datetime.now().replace(microsecond=0).isoformat()
    filename_suffix = get_mou_filename(instance)
    filename = f"{date}_{filename_suffix}"
    path += filename
    return path


def get_mou_filename(request_obj):
    from coldfront.core.allocation.models import (
        AllocationAdditionRequest,
        SecureDirRequest,
    )
    from coldfront.core.project.models import SavioProjectAllocationRequest

    project_name = request_obj.project.name
    last_name = ""
    type_ = ""

    fs = settings.FILE_STORAGE
    if isinstance(request_obj, SavioProjectAllocationRequest):
        last_name = request_obj.pi.last_name
        type_ += fs["details"]["NEW_PROJECT_REQUEST_MOU"]["filename_type"]
    elif isinstance(request_obj, AllocationAdditionRequest):
        last_name = request_obj.requester.last_name
        type_ += fs["details"]["SERVICE_UNITS_PURCHASE_REQUEST_MOU"]["filename_type"]
    elif isinstance(request_obj, SecureDirRequest):
        last_name = request_obj.pi.last_name
        type_ += fs["details"]["SECURE_DIRECTORY_REQUEST_MOU"]["filename_type"]

    filename = f"{project_name}_{last_name}_{type_}.pdf"
    return filename


def make_director_kwargs() -> dict:
    """Return constructor kwargs for a MouGenerator from application settings."""
    with open(settings.SAVIO_MOU_DIRECTOR_SIGNATURE_PATH, "rb") as f:
        director_signature_b64 = base64.b64encode(f.read()).decode()
    return {
        "director_name": settings.SAVIO_MOU_DIRECTOR_NAME,
        "director_title": settings.SAVIO_MOU_DIRECTOR_TITLE,
        "director_signature_b64": director_signature_b64,
    }


def generate_unsigned_mou_pdf(request_obj) -> bytes:
    """Generate an unsigned MOU PDF for the given request object.

    Returns an empty bytes object if the request type does not map to a
    known generator (e.g. a non-recharge, non-instructional new-project
    request).
    """
    from coldfront.core.allocation.models import (
        AllocationAdditionRequest,
        SecureDirRequest,
    )
    from coldfront.core.project.models import SavioProjectAllocationRequest
    from coldfront.core.resource.utils_.allowance_utils.computing_allowance import (
        ComputingAllowance,
    )
    from coldfront.lib.brc_mou_generator import (
        InstructionalMouGenerator,
        RechargeMouGenerator,
        SecureDirMouGenerator,
    )

    director_kwargs = make_director_kwargs()

    if isinstance(request_obj, SavioProjectAllocationRequest):
        first_name = request_obj.pi.first_name
        last_name = request_obj.pi.last_name
        project_name = request_obj.project.name
        allowance = ComputingAllowance(request_obj.computing_allowance)
        if allowance.is_instructional():
            from coldfront.core.allocation.utils import (
                calculate_service_units_to_allocate,
            )

            service_units = calculate_service_units_to_allocate(
                allowance,
                request_obj.request_time,
                allocation_period=request_obj.allocation_period,
            )
            return InstructionalMouGenerator(**director_kwargs).generate(
                first_name,
                last_name,
                project_name,
                service_units=int(service_units),
                extra_fields=request_obj.extra_fields,
                allowance_end=request_obj.allocation_period.end_date,
            )
        elif allowance.is_recharge():
            return RechargeMouGenerator(**director_kwargs).generate(
                first_name,
                last_name,
                project_name,
                service_units=int(request_obj.extra_fields["num_service_units"]),
                extra_fields=request_obj.extra_fields,
            )

    elif isinstance(request_obj, AllocationAdditionRequest):
        first_name = request_obj.requester.first_name
        last_name = request_obj.requester.last_name
        project_name = request_obj.project.name
        return RechargeMouGenerator(**director_kwargs).generate(
            first_name,
            last_name,
            project_name,
            service_units=int(request_obj.num_service_units),
            extra_fields=request_obj.extra_fields,
        )

    elif isinstance(request_obj, SecureDirRequest):
        first_name = request_obj.pi.first_name
        last_name = request_obj.pi.last_name
        project_name = request_obj.project.name
        return SecureDirMouGenerator(**director_kwargs).generate(
            first_name,
            last_name,
            project_name,
            department=request_obj.department,
        )

    return b""


class DynamicFieldFile(FieldFile):
    """A FieldFile whose file storage backend is determined by
    application settings."""

    def __init__(self, instance, field, name):
        super().__init__(instance, field, name)
        self.storage = self._get_storage_backend()

    @staticmethod
    def _get_storage_backend():
        fs = settings.FILE_STORAGE
        backend = fs["backend"]
        if backend == "file_system":
            # Files are written to the concatenation of MEDIA_ROOT and the path
            # designated by upload_to in the model field.

            return FileSystemStorage()
        elif backend == "google_drive":
            from gdstorage.storage import GoogleDriveStorage

            # If necessary, permissions may be added to restrict access.
            # https://django-googledrive-storage.readthedocs.io/en/latest/#file-permissions
            permissions = ()
            return GoogleDriveStorage(permissions=permissions)
        else:
            raise ImproperlyConfigured(f"Unexpected FILE_STORAGE backend: {backend}.")


class DynamicFileField(models.FileField):
    """A FieldFile that stores files in the file storage backend
    determined by application settings.

    Settings may be changed at runtime without a database migration."""

    attr_class = DynamicFieldFile
