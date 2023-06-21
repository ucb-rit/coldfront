from coldfront.core.utils.common import import_from_settings
from datetime import datetime
def upload_to_func(instance, filename):
    fs = import_from_settings('FILE_STORAGE')
    path = ''
    type_ = ''
    import coldfront.core.project.models as project_models
    import coldfront.core.allocation.models as allocation_models
    if isinstance(instance, project_models.SavioProjectAllocationRequest):
        path += fs['details']['NEW_PROJECT_REQUEST_MOU']['location']
        type_ = 'NewProject'
    elif isinstance(instance, allocation_models.AllocationAdditionRequest):
        path += fs['details']['SERVICE_UNITS_PURCHASE_REQUEST_MOU']['location']
        type_ = 'AllowancePurchase'
    elif isinstance(instance, allocation_models.SecureDirRequest):
        path += fs['details']['SECURE_DIRECTORY_REQUEST_MOU']['location']
        type_ = 'SecureDirectory'
    path += \
       f'{datetime.now().replace(microsecond=0).isoformat()}_' \
       f'{instance.project.name}_{instance.requester.last_name}_{type_}_MOU.pdf'
    return path