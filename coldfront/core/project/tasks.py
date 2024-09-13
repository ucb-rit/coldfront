import math
from datetime import datetime, timedelta

from django.core.exceptions import ImproperlyConfigured
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django_q.models import Schedule
from django_q.tasks import async_task, schedule
from flags.state import flag_enabled
from django.conf import settings

from coldfront.core.project.models import Project, ProjectStatusChoice
from coldfront.core.project.utils_.renewal_utils import get_next_allowance_year_period
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances, LRCAllowances
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.mail import send_email

computing_allowance_interface = ComputingAllowanceInterface()
if flag_enabled('BRC_ONLY'):
    ALLOWANCE_NAME = BRCAllowances.FCA
    PROJECT_NAME_PREFIX = computing_allowance_interface.code_from_name(
        ALLOWANCE_NAME)
elif flag_enabled('LRC_ONLY'):
    ALLOWANCE_NAME = LRCAllowances.PCA
    PROJECT_NAME_PREFIX = computing_allowance_interface.code_from_name(
        ALLOWANCE_NAME)
else:
    raise ImproperlyConfigured

NUM_BATCHES = 2

MINUTES_BETWEEN_BATCHES = 60

def send_tailored_email(project):
    """ This function sends one personally tailored email to the PIs/managers 
    returned by `managers_and_pis_to_email` of project. """
    alloc_period = get_next_allowance_year_period()
    template_context = {
        'project_name': project.name,
        'allocation_period': alloc_period,
        'project_prefix': PROJECT_NAME_PREFIX,
        'allowance_name': ALLOWANCE_NAME,
        'cluster_name': settings.PRIMARY_CLUSTER_NAME,
        'portal_name': settings.PORTAL_NAME,
        'portal_url': settings.CENTER_BASE_URL,
        'help_email': settings.CENTER_HELP_EMAIL,
        'email_signature': settings.EMAIL_SIGNATURE
    }

    receiver_list = []
    for receiver in project.managers_and_pis_to_email():
        receiver_list.append(receiver.user.email)

    html_message = render_to_string('email/pi_allowance_renewal_email.html', 
                                    template_context)
    plain_message = strip_tags(html_message)

    send_email(
        f'PI Computing Allowance Renewal on {alloc_period.name}',
        plain_message,
        settings.EMAIL_SENDER,
        receiver_list,
        html_body=html_message
    )

def send_batch_renewal_emails(projects):
    """ This function sends a personally tailored email (via 
    `send_tailored_email`) to the PIs/managers of each project in projects. """
    for project in projects:
        async_task('coldfront.core.project.tasks.send_tailored_email', project)

def send_mass_renewal_emails():
    """ This function gets the list of all `Active` FCAs/PCAs (depending on 
    the deployment) and splits them into NUM_BATCHES (a constant) sublists. 
    Using django-q, the function schedules calls to `send_batch_renewal_emails` 
    on each sublist with an hour between each call. """
    active_status = ProjectStatusChoice.objects.get(name='Active')

    projects = Project.objects.filter(
        name__istartswith=PROJECT_NAME_PREFIX,
        status=active_status)
    
    batch_size = math.ceil(len(projects) / NUM_BATCHES)
    now = datetime.now()
    for i in range(NUM_BATCHES):
        start = batch_size * i
        schedule(
            'coldfront.core.project.tasks.send_batch_renewal_emails',
            projects[start:start + batch_size],
            schedule_type=Schedule.ONCE,
            next_run=now + timedelta(minutes=i * MINUTES_BETWEEN_BATCHES)
        )

