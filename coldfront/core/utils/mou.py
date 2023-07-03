from coldfront.core.utils.common import import_from_settings
import datetime
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
       f'{datetime.datetime.now().replace(microsecond=0).isoformat()}_' \
       f'{instance.project.name}_{instance.requester.last_name}_{type_}_MOU.pdf'
    return path

def get_context(request_obj):
    from coldfront.core.allocation.models import AllocationAdditionRequest, SecureDirRequest
    from coldfront.core.project.models import SavioProjectAllocationRequest
    if isinstance(request_obj, AllocationAdditionRequest):
        brc_name = 'Ken Lutz'
        pi_name = f'{request_obj.requester.first_name} {request_obj.requester.last_name}'
        between = f'{brc_name} and {pi_name}'
        pi_lab = pi_name
        pi_lab_long = pi_name
        pi_title = ''
        date = datetime.date.today().strftime("%B %d, %Y")
        re = f'{pi_lab_long} Savio Allowance Purchase Agreement'
        service_units = 300_000 #self.request_obj.survey_answers.get()
        chartstring = request_obj.extra_fields['campus_chartstring']
        cost = f'${(0.01 * service_units):.2f} ($0.01/SU)'
        signature = f'{pi_title} {pi_name}'
        body = f'This MOU describes the working agreement by which the {pi_lab} will obtain an additional allowance for use of ' \
f'the Berkeley Research Computing (BRC) Savio cluster. ' \
f'An allowance of {service_units} service units (SUs) will be created for {pi_name}. This purchased allowance will be ' \
f'separate from any Faculty Computing Allowance, so that the associated “budgets” can be managed separately. This ' \
f'purchased allowance will function largely the same as the Faculty Computing Allowance (FCA); {pi_name} will ' \
f'determine who has access, and will manage the shared resource among their Lab members. Purchased allowances ' \
f'differ from FCAs in two important ways: unlike the FCA, this purchased allowance will not expire at the end of the ' \
f'fiscal year; it will remain available until exhausted, or replenished with a subsequent purchase agreement. Also, this ' \
f'MOU allowance will be reimbursed for SUs lost if jobs fail or are killed due to unplanned downtime. ' \
f'The associated expense of {cost} will be transferred by the BRC program financial staff to the COA:\n' \
f'\t{chartstring}\n' \
f'Once this transfer is complete, the allowance access will be enabled. ' \
f'BRC staff will provide the {pi_lab} with the details for using the purchased allowance, including how to submit ' \
f'jobs to Savio using this allowance. ' \
f'The purchased allowance is pre-paid and non-refundable. ' \
f'This agreement will remain in effect until the purchased allowance is exhausted. If additional access is needed, ' \
f'additional separate MOU\'s may be negotiated.'
        return dict(between=between, date=date, re=re, signature=signature, body=body)
    return error