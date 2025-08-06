from decimal import Decimal

from django.db import transaction
from flags.state import flag_enabled

from coldfront.api.statistics.utils import get_accounting_allocation_objects
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.utils import get_project_compute_resource_name
from coldfront.core.allocation.utils_.accounting_utils import set_service_units
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.resource.utils import get_compute_resource_names
from coldfront.core.resource.utils import get_primary_compute_resource_name
from coldfront.core.utils.common import display_time_zone_current_date
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.common import project_detail_url
from coldfront.core.utils.mail import send_email_template
from django.conf import settings
from django.db.models import Case, CharField, F, Value, When
from django.urls import reverse
from urllib.parse import urljoin


def annotate_queryset_with_cluster_name(queryset):
    """Given a queryset of Projects, annotate each instance with a
    character field named 'cluster_name', which denotes its parent
    cluster."""
    cluster_names = [name.lower() for name in get_compute_resource_names()]
    whens = [When(name__in=cluster_names, then=F('name'))]
    if flag_enabled('BRC_ONLY'):
        whens.append(
            When(name__startswith='vector_', then=Value('Vector')))
    return queryset.annotate(
        cluster_name=Case(
            *whens,
            default=Value(settings.PRIMARY_CLUSTER_NAME),
            output=CharField()))


def project_join_list_url():
    domain = import_from_settings('CENTER_BASE_URL')
    view = reverse('project-join-list')
    return urljoin(domain, view)


def render_project_compute_usage(project):
    """Return a str containing the given Project's usage of its compute
    allowance, the total allowance, and the percentage used, rounded to
    two decimal places.

    Return 'N/A':
        - If the Project's status is not 'Active'.
        - If relevant database objects cannot be retrieved. This is done
          for simplicity, even though some cases would be unexpected.

    Return 'Failed to compute' if calculations fail.

    Returns:
        - str

    Raises:
        - AssertionError
    """
    assert isinstance(project, Project)

    n_a = 'N/A'
    if project.status.name != 'Active':
        return n_a
    try:
        accounting_allocation_objects = get_accounting_allocation_objects(
            project)
    except Exception:
        return n_a

    try:
        allowance = Decimal(
            accounting_allocation_objects.allocation_attribute.value)
        usage = Decimal(
            accounting_allocation_objects.allocation_attribute_usage.value)
        # Retain two decimal places.
        percentage = (
            Decimal(100.00) * usage / allowance).quantize(Decimal('0.00'))
    except Exception:
        return 'Failed to compute'
    return f'{usage}/{allowance} ({percentage} %)'


def review_project_join_requests_url(project):
    domain = import_from_settings('CENTER_BASE_URL')
    view = reverse('project-review-join-requests', kwargs={'pk': project.pk})
    return urljoin(domain, view)


def send_added_to_project_notification_email(project, project_user):
    """Send a notification email to a user stating that they have been
    added to a project by its managers."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    subject = f'Added to Project {project.name}'
    template_name = 'email/added_to_project.txt'

    user = project_user.user

    context = {
        'user': user,
        'project_name': project.name,
        'support_email': settings.CENTER_HELP_EMAIL,
        'signature': settings.EMAIL_SIGNATURE,
    }
    if flag_enabled('BRC_ONLY'):
        context['include_docs_txt'] = (
            'deployments/brc/cluster_access_processing_docs.txt')
    elif flag_enabled('LRC_ONLY'):
        context['include_docs_txt'] = (
            'deployments/lrc/cluster_access_processing_docs.txt')

    sender = settings.EMAIL_SENDER
    receiver_list = [user.email]

    send_email_template(
        subject, template_name, context, sender, receiver_list)


def send_project_join_notification_email(project, project_user):
    """Send a notification email to the users of the given Project who
    have email notifications enabled stating that the given ProjectUser
    has requested to join it."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    user = project_user.user

    subject = f'New request to join Project {project.name}'
    context = {'PORTAL_NAME': settings.PORTAL_NAME,
               'project_name': project.name,
               'user_string': f'{user.first_name} {user.last_name} ({user.email})',
               'signature': import_from_settings('EMAIL_SIGNATURE', ''),
               'review_url': review_project_join_requests_url(project),
               'url': project_detail_url(project)}

    receiver_list = project.managers_and_pis_emails()

    send_email_template(subject,
                        'email/new_project_join_request.txt',
                        context,
                        settings.EMAIL_SENDER,
                        receiver_list,
                        html_template='email/new_project_join_request.html')


def send_project_join_request_approval_email(project, project_user):
    """Send a notification email to a user stating that their request to
    join the given project has been approved."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    subject = f'Request to Join {project.name} Approved'
    template_name = 'email/project_join_request_approved.txt'

    user = project_user.user

    context = {
        'user': user,
        'project_name': project.name,
        'support_email': settings.CENTER_HELP_EMAIL,
        'signature': settings.EMAIL_SIGNATURE,
    }
    if flag_enabled('BRC_ONLY'):
        context['include_docs_txt'] = (
            'deployments/brc/cluster_access_processing_docs.txt')
    elif flag_enabled('LRC_ONLY'):
        context['include_docs_txt'] = (
            'deployments/lrc/cluster_access_processing_docs.txt')

    sender = settings.EMAIL_SENDER
    receiver_list = [user.email]

    send_email_template(subject, template_name, context, sender, receiver_list)


def send_project_join_request_denial_email(project, project_user):
    """Send a notification email to a user stating that their request to
    join the given project has been denied."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    subject = f'Request to Join {project.name} Denied'
    template_name = 'email/project_join_request_denied.txt'

    user = project_user.user

    context = {
        'user': user,
        'project_name': project.name,
        'support_email': settings.CENTER_HELP_EMAIL,
        'signature': settings.EMAIL_SIGNATURE,
    }

    sender = settings.EMAIL_SENDER
    receiver_list = [user.email]

    send_email_template(subject, template_name, context, sender, receiver_list)


def deactivate_project_and_allocation(project, change_reason=None):
    """For the given Project, perform the following:
        1. Set its status to 'Inactive',
        2. Set its corresponding "CLUSTER_NAME Compute" Allocation's
           status to 'Expired', its start_date to the current date, and
           its end_date to None, and
        3. Reset the Service Units values and usages for the Allocation
           and its AllocationUsers.

    Parameters:
        - project (Project): an instance of the Project model
        - change_reason (str or None): An optional reason to set in
                                       created historical objects

    Returns:
        - None

    Raises:
        - AssertionError
        - MultipleObjectsReturned
        - ObjectDoesNotExist
        - TypeError"""
    assert isinstance(project, Project)

    if change_reason is None:
        change_reason = 'Zeroing service units during allocation expiration.'

    project.status = ProjectStatusChoice.objects.get(name='Inactive')

    accounting_allocation_objects = get_accounting_allocation_objects(
        project, enforce_allocation_active=False)
    allocation = accounting_allocation_objects.allocation
    allocation.status = AllocationStatusChoice.objects.get(name='Expired')
    allocation.start_date = display_time_zone_current_date()
    allocation.end_date = None

    num_service_units = settings.ALLOCATION_MIN
    set_su_kwargs = {
        'allocation_allowance': num_service_units,
        'allocation_usage': num_service_units,
        'allocation_change_reason': change_reason,
        'user_allowance': num_service_units,
        'user_usage': num_service_units,
        'user_change_reason': change_reason,
    }

    with transaction.atomic():
        project.save()
        allocation.save()
        set_service_units(accounting_allocation_objects, **set_su_kwargs)


def is_primary_cluster_project(project):
    """Return whether the Project is associated with the primary
    cluster."""
    project_compute_resource_name = get_project_compute_resource_name(project)
    primary_cluster_resource_name = get_primary_compute_resource_name()
    return project_compute_resource_name == primary_cluster_resource_name


def higher_project_user_role(role_1, role_2):
    """Given two ProjectUserRoleChoices, return the "higher" (more
    privileged) of the two."""
    assert isinstance(role_1, ProjectUserRoleChoice)
    assert isinstance(role_2, ProjectUserRoleChoice)
    roles_ascending = ['User', 'Manager', 'Principal Investigator']
    assert role_1.name in roles_ascending
    assert role_2.name in roles_ascending
    role_1_index = roles_ascending.index(role_1.name)
    role_2_index = roles_ascending.index(role_2.name)
    return role_1 if role_1_index >= role_2_index else role_2
