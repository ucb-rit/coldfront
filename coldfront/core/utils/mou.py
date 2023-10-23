from coldfront.core.utils.common import import_from_settings
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from django.template.loader import render_to_string
import datetime

def upload_to_func(instance, filename):
    fs = import_from_settings('FILE_STORAGE')
    path = ''
    type_ = ''
    from coldfront.core.allocation.models import (AllocationAdditionRequest,
                                                  SecureDirRequest,
                                                  AllocationPeriod)
    from coldfront.core.project.models import SavioProjectAllocationRequest
    if isinstance(instance, SavioProjectAllocationRequest):
        path += fs['details']['NEW_PROJECT_REQUEST_MOU']['location']
        type_ = 'NewProject_MOU'
    elif isinstance(instance, AllocationAdditionRequest):
        path += fs['details']['SERVICE_UNITS_PURCHASE_REQUEST_MOU']['location']
        type_ = 'AllowancePurchase_MOU'
    elif isinstance(instance, SecureDirRequest):
        path += fs['details']['SECURE_DIRECTORY_REQUEST_MOU']['location']
        type_ = 'SecureDirectory_RUA'
    date = datetime.datetime.now().replace(microsecond=0).isoformat()
    project_name = instance.project.name
    requester_last_name = instance.requester.last_name
    filename = f'{date}_{project_name}_{requester_last_name}_{type_}.pdf'
    path += filename
    return path
