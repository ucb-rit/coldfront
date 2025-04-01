from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.views.generic.base import TemplateView
from flags.state import flag_enabled
from coldfront.core.utils.gsheets import get_all_condo_allocations

from coldfront.core.allocation.models import (AllocationAttributeType,
                                              AllocationUserAttribute,
                                              AllocationRenewalRequest,
                                              AllocationAdditionRequest,
                                              SecureDirAddUserRequest,
                                              SecureDirRemoveUserRequest,
                                              SecureDirRequest,
                                              ClusterAccessRequest)
from coldfront.core.allocation.utils import annotate_queryset_with_allocation_period_not_started_bool
from coldfront.core.project.models import (ProjectUserRemovalRequest,
                                           SavioProjectAllocationRequest,
                                           VectorProjectAllocationRequest,
                                           ProjectUserJoinRequest)
from coldfront.core.project.utils_.permissions_utils import \
    is_user_manager_or_pi_of_project


class RequestListItem:
    """
    Object to keep track of all variables used in for each request type
    in the request hub
    """

    def __init__(self):
        self.num = None
        self.title = None
        self.num_pending = None
        self.table = None
        self.pending_queryset = None
        self.complete_queryset = None
        self.button_path = None
        self.button_arg1 = None
        self.button_arg2 = None
        self.button_text = None
        self.id = None
        self.help_text = None


class RequestHubView(LoginRequiredMixin,
                     UserPassesTestMixin,
                     TemplateView):
    template_name = 'request_hub/request_hub.html'
    paginate_by = 10
    paginators = 0
    show_all_requests = False

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.show_all_requests:
            if self.request.user.is_superuser or self.request.user.is_staff:
                return True
        else:
            return True

    def create_paginator(self, queryset):
        """
        Creates a paginator object for the given queryset
        and updates the context with the created object.
        """
        paginator = Paginator(queryset, self.paginate_by)
        page = self.request.GET.get(f'page{self.paginators}')
        try:
            queryset = paginator.page(page)
        except PageNotAnInteger:
            queryset = paginator.page(1)
        except EmptyPage:
            queryset = paginator.page(paginator.num_pages)

        self.paginators += 1

        return queryset

    def get_cluster_account_request(self):
        """Populates a RequestListItem with data for cluster account requests"""
        cluster_request_object = RequestListItem()

        user = self.request.user

        kwargs = {}
        if not self.show_all_requests:
            kwargs['allocation_user__user'] = user

        cluster_account_list_complete = \
            ClusterAccessRequest.objects.filter(
                status__name__in=['Denied', 'Complete'], **kwargs).order_by(
                '-modified')

        cluster_account_list_pending = \
            ClusterAccessRequest.objects.filter(
                status__name__in=['Pending - Add', 'Processing'], **kwargs).order_by(
                '-modified')

        cluster_request_object.num = self.paginators
        cluster_request_object.pending_queryset = \
            self.create_paginator(cluster_account_list_pending)

        cluster_request_object.complete_queryset = \
            self.create_paginator(cluster_account_list_complete)

        cluster_request_object.num_pending = cluster_account_list_pending.count()

        cluster_request_object.title = 'Cluster Access Requests'
        cluster_request_object.table = \
            'allocation/allocation_cluster_account_request_list_table.html'
        cluster_request_object.button_path = \
            'allocation-cluster-account-request-list'
        cluster_request_object.button_text = \
            'Go To Cluster Access Requests Main Page'
        cluster_request_object.id = 'cluster_access_request_section'
        cluster_request_object.help_text = \
            'Showing your cluster access requests.'

        return cluster_request_object

    def get_hardware_procurement_request(self):
        """Populates a RequestListItem with data for hardware
        procurement requests"""

        # Note: These imports are placed here because the hardware_procurements
        #  plugin may not necessarily be installed.
        from coldfront.plugins.hardware_procurements.utils import UserInfoDict
        from coldfront.plugins.hardware_procurements.utils.data_sources import fetch_hardware_procurements

        user = self.request.user

        fetch_hardware_procurements_kwargs = {}
        if not self.show_all_requests:
            user_data = UserInfoDict.from_user(user)
            fetch_hardware_procurements_kwargs['user_data'] = user_data

        pending_hardware_procurements = list(
            fetch_hardware_procurements(
                **{**fetch_hardware_procurements_kwargs, 'status': 'Pending'}))
        complete_hardware_procurements = list(
            fetch_hardware_procurements(
                **{**fetch_hardware_procurements_kwargs, 'status': 'Complete'}))

        hardware_procurement_request_obj = RequestListItem()
        hardware_procurement_request_obj.num = self.paginators
        hardware_procurement_request_obj.pending_queryset = \
            self.create_paginator(pending_hardware_procurements)
        hardware_procurement_request_obj.complete_queryset = \
            self.create_paginator(complete_hardware_procurements)
        hardware_procurement_request_obj.num_pending = len(
            pending_hardware_procurements)
        hardware_procurement_request_obj.title = 'Hardware Procurement Requests'
        hardware_procurement_request_obj.table = (
            'hardware_procurements/'
            'hardware_procurement_request_list_table.html')
        hardware_procurement_request_obj.button_path = (
            'hardware-procurement-list')
        hardware_procurement_request_obj.button_text = (
            'Go To Hardware Procurement Requests Main Page')
        hardware_procurement_request_obj.id = (
            'hardware_procurement_request_section')
        hardware_procurement_request_obj.help_text = (
            'Showing your hardware procurement requests.')
        return hardware_procurement_request_obj

    def get_project_removal_request(self):
        """Populates a RequestListItem with data for project removal requests"""
        removal_request_object = RequestListItem()
        user = self.request.user

        args = []
        if not self.show_all_requests:
            args.append(Q(project_user__user=user) | Q(requester=user))

        removal_request_pending = \
            ProjectUserRemovalRequest.objects.filter(
                status__name__in=['Pending', 'Processing'], *args).order_by(
                '-modified')

        removal_request_complete = \
            ProjectUserRemovalRequest.objects.filter(
                status__name='Complete', *args).order_by(
                '-modified')

        removal_request_object.num = self.paginators
        removal_request_object.pending_queryset = \
            self.create_paginator(removal_request_pending)

        removal_request_object.complete_queryset = \
            self.create_paginator(removal_request_complete)

        removal_request_object.num_pending = removal_request_pending.count()

        removal_request_object.title = 'Project Removal Requests'
        removal_request_object.table = \
            'project/project_removal/project_removal_request_list_table.html'
        removal_request_object.button_path = \
            'project-removal-request-list'
        removal_request_object.button_text = \
            'Go To Project Removal Requests Main Page'
        removal_request_object.id = 'project_removal_request_section'
        removal_request_object.help_text = \
            'Showing project removal requests that you requested or requests ' \
            'in which you are the user being removed.'

        return removal_request_object

    def get_savio_project_request(self):
        """Populates a RequestListItem with data for savio project requests"""
        savio_proj_request_object = RequestListItem()
        user = self.request.user

        args = []
        if not self.show_all_requests:
            args.append(Q(pi=user) | Q(requester=user))

        pending_status_names = ['Under Review', 'Approved - Processing']
        project_request_pending = \
            annotate_queryset_with_allocation_period_not_started_bool(
                SavioProjectAllocationRequest.objects.filter(
                    status__name__in=pending_status_names, *args
                ).order_by('-request_time'))

        complete_status_names = [
            'Approved - Complete', 'Approved - Scheduled', 'Denied']
        project_request_complete = \
            annotate_queryset_with_allocation_period_not_started_bool(
                SavioProjectAllocationRequest.objects.filter(
                    status__name__in=complete_status_names, *args
                ).order_by('-request_time'))

        savio_proj_request_object.num = self.paginators
        savio_proj_request_object.pending_queryset = \
            self.create_paginator(project_request_pending)

        savio_proj_request_object.complete_queryset = \
            self.create_paginator(project_request_complete)

        savio_proj_request_object.num_pending = project_request_pending.count()

        savio_proj_request_object.title = 'New Project Requests'
        savio_proj_request_object.table = \
            'project/project_request/savio/project_request_list_table.html'
        savio_proj_request_object.button_path = \
            'new-project-pending-request-list'
        savio_proj_request_object.button_text = \
            'Go To New Project Requests Main Page'
        savio_proj_request_object.id = 'new_project_request_section'
        savio_proj_request_object.help_text = \
            'Showing new project requests that you requested or requests ' \
            'in which you are the PI for the associated project.'

        return savio_proj_request_object

    def get_vector_project_request(self):
        """Populates a RequestListItem with data for vector project requests"""
        vector_proj_request_object = RequestListItem()
        user = self.request.user

        args = []
        if not self.show_all_requests:
            args.append(Q(pi=user) | Q(requester=user))

        project_request_pending = \
            VectorProjectAllocationRequest.objects.filter(
                status__name__in=['Under Review', 'Approved - Processing'],
                *args).order_by('-modified')

        project_request_complete = \
            VectorProjectAllocationRequest.objects.filter(
                status__name__in=['Approved - Complete', 'Denied'],
                *args).order_by('-modified')

        vector_proj_request_object.num = self.paginators
        vector_proj_request_object.pending_queryset = \
            self.create_paginator(project_request_pending)

        vector_proj_request_object.complete_queryset = \
            self.create_paginator(project_request_complete)

        vector_proj_request_object.num_pending = project_request_pending.count()

        vector_proj_request_object.title = 'Vector Project Requests'
        vector_proj_request_object.table = \
            'project/project_request/vector/project_request_list_table.html'
        vector_proj_request_object.button_path = \
            'vector-project-pending-request-list'
        vector_proj_request_object.button_text = \
            'Go To Vector Project Requests Main Page'
        vector_proj_request_object.id = 'vector_project_request_section'
        vector_proj_request_object.help_text = \
            'Showing Vector project requests that you requested or requests ' \
            'in which you are the PI for the associated project.'

        return vector_proj_request_object

    def get_project_join_request(self):
        """Populates a RequestListItem with data for project join requests"""
        proj_join_request_object = RequestListItem()
        user = self.request.user

        args = []
        if not self.show_all_requests:
            args.append(Q(project_user__user=user))

        project_join_request_pending = \
            ProjectUserJoinRequest.objects.filter(
                project_user__status__name='Pending - Add',
                *args).order_by('-modified')

        project_join_request_complete = \
            ProjectUserJoinRequest.objects.filter(
                project_user__status__name__in=['Active', 'Denied'],
                *args).order_by('-modified')

        proj_join_request_object.num = self.paginators
        proj_join_request_object.pending_queryset = \
            self.create_paginator(project_join_request_pending)

        proj_join_request_object.complete_queryset = \
            self.create_paginator(project_join_request_complete)

        proj_join_request_object.num_pending = \
            project_join_request_pending.count()

        proj_join_request_object.title = 'Project Join Requests'
        proj_join_request_object.table = \
            'project/project_join_request_list_table.html'
        proj_join_request_object.button_path = \
            'project-join-request-list'
        proj_join_request_object.button_text = \
            'Go To Project Join Requests Main Page'
        proj_join_request_object.id = 'project_join_request_section'
        proj_join_request_object.help_text = (
            'Showing your project join requests. Please contact a project '
            'manager or PI if your request has not been reviewed in a '
            'reasonable time frame.')

        return proj_join_request_object

    def get_project_renewal_request(self):
        """Populates a RequestListItem with data for project renewal
        requests"""
        proj_renewal_request_object = RequestListItem()
        user = self.request.user

        args = []
        if not self.show_all_requests:
            args.append(Q(requester=user) | Q(pi=user))

        pending_status_names = ['Under Review']
        project_renewal_request_pending = \
            annotate_queryset_with_allocation_period_not_started_bool(
                AllocationRenewalRequest.objects.filter(
                    status__name__in=pending_status_names, *args
                ).order_by('-request_time'))

        complete_status_names = ['Approved', 'Complete', 'Denied']
        project_renewal_request_complete = \
            annotate_queryset_with_allocation_period_not_started_bool(
                AllocationRenewalRequest.objects.filter(
                    status__name__in=complete_status_names, *args
                ).order_by('-request_time'))

        proj_renewal_request_object.num = self.paginators
        proj_renewal_request_object.pending_queryset = \
            self.create_paginator(project_renewal_request_pending)

        proj_renewal_request_object.complete_queryset = \
            self.create_paginator(project_renewal_request_complete)

        proj_renewal_request_object.num_pending = \
            project_renewal_request_pending.count()

        proj_renewal_request_object.title = 'Project Renewal Requests'
        proj_renewal_request_object.table = \
            'project/project_renewal/project_renewal_request_list_table.html'
        proj_renewal_request_object.button_path = \
            'pi-allocation-renewal-pending-request-list'
        proj_renewal_request_object.button_text = \
            'Go To Project Renewal Requests Main Page'
        proj_renewal_request_object.id = 'project_renewal_request_section'
        proj_renewal_request_object.help_text = \
            'Showing project renewal requests that you requested or requests ' \
            'in which you are the PI for the associated project.'

        return proj_renewal_request_object

    def get_su_purchase_request(self):
        """Populates a RequestListItem with data for SU purchase requests"""
        su_purchase_request_object = RequestListItem()
        user = self.request.user

        su_purchase_request_pending = AllocationAdditionRequest.objects.filter(
            status__name__in=['Under Review']).order_by('-modified')

        su_purchase_request_complete = AllocationAdditionRequest.objects.filter(
            status__name__in=['Complete', 'Denied']).order_by('-modified')

        if not self.show_all_requests:
            request_ids = [
                r.id for r in su_purchase_request_pending
                if is_user_manager_or_pi_of_project(user, r.project)]
            su_purchase_request_pending = \
                su_purchase_request_pending.filter(id__in=request_ids)

            request_ids = [
                r.id for r in su_purchase_request_complete
                if is_user_manager_or_pi_of_project(user, r.project)]
            su_purchase_request_complete = \
                su_purchase_request_complete.filter(id__in=request_ids)

        su_purchase_request_object.num = self.paginators
        su_purchase_request_object.pending_queryset = \
            self.create_paginator(su_purchase_request_pending)

        su_purchase_request_object.complete_queryset = \
            self.create_paginator(su_purchase_request_complete)

        su_purchase_request_object.num_pending = \
            su_purchase_request_pending.count()

        su_purchase_request_object.title = 'Service Unit Purchase Requests'
        su_purchase_request_object.table = \
            'project/project_allocation_addition/request_list_table.html'
        su_purchase_request_object.button_path = \
            'service-units-purchase-pending-request-list'
        su_purchase_request_object.button_text = \
            'Go To Service Unit Purchase Requests Main Page'
        su_purchase_request_object.id = 'service_unit_purchase_request_section'
        su_purchase_request_object.help_text = \
            'Showing service unit purchase requests in which you are a PI ' \
            'or manager for the associated project.'

        return su_purchase_request_object

    def get_secure_dir_join_request(self):
        """Populates a RequestListItem with data for secure dir join requests"""
        secure_dir_join_request_object = RequestListItem()
        user = self.request.user

        secure_dir_join_pending = SecureDirAddUserRequest.objects.filter(
            status__name__in=['Pending', 'Processing']).order_by('-modified')

        secure_dir_join_complete = SecureDirAddUserRequest.objects.filter(
            status__name__in=['Complete', 'Denied']).order_by('-modified')

        if not self.show_all_requests:
            # limit secure_dir_requests to objects user is a PI of or user has
            user_cond = Q(user=user)
            request_pks = [request.pk for request in secure_dir_join_pending if
                           request.allocation.project.projectuser_set.filter(
                               user=user,
                               role__name='Principal Investigator',
                               status__name='Active'
                           ).exists()]
            pi_cond = Q(pk__in=request_pks)

            secure_dir_join_pending = secure_dir_join_pending.filter(
                user_cond | pi_cond)

            request_pks = [request.pk for request in secure_dir_join_complete if
                           request.allocation.project.projectuser_set.filter(
                               user=user,
                               role__name='Principal Investigator',
                               status__name='Active'
                           ).exists()]
            pi_cond = Q(pk__in=request_pks)

            secure_dir_join_complete = secure_dir_join_complete.filter(
                user_cond | pi_cond)

        secure_dir_join_request_object.num = self.paginators
        secure_dir_join_request_object.pending_queryset = \
            self.create_paginator(secure_dir_join_pending)

        secure_dir_join_request_object.complete_queryset = \
            self.create_paginator(secure_dir_join_complete)

        secure_dir_join_request_object.num_pending = \
            secure_dir_join_pending.count()

        secure_dir_join_request_object.title = 'Secure Directory Join Requests'
        secure_dir_join_request_object.table = \
            'secure_dir/secure_dir_manage_user_request_list_table.html'
        secure_dir_join_request_object.button_path = \
            'secure-dir-manage-users-request-list'
        secure_dir_join_request_object.button_arg1 = \
            'add'
        secure_dir_join_request_object.button_arg2 = \
            'pending'
        secure_dir_join_request_object.button_text = \
            'Go To Secure Directory Join Requests Main Page'
        secure_dir_join_request_object.id = 'secure_dir_join_request_section'
        secure_dir_join_request_object.help_text = \
            'Showing secure directory join requests in which you are a PI ' \
            'for the associated project or in which you are the user.'

        return secure_dir_join_request_object

    def get_secure_dir_remove_request(self):
        """Populates a RequestListItem with data for secure dir
        remove requests"""
        secure_dir_remove_request_object = RequestListItem()
        user = self.request.user

        secure_dir_remove_pending = SecureDirRemoveUserRequest.objects.filter(
            status__name__in=['Pending', 'Processing']).order_by('-modified')

        secure_dir_remove_complete = SecureDirRemoveUserRequest.objects.filter(
            status__name__in=['Complete', 'Denied']).order_by('-modified')

        if not self.show_all_requests:
            # limit secure_dir_requests to objects user is a PI of or user has
            user_cond = Q(user=user)
            request_pks = [request.pk for request in secure_dir_remove_pending if
                           request.allocation.project.projectuser_set.filter(
                               user=user,
                               role__name='Principal Investigator',
                               status__name='Active'
                           ).exists()]
            pi_cond = Q(pk__in=request_pks)

            secure_dir_remove_pending = secure_dir_remove_pending.filter(
                user_cond | pi_cond)

            request_pks = [request.pk for request in secure_dir_remove_complete if
                           request.allocation.project.projectuser_set.filter(
                               user=user,
                               role__name='Principal Investigator',
                               status__name='Active'
                           ).exists()]
            pi_cond = Q(pk__in=request_pks)

            secure_dir_remove_complete = secure_dir_remove_complete.filter(
                user_cond | pi_cond)

        secure_dir_remove_request_object.num = self.paginators
        secure_dir_remove_request_object.pending_queryset = \
            self.create_paginator(secure_dir_remove_pending)

        secure_dir_remove_request_object.complete_queryset = \
            self.create_paginator(secure_dir_remove_complete)

        secure_dir_remove_request_object.num_pending = \
            secure_dir_remove_pending.count()

        secure_dir_remove_request_object.title = \
            'Secure Directory Removal Requests'
        secure_dir_remove_request_object.table = \
            'secure_dir/secure_dir_manage_user_request_list_table.html'
        secure_dir_remove_request_object.button_path = \
            'secure-dir-manage-users-request-list'
        secure_dir_remove_request_object.button_arg1 = \
            'remove'
        secure_dir_remove_request_object.button_arg2 = \
            'pending'
        secure_dir_remove_request_object.button_text = \
            'Go To Secure Directory Removal Requests Main Page'
        secure_dir_remove_request_object.id = \
            'secure_dir_remove_request_section'
        secure_dir_remove_request_object.help_text = \
            'Showing secure directory removal requests in which you are a PI ' \
            'for the associated project or in which you are the user.'

        return secure_dir_remove_request_object

    def get_secure_dir_request(self):
        """Populates a RequestListItem with data for secure dir requests"""
        secure_dir_request_object = RequestListItem()
        user = self.request.user

        secure_dir_pending = SecureDirRequest.objects.filter(
            status__name__in=['Under Review', 'Approved - Processing']).order_by('-modified')

        secure_dir_complete = SecureDirRequest.objects.filter(
            status__name__in=['Approved - Complete', 'Denied']).order_by('-modified')

        if not self.show_all_requests:
            # limit secure_dir_requests to objects user is a PI of or user has
            user_cond = Q(requester=user)
            request_pks = [request.pk for request in secure_dir_pending if
                           request.project.projectuser_set.filter(
                               user=user,
                               role__name='Principal Investigator',
                               status__name='Active'
                           ).exists()]
            pi_cond = Q(pk__in=request_pks)

            secure_dir_pending = secure_dir_pending.filter(user_cond | pi_cond)

            request_pks = [request.pk for request in secure_dir_complete if
                           request.project.projectuser_set.filter(
                               user=user,
                               role__name='Principal Investigator',
                               status__name='Active'
                           ).exists()]
            pi_cond = Q(pk__in=request_pks)

            secure_dir_complete = secure_dir_complete.filter(
                user_cond | pi_cond)

        secure_dir_request_object.num = self.paginators
        secure_dir_request_object.pending_queryset = \
            self.create_paginator(secure_dir_pending)

        secure_dir_request_object.complete_queryset = \
            self.create_paginator(secure_dir_complete)

        secure_dir_request_object.num_pending = \
            secure_dir_pending.count()

        secure_dir_request_object.title = \
            'Secure Directory Requests'
        secure_dir_request_object.table = \
            'secure_dir/secure_dir_request/secure_dir_request_list_table.html'
        secure_dir_request_object.button_path = \
            'secure-dir-pending-request-list'
        secure_dir_request_object.button_text = \
            'Go To Secure Directory Requests Main Page'
        secure_dir_request_object.id = \
            'secure_dir_request_section'
        secure_dir_request_object.help_text = \
            'Showing secure directory requests for projects where you are a PI.'

        return secure_dir_request_object

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add your existing request types to this list.
        requests = [
            'cluster_account_request',
            'project_removal_request',
            'savio_project_request',
            'vector_project_request',
            'project_join_request',
            'project_renewal_request',
            'su_purchase_request',
        ]

        if flag_enabled('SECURE_DIRS_REQUESTABLE'):
            requests += ['secure_dir_request',
                         'secure_dir_join_request',
                         'secure_dir_remove_request']

        if flag_enabled('HARDWARE_PROCUREMENTS_ENABLED'):
            requests.append('hardware_procurement_request')

        context['show_all'] = ((self.request.user.is_superuser or
                                self.request.user.is_staff) and
                               self.show_all_requests)

        for req in requests:
            request_obj = eval(f'self.get_{req}()')
            if context['show_all']:
                request_obj.help_text = f'Showing all {request_obj.title} in {settings.PORTAL_NAME}.'
            context[f'{req}_obj'] = request_obj

        context['admin_staff'] = (self.request.user.is_superuser or
                                  self.request.user.is_staff)
        context['hide_table_sorter'] = True

        return context
