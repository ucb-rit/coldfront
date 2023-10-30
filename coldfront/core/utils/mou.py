from coldfront.core.utils.common import import_from_settings
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from django.template.loader import render_to_string
import datetime

def upload_to_func(instance, filename):
    from coldfront.core.allocation.models import (AllocationAdditionRequest,
                                                  SecureDirRequest)
    from coldfront.core.project.models import SavioProjectAllocationRequest
    fs = import_from_settings('FILE_STORAGE') or {}
    path = ''
    if isinstance(instance, SavioProjectAllocationRequest):
        path += fs['details']['NEW_PROJECT_REQUEST_MOU']['location']
    elif isinstance(instance, AllocationAdditionRequest):
        path += fs['details']['SERVICE_UNITS_PURCHASE_REQUEST_MOU']['location']
    elif isinstance(instance, SecureDirRequest):
        path += fs['details']['SECURE_DIRECTORY_REQUEST_MOU']['location']
    date = datetime.datetime.now().replace(microsecond=0).isoformat()
    project_name = instance.project.name
    requester_last_name = instance.requester.last_name
    type_ = get_mou_filename(instance)
    filename = f'{date}_{project_name}_{requester_last_name}_{type_}.pdf'
    path += filename
    return path

def get_mou_filename(request_obj):
    from coldfront.core.allocation.models import (AllocationAdditionRequest,
                                                  SecureDirRequest)
    from coldfront.core.project.models import SavioProjectAllocationRequest
    fs = import_from_settings('FILE_STORAGE') or {}
    type_ = ''
    if isinstance(request_obj, SavioProjectAllocationRequest):
        type_ += fs['details']['NEW_PROJECT_REQUEST_MOU']['filename_type']
    elif isinstance(request_obj, AllocationAdditionRequest):
        type_ += fs['details']['SERVICE_UNITS_PURCHASE_REQUEST_MOU']['filename_type']
    elif isinstance(request_obj, SecureDirRequest):
        type_ += fs['details']['SECURE_DIRECTORY_REQUEST_MOU']['filename_type']
    project_name = request_obj.project.name
    last_name = request_obj.requester.last_name
    filename = f'{project_name}_{last_name}_{type_}.pdf'
    return filename