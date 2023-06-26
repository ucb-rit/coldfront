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

def get_context(request_obj):
    from coldfront.core.allocation.models import AllocationAdditionRequest, SecureDirRequest
    from coldfront.core.project.models import SavioProjectAllocationRequest
    if isinstance(request_obj, AllocationAdditionRequest):
        brc_name = 'Ken Lutz'
        pi_name = self.request_obj.requester.get_full_name()
        between = f'{brc_name} and {pi_name}'
        date = str(datetime.today)
        pi_lab = pi_name
        pi_lab_long = pi_name
        pi_title = ''
        date = datetime.date.today().strftime("%B %d, %Y")
        re = f'{pi_lab_long} Savio Allowance Purchase Agreement'
        service_units = 300_000 #self.request_obj.survey_answers.get()
        chartstring = 'idk chartstring' #self.request_obj.survey_answers.get()
        cost = f'${(0.01 * service_units):.2f} ($0.01/SU)'
        signature = f'{pi_title} {pi_name}'
        return dict(between=between, date=date, re=re, signature=signature)
    return None