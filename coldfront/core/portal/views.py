import operator
from collections import Counter
from collections import defaultdict

from django.conf import settings
from django.contrib.humanize.templatetags.humanize import intcomma
from django.db.models import Count, Q, Sum
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import Http404
from django.conf import settings

from flags.state import flag_enabled

from coldfront.core.allocation.models import (Allocation,
                                              AllocationUser,
                                              AllocationUserAttribute)
from coldfront.core.allocation.utils import (get_project_compute_allocation,
                                             get_project_compute_resource_name)
# from coldfront.core.grant.models import Grant
from coldfront.core.portal.utils import (generate_allocations_chart_data,
                                         generate_publication_by_year_chart_data,
                                         generate_resources_chart_data,
                                         generate_total_grants_by_agency_chart_data)
from coldfront.core.project.models import Project, ProjectUserJoinRequest
from coldfront.core.project.models import ProjectUserJoinRequest
from coldfront.core.project.models import ProjectUserRemovalRequest
from coldfront.core.project.utils import render_project_compute_usage

from coldfront.core.utils.gsheets import get_all_condo_allocations
from django.contrib.auth.decorators import login_required


# from coldfront.core.publication.models import Publication
# from coldfront.core.research_output.models import ResearchOutput


def home(request):
    context = {}
    if request.user.is_authenticated:
        template_name = 'portal/authorized_home.html'
        project_list = Project.objects.filter(
            Q(status__name__in=['New', 'Active', ]) &
            Q(projectuser__user=request.user) &
            Q(projectuser__status__name__in=['Active', 'Pending - Remove'])
        ).distinct().order_by('name')
        cluster_access_attributes = AllocationUserAttribute.objects.filter(
            allocation_attribute_type__name='Cluster Account Status',
            allocation_user__user=request.user
        )
        access_states = {}
        for attribute in cluster_access_attributes:
            project = attribute.allocation.project
            status = attribute.value
            access_states[project] = status

        for project in project_list:
            project.display_status = access_states.get(project, None)
            if project.display_status is not None and 'Active' in project.display_status:
                context['cluster_username'] = request.user.username

            resource_name = get_project_compute_resource_name(project)
            project.cluster_name = resource_name.replace(' Compute', '')
            try:
                rendered_compute_usage = render_project_compute_usage(project)
            except Exception:
                rendered_compute_usage = 'Unexpected error'
            project.rendered_compute_usage = rendered_compute_usage

        allocation_list = Allocation.objects.filter(
           Q(status__name__in=['Active', 'New', 'Renewal Requested', ]) &
           Q(project__status__name__in=['Active', 'New']) &
           Q(project__projectuser__user=request.user) &
           Q(project__projectuser__status__name__in=['Active', ]) &
           Q(allocationuser__user=request.user) &
           Q(allocationuser__status__name__in=['Active', ])
        ).distinct().order_by('-created')
        context['project_list'] = project_list
        context['allocation_list'] = allocation_list

        num_join_requests = ProjectUserJoinRequest.objects.filter(
                project_user__status__name='Pending - Add',
                project_user__user=request.user
            ).order_by('project_user', '-created').distinct('project_user').count()
        context['num_join_requests'] = num_join_requests

        context['pending_removal_request_projects'] = [
            removal_request.project_user.project.name
            for removal_request in ProjectUserRemovalRequest.objects.filter(
                Q(project_user__user__username=request.user.username) &
                Q(status__name='Pending')
            )
        ]

        if flag_enabled('HARDWARE_PROCUREMENTS_ENABLED'):

            from coldfront.plugins.hardware_procurements.utils import UserInfoDict
            from coldfront.plugins.hardware_procurements.utils.data_sources import fetch_hardware_procurements

            user_data = UserInfoDict.from_user(request.user)
            context['hardware_procurements'] = list(
                fetch_hardware_procurements(
                    user_data=user_data, status='Complete'))

    else:
        template_name = 'portal/nonauthorized_home.html'

    context['EXTRA_APPS'] = settings.EXTRA_APPS

    if 'coldfront.plugins.system_monitor' in settings.EXTRA_APPS:
        from coldfront.plugins.system_monitor.utils import get_system_monitor_context
        context.update(get_system_monitor_context())

    return render(request, template_name, context)


def center_summary(request):
    context = {}

    """
    # Publications Card
    publications_by_year = list(Publication.objects.filter(year__gte=1999).values(
        'unique_id', 'year').distinct().values('year').annotate(num_pub=Count('year')).order_by('-year'))

    publications_by_year = [(ele['year'], ele['num_pub'])
                            for ele in publications_by_year]

    publication_by_year_bar_chart_data = generate_publication_by_year_chart_data(
        publications_by_year)
    context['publication_by_year_bar_chart_data'] = publication_by_year_bar_chart_data
    context['total_publications_count'] = Publication.objects.filter(
        year__gte=1999).values('unique_id', 'year').distinct().count()

    # Research Outputs card
    context['total_research_outputs_count'] = ResearchOutput.objects.all().distinct().count()
    """

    context['total_research_outputs_count'] = 0
    context['total_publications_count'] = 0
    context['publication_by_year_bar_chart_data'] = 0

    """
    # Grants Card
    total_grants_by_agency_sum = list(Grant.objects.values(
        'funding_agency__name').annotate(total_amount=Sum('total_amount_awarded')))

    total_grants_by_agency_count = list(Grant.objects.values(
        'funding_agency__name').annotate(count=Count('total_amount_awarded')))

    total_grants_by_agency_count = {
        ele['funding_agency__name']: ele['count'] for ele in total_grants_by_agency_count}

    total_grants_by_agency = [['{}: ${} ({})'.format(
        ele['funding_agency__name'],
        intcomma(int(ele['total_amount'])),
        total_grants_by_agency_count[ele['funding_agency__name']]
    ), ele['total_amount']] for ele in total_grants_by_agency_sum]

    total_grants_by_agency = sorted(
        total_grants_by_agency, key=operator.itemgetter(1), reverse=True)
    grants_agency_chart_data = generate_total_grants_by_agency_chart_data(
        total_grants_by_agency)
    context['grants_agency_chart_data'] = grants_agency_chart_data
    context['grants_total'] = intcomma(
        int(sum(list(Grant.objects.values_list('total_amount_awarded', flat=True)))))
    context['grants_total_pi_only'] = intcomma(
        int(sum(list(Grant.objects.filter(role='PI').values_list('total_amount_awarded', flat=True)))))
    context['grants_total_copi_only'] = intcomma(
        int(sum(list(Grant.objects.filter(role='CoPI').values_list('total_amount_awarded', flat=True)))))
    context['grants_total_sp_only'] = intcomma(
        int(sum(list(Grant.objects.filter(role='SP').values_list('total_amount_awarded', flat=True)))))
    """

    context['grants_total_sp_only'] = 0
    context['grants_total_copi_only'] = 0
    context['grants_total_pi_only'] = 0
    context['grants_total'] = 0
    context['grants_agency_chart_data'] = 0

    return render(request, 'portal/center_summary.html', context)


@cache_page(60 * 15)
def allocation_by_fos(request):

    allocations_by_fos = Counter(list(Allocation.objects.filter(
        status__name='Active').values_list('project__field_of_science__description', flat=True)))

    user_allocations = AllocationUser.objects.filter(
        status__name='Active', allocation__status__name='Active')

    active_users_by_fos = Counter(list(user_allocations.values_list(
        'allocation__project__field_of_science__description', flat=True)))
    total_allocations_users = user_allocations.values(
        'user').distinct().count()

    pis = set()
    for project in Project.objects.filter(status__name__in=['Active', 'New']):
        pis.update([pi.username for pi in project.pis()])
    active_pi_count = len(pis)

    context = {}
    context['allocations_by_fos'] = dict(allocations_by_fos)
    context['active_users_by_fos'] = dict(active_users_by_fos)
    context['total_allocations_users'] = total_allocations_users
    context['active_pi_count'] = active_pi_count
    return render(request, 'portal/allocation_by_fos.html', context)


@cache_page(60 * 15)
def allocation_summary(request):

    allocation_resources = [
        allocation.get_parent_resource.parent_resource if allocation.get_parent_resource.parent_resource else allocation.get_parent_resource for allocation in Allocation.objects.filter(status__name='Active')]

    allocations_count_by_resource = dict(Counter(allocation_resources))

    allocation_count_by_resource_type = dict(
        Counter([ele.resource_type.name for ele in allocation_resources]))

    allocations_chart_data = generate_allocations_chart_data()
    resources_chart_data = generate_resources_chart_data(
        allocation_count_by_resource_type)

    context = {}
    context['allocations_chart_data'] = allocations_chart_data
    context['allocations_count_by_resource'] = allocations_count_by_resource
    context['resources_chart_data'] = resources_chart_data

    return render(request, 'portal/allocation_summary.html', context)


# TODO: Clean up.
@login_required
def decommission_details(request):
    """
    Renders a page with a list of decommission alerts.
    Each alert is displayed using configurable columns and includes a link
    to an individual detail page.
    """
    alerts = get_all_condo_allocations(request.user.email)

    context = {
        "decommission_alerts": alerts,
        "decommission_alert_columns": getattr(settings, "DECOMMISSION_ALERT_COLUMNS_KEYS", [])
    }
    return render(request, "portal/decommission_details.html", context)


from django.http import Http404


@login_required
def decommission_entry_detail(request, entry_id):
    """
    Look up a specific decommission alert for the current user using the unique id,
    and display its details using configurable columns.
    """
    alerts = get_all_condo_allocations(request.user.email)
    alert = None
    for a in alerts:
        if a.get("id") == entry_id:
            alert = a
            break
    if not alert:
        raise Http404("Decommission entry not found.")

    detail_columns = getattr(settings, "DECOMMISSION_DETAIL_COLUMNS", [])
    return render(request, "portal/decommission_entry_detail.html", {
        "alert": alert,
        "decommission_detail_columns": detail_columns,
    })