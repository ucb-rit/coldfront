from coldfront.core.allocation.models import (AllocationRenewalRequest,
                                              AllocationAdditionRequest,
                                              SecureDirAddUserRequest,
                                              SecureDirRemoveUserRequest,
                                              SecureDirRequest,
                                              ClusterAccessRequest)
from coldfront.core.project.models import (ProjectUserRemovalRequest,
                                           SavioProjectAllocationRequest,
                                           VectorProjectAllocationRequest,
                                           ProjectUserJoinRequest,
                                           ProjectUser)
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period

from constance import config
from django.conf import settings
from django.db.models import Q

import logging


logger = logging.getLogger(__name__)


def allocation_navbar_visibility(request):
    """Set the following context variables:
        - ALLOCATION_VISIBLE: Whether the allocation tab should be
          visible to the requesting user."""
    allocation_key = 'ALLOCATION_VISIBLE'
    context = {
        allocation_key: False,
    }

    if not request.user.is_authenticated:
        return context

    # Allocation list view should be visible to superusers and staff.
    if request.user.is_superuser or request.user.is_staff:
        context[allocation_key] = True
        return context

    # Allocation list view should be visible to active PIs and Managers.
    project_user = ProjectUser.objects.filter(
        Q(role__name__in=['Manager', 'Principal Investigator']) &
        Q(status__name='Active') &
        Q(user=request.user))
    context[allocation_key] = project_user.exists()

    return context


def constance_config(request):
    return {'CONSTANCE_CONFIG': config}


def current_allowance_year_allocation_period(request):
    context = {}
    try:
        allocation_period = get_current_allowance_year_period()
    except Exception as e:
        message = (
            f'Failed to retrieve current Allowance Year AllocationPeriod. '
            f'Details:\n'
            f'{e}')
        logger.exception(message)
    else:
        context['CURRENT_ALLOWANCE_YEAR_ALLOCATION_PERIOD'] = allocation_period
    return context


def display_time_zone(request):
    return {'DISPLAY_TIME_ZONE': settings.DISPLAY_TIME_ZONE}


def portal_and_program_names(request):
    return {
        'PORTAL_NAME': settings.PORTAL_NAME,
        'PROGRAM_NAME_LONG': settings.PROGRAM_NAME_LONG,
        'PROGRAM_NAME_SHORT': settings.PROGRAM_NAME_SHORT,
    }


def primary_cluster_name(request):
    return {
        'PRIMARY_CLUSTER_NAME': settings.PRIMARY_CLUSTER_NAME,
    }


def request_alert_counts(request):

    context = {   
        'cluster_account_req_count': ClusterAccessRequest.objects.filter(
            status__name__in=['Pending - Add', 'Processing']).count(),
        'project_removal_req_count': ProjectUserRemovalRequest.objects.filter(
            status__name__in=['Pending', 'Processing']).count(),
        'savio_project_req_count': SavioProjectAllocationRequest.objects.filter(
            status__name__in=['Under Review', 'Approved - Processing'])
            .count(),
        'vector_project_req_count': VectorProjectAllocationRequest.objects.filter(
            status__name__in=['Under Review', 'Approved - Processing']
            ).count(),
        'project_join_req_count': ProjectUserJoinRequest.objects.filter(
            project_user__status__name='Pending - Add'
            ).count(),
        'project_renewal_req_count': AllocationRenewalRequest.objects.filter(
            status__name__in=['Under Review']
            ).count(),
        'su_purchase_req_count': AllocationAdditionRequest.objects.filter(
            status__name__in=['Under Review']).count(),
        'secure_dir_join_req_count': SecureDirAddUserRequest.objects.filter(
            status__name__in=['Pending', 'Processing']).count(),
        'secure_dir_remove_req_count': SecureDirRemoveUserRequest.objects.filter(
            status__name__in=['Pending', 'Processing']).count(),
        'secure_dir_req_count': SecureDirRequest.objects.filter(
            status__name__in=['Under Review', 'Approved - Processing']).count(),
        }
    context = {k:v for k,v in context.items() if (v > 0)}
    req_count_sum = sum(context.values())
    context['request_counts'] = req_count_sum

    return context