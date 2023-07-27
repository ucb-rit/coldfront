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

def get_mou_html(request_obj):
    from coldfront.core.allocation.models import (AllocationAdditionRequest,
                                                  SecureDirRequest,
                                                  AllocationPeriod)
    from coldfront.core.project.models import SavioProjectAllocationRequest
    context = {}
    context['static_root'] = import_from_settings('STATIC_ROOT')
    context['brc_name'] = 'Ken Lutz'
    context['pi_name'] = f'{request_obj.requester.first_name} {request_obj.requester.last_name}'
    context['date'] = datetime.date.today().strftime("%B %d, %Y")
    context['project'] = request_obj.project.name
    context['mou_title'] = 'Memorandum of Understanding'
    context['mou_subtitle'] = ''
    context['footer'] = ''

    if isinstance(request_obj, SavioProjectAllocationRequest) and \
                        ComputingAllowance(request_obj.computing_allowance) \
                            .is_instructional():
        context['service_units'] = request_obj.computing_allowance \
                                                         .get_attribute('Service Units')
        context['course_dept'] = request_obj.extra_fields['course_department']
        context['dept_and_pi'] = f'{context["course_dept"]}/{context["pi_name"]}'
        context['between'] = f'{context["brc_name"]} (BRC) and {context["pi_name"]}'
        context['re'] = f'{context["dept_and_pi"]} ICA Agreement'
        context['course_name'] = request_obj.extra_fields['course_name']
        context['point_of_contact'] = request_obj.extra_fields['point_of_contact']
        context['num_students'] = int(request_obj.extra_fields['num_students'])
        allowance_end = request_obj.allocation_period.end_date
        context['allowance_last_month'] = allowance_end.strftime('%B %Y')
        allowance_year = AllocationPeriod.objects.get(
                     name__startswith='Allowance Year',
                     start_date__lte=allowance_end,
                     end_date__gte=allowance_end).name
        context['allowance_year_short'] = f'AY {allowance_year.split(" ")[2][2:]}/' \
                                 f'{allowance_year.split(" ")[4][2:]}'
        context['signature'] = f'{context["pi_name"]}\n{context["course_dept"]}'
        context['body'] = render_to_string('ica_body_template.html', context)

    elif isinstance(request_obj, AllocationAdditionRequest) or \
                (isinstance(request_obj, SavioProjectAllocationRequest) and \
                ComputingAllowance(request_obj.computing_allowance)\
                                                        .is_recharge()):
        context['between'] = f'{context["brc_name"]} (BRC) and {context["pi_name"]}'
        context['re'] = f'{context["project"]} Savio Allowance Purchase Agreement'
        if isinstance(request_obj, AllocationAdditionRequest):
            service_units = int(request_obj.num_service_units)
        else:
            service_units = int(request_obj.extra_fields['num_service_units'])
        context['chartstring'] = request_obj.extra_fields['campus_chartstring']
        context['cost'] = f'${(0.01 * service_units):.2f} ($0.01/SU)'
        context['signature'] = f'{context["pi_name"]}\n{context["project"]}'
        context['body'] = render_to_string('recharge_body_template.html', context)

    elif isinstance(request_obj, SecureDirRequest):
        department = request_obj.department
        context['between'] = f'RTL / Research IT and {department}/{context["pi_name"]}'
        context['re'] = f'P2/P3 Savio project Researcher Use Agreement'
        context['signature'] = f'{context["pi_name"]}\n{context["project"]}'
        context['mou_title'] = 'Researcher Use Agreement (RUA)'
        context['mou_subtitle'] = 'for using P2/P3 data in the Savio HPC environment'
        with open('./coldfront/core/utils/templates/secure_dir_body.html', 'r') as f, \
             open('./coldfront/core/utils/templates/secure_dir_footer.html', 'r') as f2:
            context['body'] = str(f.read())
            context['footer'] = str(f2.read())

    return render_to_string('mou_template.html', context)