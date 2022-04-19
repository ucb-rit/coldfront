from coldfront.core.project.models import ProjectUser
from django.db.models import Q
from flags.state import flag_enabled
import functools


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
