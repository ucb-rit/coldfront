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
    date = datetime.date.today().strftime("%B %d, %Y")
    project = request_obj.project.name
    mou_title = 'Memorandum of Understanding'
    mou_subtitle = ''
    footer = ''

    if isinstance(request_obj, SavioProjectAllocationRequest) and \
                        ComputingAllowance(request_obj.computing_allowance) \
                            .is_instructional():
        service_units = request_obj.computing_allowance \
                                                .get_attribute('Service Units')
        course_dept = request_obj.extra_fields['course_department']
        dept_and_pi = f'{course_dept}/{pi_name}'
        between = f'{brc_name} (BRC) and {pi_name}'
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
            f'{course_dept} to provide an Instructional Computing Allowance (ICA) for computing on Savio ' \
            f'associated with {pi_name}\'s course {course_name}<br><br>' \
            f'The BRC ICA is provided in the context of an active partnership between {dept_and_pi} and BRC, wherein ' \
            f'both parties agree to specific roles and responsibilities and associated activities:<br>' \
            f'<ul><li>{dept_and_pi} agrees to name a front-line point-of-contact (specified below; this point-of-contact ' \
            f'for a course will generally be a course GSI) who will attempt to resolve issues and questions from students.</li>' \
            f'<ul><li>Students will not contact BRC staff directly (via email, telephone, or in person) with issues.</li>' \
            f'<li>All issues that cannot be resolved locally by the point-of-contact or other {course_dept} faculty or staff, will ' \
            f'be raised by the point-of-contact through normal BRC issue channels (e.g., brc-hpc-help@berkeley.edu).</li>' \
            f'<li>For this {dept_and_pi} ICA, the point-of-contact will be {point_of_contact}</li>' \
            f'<li>If {dept_and_pi} wishes to change the point-of-contact, the new person must have sufficient training ' \
            f'and/or experience with the high performance computing in Savio to support the students, and must be ' \
            f'approved in advance by BRC staff before the change can be made.</li>' \
            f'<li>Bulk account creations (e.g., a student list) will be requested at least 2 weeks before they are required for use.</li>' \
            f'<li>If there are ongoing problems with students contacting BRC directly rather than going through the point-of-contact ' \
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

    elif isinstance(request_obj, AllocationAdditionRequest) or \
                (isinstance(request_obj, SavioProjectAllocationRequest) and \
                ComputingAllowance(request_obj.computing_allowance)\
                                                        .is_recharge()):
        between = f'{brc_name} (BRC) and {pi_name}'
        re = f'{project} Savio Allowance Purchase Agreement'
        if isinstance(request_obj, AllocationAdditionRequest):
            service_units = int(request_obj.num_service_units)
        else:
            service_units = int(request_obj.extra_fields['num_service_units'])
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

    elif isinstance(request_obj, SecureDirRequest):
        between = f'Research IT (Research, Teaching and Learning) and {pi_name}'
        re = f'P3 Savio project Researcher Use Agreement'
        signature = f'{pi_name}<br>{project}'
        mou_title = 'Researcher Use Agreement (RUA)'
        mou_subtitle = 'for using P3 data in the Savio HPC environment'
        body = \
'''
This document outlines the agreement between the Berkeley Research Computing (BRC) program and the PI named above (hereafter referred to as "the PI") for the use of P3 data, as defined in the UC Berkeley Data Classification Standard, in the Savio High Performing Computing (HPC) system. The agreement is based upon a shared responsibility model for ensuring the security of the data, and compliance with the UC Berkeley Minimum Security Standard for Electronic Information policy and any associated Data Use Agreement (DUA). This agreement details the responsibilities of the PI, as well as any other researchers that are granted access by the PI to use the data in Savio. 
<br><br>Before use of P3 data in Savio, Research IT staff will evaluate the data protection level of the data in question, which generally involves a review of relevant data use agreement (DUA) requirements to ensure Savio is in compliance. If Research IT staff deem it necessary, the evaluation will be escalated to Information Security & Policy (ISP) for a more formal data protection level assessment. If the data meet the requirements of the review and other approval requirements, the request for access may be granted. If the assessment reveals that the data are at the P4 level, Savio will not be allowed to be used for the research project. 
<br><br>The responsibilities are described in alignment with the Savio MSSEI PL1 Self-Assessment Plan; section numbers are references to that plan. In the text below, "Principal Investigator" and "PI" should be understood to be the project lead (generally the PI, and/or whoever signs the DUA), and "Researchers" includes all approved users in the group. 
<br><br>In addition to the researcher responsibilities described in this Agreement, researchers must be familiar with the Savio PL1 Incident Response Plan and the end-user requirements therein that are associated with responding to suspicious cybersecurity events. UC Berkeley's Information Security and Policy Incident Response Planning Guide, defines a suspicious event as:
<p style='margin-left: 80px;'>
An event that compromises or has the potential to compromise: the operation of covered core systems or confidentiality or integrity of covered data assets.
<br><br>A security incident may involve any or all of the following:
<ul style='margin-left: 80px;'><li>a violation of campus computer security policies and standards</li>
<li>unauthorized computer or data access</li>
<li>presence of a malicious application, such as a virus</li>
<li>presence of unexpected/unusual programs</li>
<li>a denial of service condition against data, network or computer</li>
<li>misuse of service, systems or information</li>
<li>physical or logical damage to systems</li>
<li>computer theft</li></ul></p>
<br>Researchers have access to a range of software that is managed by BRC staff, both in the base software image available on each node, as well as in the main shared modules collection. Researchers should prefer this software and these versions where this is practical; when using other software it is the researcher's responsibility to ensure that it will not compromise system security.
<h2>1.1 Removal of non-required covered data</h2>
<p style='margin-left: 40px;'>
Researchers are responsible for the removal of non-required covered data for their P3 research projects. See 15.3 Secure deletion upon decommission and 15.4 Data Access Agreement for further details. 
<br><br>For data covered under the NIH guidelines for cloud providers, see also the document NIH Active Research workflow for NIH data for removing unencrypted data from scratch.
</p><h2>8.1 Privacy and Security Training</h2>
<p style='margin-left: 40px;'>
The PI for each P3 project is responsible for ensuring that all users with access to the data in the Savio environment have completed required training in the use of the data, and in the use of the Savio infrastructure. All users with access should be familiar with the terms of this RUA.
</p><h2>9.1 Privacy and Security Training</h2>
<p style='margin-left: 40px;'>
All researchers with access to the Savio environment are bound by the terms of the campus Computer Use Policy (https://security.berkeley.edu/computer-use-policy), specifically including the management of strong passwords. Users may not share accounts, nor may they share passwords or other credentials. 
</p><h2>13.1 Controlled access based on need to know</h2>
<p style='margin-left: 40px;'>
Access to the Savio system is available to UC Berkeley principal investigators (PIs) and their associated researchers through the Faculty Computing Allowance (FCA) and Condo programs. Students may also gain access to the system through the Instructional Computing Allowance program. All users of the system must complete the BRC User Access Agreement form, and as such must accept and are subject to the Campus Computer Use Policy. All requests for access are reviewed by Research IT staff. 
<br><br>For access to covered P3 data, researchers must submit a request to BRC/Savio administrators to add their user account to the file permissions for the group directory/folder where the P3 data is stored. The request for access must be authorized by the PI (principal investigator) before being granted. BRC Savio administrators will verify the access request with the PI via email. 
<br><br>The Savio environment does not have an automated process to remove employees' access once they are no longer employed. However, by agreement and acceptance of our shared responsibility model for system security, Researchers must notify cluster administrators when a user is no longer a member of the project team using the covered system. 
<br><br>Research IT will conduct a semi-annual email-based confirmation of active users. Savio P3 accounts of those who are no longer active users will be deactivated. 
<br><br>UC Berkeley PIs must vouch for users at other institutions, and they must let us know if/when a user is no longer with the institution. 
</p><h2>14.1 Account monitoring and management</h2>
<p style='margin-left: 40px;'>
Principal Investigators (PIs) are responsible for monitoring account access to covered P3 data within the Savio environment. The Savio team will provide PIs with Linux command line syntax for checking group directory permissions to verify which user accounts have access. The Savio team will also create a spreadsheet for the project, that will allow the PI to specify which users should be members of the group (i.e., which are allowed to have access to the resources). It is the responsibility of the PI to keep this spreadsheet current, and in particular, to remove users that should no longer have access. 
</p><h2>15.1 Encryption in transit</h2>
<p style='margin-left: 40px;'>
Researchers shall not use the DTN or other data transfer means to move any P3 data in an unencrypted form. Researchers are responsible for training all users to ensure that unencrypted data is not transferred out of the Savio infrastructure, copied or moved onto personal or other devices.
</p><h2>15.2 Encryption on mobile devices and removable media </h2>
<p style='margin-left: 40px;'>
Researchers must not download covered data to their personal laptop if it is not encrypted. Note also that campus policy requires that users not copy covered P3 data to unencrypted mobile devices. Finally, note that if users download covered data onto any personal device, it is their sole responsibility to manage secure deletion of the data at the end of the project. (See also 15.3 Secure deletion upon decommission). 
<br><br>Note that covered P3 data may not be stored in user directories in Savio. This policy ensures that covered data will not be included in UC Backup program, which avoids the potential for data to reside on unencrypted tape media, and simplifies the deletion of covered data at the end of a project. 
</p><h2>15.3 Secure deletion upon decommission</h2>
<p style='margin-left: 40px;'>
Researchers and PIs are responsible for secure deletion of covered P3 data at the end of their research project. This includes both data on project storage areas, as well as in scratch<sup>1</sup>. 
<br><br>Project storage: All files on the project storage array should be deleted using normal file removal commands (e.g., rm). Inasmuch as all files on project storage must be encrypted, this will suffice. 
<br><br>Scratch (parallel filesystem) storage: All files (including in particular decrypted files and derivatives) must be deleted using a secure deletion utility such as shred. While users may choose to use the default number of passes (3), it is sufficient to run a single pass over the data; for large files this will significantly reduce the resources required to complete the secure deletion<sup>2</sup>. 
</p><h2>Additional NIH Security Best Practices for Controlled-Access Data Subject to the NIH Genomic Data Sharing (GDS) Policy ("NIH Data")</h2>
<p style='margin-left: 40px;'>
In addition to the campus security policy requirements listed above, Researchers working with NIH dbGaP data are responsible for the NIH security requirements detailed below. These requirements and guidelines refer to the NIH Security Best Practices document. See that original<sup>3</sup> for details. 
<br><ul style='margin-left: 40px'><li> Researchers working with NIH data must not post this data, or otherwise make it publicly available. BRC staff will not make any NIH data publicly available.
</li><li>NIH requires that approved users must retain the original version of the encrypted data, track all copies or extracts and ensure that the information is not divulged to anyone except authorized staff members at the institution. NIH therefore recommends ensuring careful control of physical copies of data and providing appropriate logging on machines where such data is resident. This is the responsibility of the P3 project PI.
</li><li> As collaborating investigators from other institutions must submit an independent DAR and be approved by NIH to access to the data, restrict outbound access from devices that host controlled access data.
</li><li>Only those researchers specifically authorized in the NIH agreement are permitted access to covered data. Covered data must not be shared with other institutions; collaborators at other institutions must have their own data access request (DAR). Controlled data cannot be copied from the Savio environment to other institutions (or to storage accessible to other researchers) that are not governed by the original DAR.
</li><li>Investigators and Institutions may retain only encrypted copies of the minimum data necessary at their institution to comply with institutional scientific data retention policy and any data stored on temporary backup media as are required to maintain the integrity of the institution's data protection program. Ideally, the data will exist on backup media that is not used by other projects and can therefore be destroyed or erased without impacting other users/tenants. If retaining the data on separate backup media is not possible, as will be the case with many users, the media may be retained for the standard media retention period but may not be recovered for any purpose without a new Data Access Request approved by the NIH. Retained data should be deleted at the appropriate time, according to institutional policies. Note that no covered data may be stored in home directories, which are the only area in Savio on which BRC performs backups, and so this section applies to backups created by the PI and associated researchers; the PI is responsible for any backups generated.
</li><li>Encrypt data at rest with a user's own keys. SRA-toolkit includes this feature; other software providers offer tools to meet this requirement. The NIH Active Research workflow for NIH data in Savio describes requirements and responsibilities for deletion of unencrypted data when not in active use (i.e., at rest).
</li></ul></p><br>This agreement will cover all current and future datasets, throughout the period of time that the researcher (and designated collaborators) are utilizing the Research IT resources.
'''
        footer = \
            '<sup>1</sup> If users have data on a personal device (laptops, workstations, etc.), they should review the campus Secure Deletion Guideline (available at: https://security.berkeley.edu/secure-deletion-guideline) for more information on secure deletion of data.' \
            '<br><sup>2</sup>For an analysis of the issues, see Wright C., Kleiman D., and Shyaam S. R. S., (2008). "Overwriting Hard Drive Data: The Great  Wiping Controversy", Lecture Notes in Computer Science (Springer Berlin / Heidelberg). Available at: https://www.researchgate.net/publication/221160815_Overwriting_Hard_Drive_Data_The_Great_Wiping_Controvers' \
            '<br><sup>3</sup> Available at: https://osp.od.nih.gov/wp-content/uploads/NIH_Best_Practices_for_Controlled_Access_Data_Subject_to_the_NIH_GDS_Policy.pdf'
    return dict(mou_title=mou_title, mou_subtitle=mou_subtitle, between=between,
                date=date, re=re, signature=signature, body=body, footer=footer)