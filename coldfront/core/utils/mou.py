from coldfront.core.utils.common import import_from_settings
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
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

def get_context(request_obj):
    from coldfront.core.allocation.models import (AllocationAdditionRequest,
                                                  SecureDirRequest,
                                                  AllocationPeriod)
    from coldfront.core.project.models import SavioProjectAllocationRequest
    brc_name = 'Ken Lutz'
    pi_name = f'{request_obj.requester.first_name} {request_obj.requester.last_name}'
    between = f'{brc_name} (BRC) and {pi_name}'
    date = datetime.date.today().strftime("%B %d, %Y")
    project = request_obj.project.name

    if isinstance(request_obj, SavioProjectAllocationRequest):
        computing_allowance = ComputingAllowance(request_obj.computing_allowance)
        service_units = request_obj.computing_allowance.get_attribute('Service Units')
        if computing_allowance.is_instructional():
            course_dept = request_obj.extra_fields['course_department']
            dept_and_pi = f'{course_dept}/{pi_name}'
            re = f'{dept_and_pi} ICA Agreement'
            course_name = request_obj.extra_fields['course_name']
            point_of_contact = request_obj.extra_fields['point_of_contact']
            allowance_end = request_obj.allocation_period.end_date
            allowance_year = AllocationPeriod.objects.get(
                name__startswith='Allowance Year',
                start_date__lte=allowance_end,
                end_date__gte=allowance_end).name
            allowance_year_short = f'AY {allowance_year.split(" ")[2][2:]}/' \
                            f'{allowance_year.split(" ")[4][2:]}'
            signature = f'{pi_name}<br>{course_dept}'
            body = \
f'This document outlines the agreement between the Berkeley Research Computing (BRC) program and ' \
f'{course_dept} to provide an Instructional Computing Allowance (ICA) for computing on Savio' \
f'associated with {pi_name} course {course_name}<br><br>' \
f'The BRC ICA is provided in the context of an active partnership between the Dept of Chemistry and BRC, wherein' \
f'both parties agree to specific roles and responsibilities and associated activities:<br>' \
f'<ul><li>{dept_and_pi} agrees to name a front-line point-of-contact (specified below; this point-of-contact' \
f'for a course will generally be a course GSI) who will attempt to resolve issues and questions from students.</li>' \
f'<ul><li>Students will not contact BRC staff directly (via email, telephone, or in person) with issues.</li>' \
f'<li>All issues that cannot be resolved locally by the point-of-contact or other {course_dept} faculty or staff, will' \
f'be raised by the point-of-contact through normal BRC issue channels (e.g., brc-hpc-help@berkeley.edu).</li>' \
f'<li>For this {dept_and_pi} ICA, the point-of-contact will be {point_of_contact}</li>' \
f'<li>If {dept_and_pi} wishes to change the point-of-contact, the new person must have sufficient training' \
f'and/or experience with the high performance computing in Savio to support the students, and must be ' \
f'approved in advance by BRC staff before the change can be made.</li>' \
f'<li>Bulk account creations (e.g., a student list) will be requested at least 2 weeks before they are required for use.</li>' \
f'<li>If there are ongoing problems with students contacting BRC directly rather than going through the point-of-contact' \
f'contact, BRC reserves the right to terminate the agreement, canceling the allowance and deactivating student accounts.</li></ul>' \
f'<br><li>BRC agrees to provide an allowance of {service_units} Service Units for use on the Savio computing cluster, ' \
f'and up to 10 associated accounts for trainees. BRC will provide standard support to the point-of-contact, ' \
f'including resolution of access issues, etc.' \
f'<ul><li>The allowance will expire at the end of {allowance_end}. If {dept_and_pi} requires additional ' \
f'resources for {allowance_year_short}, a renewal application can be submitted in May 2021.</li>' \
f'<li>The point-of-contact is responsible for monitoring the activity against the allowance and ensuring any policies ' \
f'about individual usage. As a default, BRC will impose per-job time and core-count limits and per-user number of job ' \
f'limits to avoid situations where one trainee accidentally uses a large fraction of the allowance in a short ' \
f'period of time, but these limits could be relaxed based on consensus of BRC and {dept_and_pi}.</li>' \
f'<li>The student/trainee accounts on Savio will be disablde ed when the allowance expires, ' \
f'unless a renewal agreement has been approved.</li></ul><br>' \
f'This agreement is understood to be a pilot, to work through issues in supporting instruction with ' \
f'BRC resources. The solution described for limiting job-time and core-counts is a simple bridge solution for the ' \
f'term of this MOU and cannot provide all the features that might be desired; BRC hopes to replace it with a more robust ' \
f'solution which is currently under development. {dept_and_pi} staff will work with BRC staff during the term of ' \
f'this MOU to clarify requirements for monitoring student usage under an ICA.'

        elif computing_allowance.is_recharge():
            re = f'{project} Savio Allowance Purchase Agreement'
            cost = f'${(0.01 * service_units):.2f} ($0.01/SU)'
            chartstring = request_obj.extra_fields['campus_chartstring']
            signature = f'{pi_name}<br>{project}'

    if isinstance(request_obj, AllocationAdditionRequest):
        re = f'{project} Savio Allowance Purchase Agreement'
        service_units = int(request_obj.num_service_units)
        chartstring = request_obj.extra_fields['campus_chartstring']
        cost = f'${(0.01 * service_units):.2f} ($0.01/SU)'
        signature = f'{pi_name}<br>{project}'
        body = \
f'This MOU describes the working agreement by which project {project} will obtain an additional allowance for use of ' \
f'the Berkeley Research Computing (BRC) Savio cluster.<br><br>' \
f'An allowance of {service_units} service units (SUs) will be created for {pi_name}. This purchased allowance will be ' \
f'separate from any Faculty Computing Allowance, so that the associated "budgets" can be managed separately. This ' \
f'purchased allowance will function largely the same as the Faculty Computing Allowance (FCA); {pi_name} will ' \
f'determine who has access, and will manage the shared resource among their Lab members. Purchased allowances ' \
f'differ from FCAs in two important ways: unlike the FCA, this purchased allowance will not expire at the end of the ' \
f'fiscal year; it will remain available until exhausted, or replenished with a subsequent purchase agreement. Also, this ' \
f'MOU allowance will be reimbursed for SUs lost if jobs fail or are killed due to unplanned downtime.<br><br>' \
f'The associated expense of {cost} will be transferred by the BRC program financial staff to the COA:<br><br>' \
f'&emsp;{chartstring}<br><br>' \
f'Once this transfer is complete, the allowance access will be enabled.<br><br>' \
f'BRC staff will provide {project} with the details for using the purchased allowance, including how to submit ' \
f'jobs to Savio using this allowance.<br><br>' \
f'The purchased allowance is pre-paid and non-refundable.<br><br>' \
f'This agreement will remain in effect until the purchased allowance is exhausted. If additional access is needed, ' \
f'additional separate MOU\'s may be negotiated.'
    return dict(between=between, date=date, re=re, signature=signature, body=body)