from coldfront.core.project.models import ProjectUser
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period

from constance import config
from django.conf import settings
from django.db.models import Q

from flags.state import flag_enabled

import functools
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


def billing_navbar_visibility(request):
    """Set the following context variables:
        - BILLING_MENU_VISIBLE: Whether the Billing menu should be
          visible to the requesting user.
        - BILLING_MENU_RECHARGE_TAB_VISIBLE: Whether the Recharge tab of
          the Billing menu should be visible to the requesting user."""
    menu_key = 'BILLING_MENU_VISIBLE'
    recharge_tab_key = 'BILLING_MENU_RECHARGE_TAB_VISIBLE'
    context = {
        menu_key: False,
        recharge_tab_key: False,
    }

    if not flag_enabled('LRC_ONLY'):
        return context
    if not request.user.is_authenticated:
        return context

    # Both should be visible to superusers and staff.
    if request.user.is_superuser or request.user.is_staff:
        context[menu_key] = True
        context[recharge_tab_key] = True
        return context

    # The Billing menu should be visible to active PIs and Managers of
    # Lawrencium projects.
    project_prefixes = ('ac_', 'lr_', 'pc_')
    is_lawrencium_project_condition = functools.reduce(
        lambda a, b: a | b,
        [Q(project__name__startswith=prefix) for prefix in project_prefixes])
    lawrencium_project_users = ProjectUser.objects.filter(
        is_lawrencium_project_condition &
        Q(role__name__in=['Manager', 'Principal Investigator']) &
        Q(status__name='Active') &
        Q(user=request.user))
    context[menu_key] = lawrencium_project_users.exists()

    # The Recharge tab of the Billing menu should be visible to active PIs and
    # Managers of Recharge projects.
    if context[menu_key]:
        recharge_project_users = lawrencium_project_users.filter(
            project__name__startswith='ac_')
        context[recharge_tab_key] = recharge_project_users.exists()

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
