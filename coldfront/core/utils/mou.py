import datetime

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models.fields.files import FieldFile


def upload_to_func(instance, filename):
    from coldfront.core.allocation.models import AllocationAdditionRequest
    from coldfront.core.allocation.models import SecureDirRequest
    from coldfront.core.project.models import SavioProjectAllocationRequest

    fs = settings.FILE_STORAGE
    path = ''
    if isinstance(instance, SavioProjectAllocationRequest):
        path += fs['details']['NEW_PROJECT_REQUEST_MOU']['location']
    elif isinstance(instance, AllocationAdditionRequest):
        path += fs['details']['SERVICE_UNITS_PURCHASE_REQUEST_MOU']['location']
    elif isinstance(instance, SecureDirRequest):
        path += fs['details']['SECURE_DIRECTORY_REQUEST_MOU']['location']
    date = datetime.datetime.now().replace(microsecond=0).isoformat()
    type_ = get_mou_filename(instance)
    filename = f'{date}_{type_}'
    path += filename
    return path


def get_mou_filename(request_obj):
    from coldfront.core.allocation.models import AllocationAdditionRequest
    from coldfront.core.allocation.models import SecureDirRequest
    from coldfront.core.project.models import SavioProjectAllocationRequest

    fs = settings.FILE_STORAGE
    type_ = ''
    if isinstance(request_obj, SavioProjectAllocationRequest):
        type_ += fs['details']['NEW_PROJECT_REQUEST_MOU']['filename_type']
    elif isinstance(request_obj, AllocationAdditionRequest):
        type_ += fs[
            'details']['SERVICE_UNITS_PURCHASE_REQUEST_MOU']['filename_type']
    elif isinstance(request_obj, SecureDirRequest):
        type_ += fs['details']['SECURE_DIRECTORY_REQUEST_MOU']['filename_type']
    project_name = request_obj.project.name
    last_name = request_obj.requester.last_name
    filename = f'{project_name}_{last_name}_{type_}.pdf'
    return filename


class DynamicFieldFile(FieldFile):
    """A FieldFile whose file storage backend is determined by
    application settings."""

    def __init__(self, instance, field, name):
        super().__init__(instance, field, name)
        self.storage = self._get_storage_backend()

    @staticmethod
    def _get_storage_backend():
        fs = settings.FILE_STORAGE
        backend = fs['backend']
        if backend == 'file_system':
            # Files are written to the concatenation of MEDIA_ROOT and the path
            # designated by upload_to in the model field.
            return FileSystemStorage()
        elif backend == 'google_drive':
            from gdstorage.storage import GoogleDriveStorage
            # If necessary, permissions may be added to restrict access.
            # https://django-googledrive-storage.readthedocs.io/en/latest/#file-permissions
            permissions = ()
            return GoogleDriveStorage(permissions=permissions)
        else:
            raise ImproperlyConfigured(
                f'Unexpected FILE_STORAGE backend: {backend}.')


class DynamicFileField(models.FileField):
    """A FieldFile that stores files in the file storage backend
    determined by application settings.

    Settings may be changed at runtime without a database migration."""

    attr_class = DynamicFieldFile
