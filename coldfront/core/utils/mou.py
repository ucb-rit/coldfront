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
        type_ = 'NewProject'
    elif isinstance(instance, AllocationAdditionRequest):
        path += fs['details']['SERVICE_UNITS_PURCHASE_REQUEST_MOU']['location']
        type_ = 'AllowancePurchase'
    elif isinstance(instance, SecureDirRequest):
        path += fs['details']['SECURE_DIRECTORY_REQUEST_MOU']['location']
        type_ = 'SecureDirectory'
    path += \
       f'{datetime.datetime.now().replace(microsecond=0).isoformat()}_' \
       f'{instance.project.name}_{instance.requester.last_name}_{type_}_MOU.pdf'
    return path
