from collections import defaultdict
from itertools import chain

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q, QuerySet
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from iso8601 import iso8601

from coldfront.core.allocation.forms_.cluster_acct_deletion_forms import \
    ClusterAcctDeletionRequestForm, ClusterAcctDeletionRequestSearchForm, \
    ClusterAcctDeletionEligibleUsersSearchForm
from coldfront.core.allocation.models import (Allocation,
                                              AllocationAttributeType,
                                              AllocationUserStatusChoice,
                                              ClusterAcctDeletionRequest)
from coldfront.core.allocation.utils_.cluster_acct_deletion_utils import \
    ClusterAcctDeletionRequestRunner

from coldfront.core.project.forms_.removal_forms import \
    (ProjectRemovalRequestSearchForm,
     ProjectRemovalRequestUpdateStatusForm,
     ProjectRemovalRequestCompletionForm)
from coldfront.core.project.models import (Project,
                                           ProjectUserStatusChoice,
                                           ProjectUserRemovalRequest,
                                           ProjectUserRemovalRequestStatusChoice,
                                           ProjectUser)
from coldfront.core.project.utils_.removal_utils import \
    ProjectRemovalRequestRunner
from coldfront.core.utils.common import (import_from_settings,
                                         utc_now_offset_aware)
from coldfront.core.utils.mail import send_email_template

import logging

from coldfront.core.utils.views import ListViewClass

EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED', False)


class ClusterAcctDeletionRequestFormView(LoginRequiredMixin,
                                         UserPassesTestMixin,
                                         FormView):
    logger = logging.getLogger(__name__)
    form_class = ClusterAcctDeletionRequestForm
    template_name = \
        'cluster_acct_deletion/cluster_acct_deletion_user.html'

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        if self.request.user == self.user_obj:
            return True

        # TODO: who can request account deletion? Should we block PIs from deleting accounts?
        # PIs that are PIs for projects that the user belongs to.
        if self.is_pi:
            return True

    def dispatch(self, request, *args, **kwargs):
        self.user_obj = get_object_or_404(User, pk=self.kwargs.get('pk'))
        user_projects = \
            ProjectUser.objects.filter(
                user=self.user_obj,
                status__name='Active').values_list('project', flat=True)
        self.is_pi = ProjectUser.objects.filter(
            user=self.request.user,
            role__name__in=['Principal Investigator'],
            status__name='Active',
            project__in=user_projects).exists()

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            if self.is_pi:
                requester_str = 'PI'
            elif self.request.user == self.user_obj:
                requester_str = 'User'
            else:
                requester_str = 'System'

            request_runner = ClusterAcctDeletionRequestRunner(self.user_obj,
                                                              requester_str)
            runner_result = request_runner.run()
            success_messages, error_messages = request_runner.get_messages()

            if runner_result:
                request_runner.send_emails()
                for message in success_messages:
                    messages.success(self.request, message)
            else:
                for message in error_messages:
                    messages.error(self.request, message)
        except Exception as e:
            self.logger.exception(e)
            error_message = \
                'Unexpected error. Please contact an administrator.'
            messages.error(self.request, error_message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_obj'] = self.user_obj
        context['user_str'] = f'{self.user_obj.first_name} ' \
                              f'{self.user_obj.last_name}'

        if self.is_pi or self.request.user.is_superuser:
            context['back_url'] = 'cluster-account-deletion-eligible-users'
        else:
            context['back_url'] = 'home'

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['requester'] = self.request.user
        kwargs['user_obj'] = self.user_obj

        return kwargs

    def get_success_url(self):
        return reverse('home')


class ClusterAcctDeletionRequestEligibleUsersView(LoginRequiredMixin,
                                                  UserPassesTestMixin,
                                                  ListViewClass):
    template_name = \
        'cluster_acct_deletion/cluster_acct_deletion_eligible_users.html'
    paginate_by = 25
    context_object_name = 'eligible_users'
    
    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        if ProjectUser.objects.filter(
                user=self.request.user,
                role__name__in=['Principal Investigator'],
                status__name='Active').exists():
            return True

    def get_queryset(self):
        # TODO: can managers' accounts be deleted?
        if self.request.user.is_superuser:
            proj_eligible_users_to_delete = ProjectUser.objects.filter(
                role__name='User').order_by('user__username')
        else:
            pi_projects = ProjectUser.objects.filter(
                user=self.request.user,
                role__name__in=['Principal Investigator'],
                status__name='Active').values_list('project', flat=True)

            proj_eligible_users_to_delete = ProjectUser.objects.filter(
                project__in=pi_projects,
                role__name='User').order_by('user__username')

        pending_deletion_requests = \
            ClusterAcctDeletionRequest.objects.filter(
                status__name__in=['Queued', 'Ready', 'Processing'])

        proj_eligible_users_to_delete = proj_eligible_users_to_delete.exclude(
            user__in=pending_deletion_requests.values_list('user',
                                                           flat=True)).exclude(
            user=self.request.user).order_by('user__username')

        search_form = ClusterAcctDeletionEligibleUsersSearchForm(
            self.request.GET)
        if search_form.is_valid():
            data = search_form.cleaned_data

            if data.get('username'):
                proj_eligible_users_to_delete = proj_eligible_users_to_delete.filter(
                    user__username__icontains=data.get('username'))

            if data.get('first_name'):
                proj_eligible_users_to_delete = proj_eligible_users_to_delete.filter(
                    user__first_name__icontains=data.get('first_name'))

            if data.get('last_name'):
                proj_eligible_users_to_delete = proj_eligible_users_to_delete.filter(
                    user__last_name__icontains=data.get('last_name'))

        eligible_users_to_delete = defaultdict()
        for proj_user in proj_eligible_users_to_delete:
            if proj_user.user in eligible_users_to_delete:
                eligible_users_to_delete[proj_user.user]['projects'].append(
                    proj_user.project.name)
            else:
                eligible_users_to_delete[proj_user.user] = {
                    'user': proj_user.user,
                    'projects': [proj_user.project.name]
                }

        # Filter on projects separately so that all projects are still shown in table.
        project_filter = None
        if search_form.is_valid():
            project_filter = search_form.cleaned_data.get('project')

        # Making a user friendly string of the user's projects.
        for user, data in eligible_users_to_delete.copy().items():
            flag = False
            if project_filter:
                for project in data['projects']:
                    if project_filter not in project:
                        eligible_users_to_delete.pop(user)
                        flag = True
                        break
            if flag:
                continue
            data['projects'] = ', '.join(data['projects'])
            eligible_users_to_delete[user] = data

        # Need to create a tuple for the paginator.
        eligible_users_to_delete = tuple(eligible_users_to_delete.values())

        return eligible_users_to_delete

    def get_context_data(self, **kwargs):
        kwargs.update({'search_form': ClusterAcctDeletionEligibleUsersSearchForm})
        context = super().get_context_data(**kwargs)
        return context


class ClusterAcctDeletionRequestListView(LoginRequiredMixin,
                                         UserPassesTestMixin,
                                         ListView):
    model = ClusterAcctDeletionRequest
    template_name = \
        'cluster_acct_deletion/cluster_acct_deletion_request_list.html'
    context_object_name = 'cluster_acct_deletion_requests'
    paginate_by = 25

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm(
                'allocation.view_ClusterAcctDeletionrequest'):
            return True

    def get_queryset(self):
        request_search_form = ClusterAcctDeletionRequestSearchForm(
            self.request.GET)
        if request_search_form.is_valid():
            # TODO: ordery by
            data = request_search_form.cleaned_data
            queryset = ClusterAcctDeletionRequest.objects.all()

            if data.get('username'):
                queryset = queryset.filter(
                    user__username__icontains=data.get('username'))

            if data.get('first_name'):
                queryset = queryset.filter(
                    user__first_name__icontains=data.get('first_name'))

            if data.get('last_name'):
                queryset = queryset.filter(
                    user__last_name__icontains=data.get('last_name'))

            if data.get('status'):
                queryset = queryset.filter(status__name=data.get('status'))
            else:
                queryset = queryset.filter(status__name='Ready')

            if data.get('requester'):
                queryset = queryset.filter(
                    requester__name=data.get('requester'))

        else:
            queryset = ClusterAcctDeletionRequest.objects.filter(
                status__name='Ready').order_by('created')

        return queryset

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context['status'] = 'Ready'

        request_search_form = ClusterAcctDeletionRequestSearchForm(
            self.request.GET)

        if request_search_form.is_valid():
            context['request_search_form'] = request_search_form
            data = request_search_form.cleaned_data
            filter_parameters = ''
            for key, value in data.items():
                if value:
                    if isinstance(value, QuerySet):
                        for ele in value:
                            filter_parameters += '{}={}&'.format(key, ele.pk)
                    else:
                        filter_parameters += '{}={}&'.format(key, value)
            context['request_search_form'] = request_search_form

            if data.get('status'):
                context['status'] = data.get('status')
        else:
            filter_parameters = ''
            context[
                'request_search_form'] = ClusterAcctDeletionRequestSearchForm()

        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            filter_parameters_with_order_by = filter_parameters + \
                                              'order_by=%s&direction=%s&' % (
                                                  order_by, direction)
        else:
            filter_parameters_with_order_by = filter_parameters

        if filter_parameters:
            context['expand_accordion'] = 'show'
        context['filter_parameters'] = filter_parameters
        context[
            'filter_parameters_with_order_by'] = filter_parameters_with_order_by

        context['expand_accordion'] = 'show'

        cluster_acct_deletion_requests = context.get(
            'cluster_acct_deletion_requests')
        paginator = Paginator(cluster_acct_deletion_requests,
                              self.paginate_by)

        page = self.request.GET.get('page')

        try:
            cluster_acct_deletion_requests = paginator.page(page)
        except PageNotAnInteger:
            cluster_acct_deletion_requests = paginator.page(1)
        except EmptyPage:
            cluster_acct_deletion_requests = paginator.page(
                paginator.num_pages)

        context['actions_visible'] = self.request.user.is_superuser and \
                                     context['status'] not in ['Complete',
                                                               'Canceled']

        return context


class ClusterAcctDeletionRequestMixin(object):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_obj = None

    # def redirect_if_disallowed_status(self, http_request,
    #                                   disallowed_status_names=(
    #                                           'Approved - Complete',
    #                                           'Denied')):
    #     """Return a redirect response to the detail view for this
    #     project request if its status has one of the given disallowed
    #     names, after sending a message to the user. Otherwise, return
    #     None."""
    #     if not isinstance(self.request_obj, SecureDirRequest):
    #         raise TypeError(
    #             f'Request object has unexpected type '
    #             f'{type(self.request_obj)}.')
    #     status_name = self.request_obj.status.name
    #     if status_name in disallowed_status_names:
    #         message = (
    #             f'You cannot perform this action on a request with status '
    #             f'{status_name}.')
    #         messages.error(http_request, message)
    #         return HttpResponseRedirect(
    #             self.request_detail_url(self.request_obj.pk))
    #     return None

    @staticmethod
    def request_detail_url(pk):
        """Return the URL to the detail view for the request with the
        given primary key."""
        return reverse('cluster-account-deletion-request-detail',
                       kwargs={'pk': pk})

    def set_request_obj(self, pk):
        """Set this instance's request_obj to be the
        ClusterAcctDeletionRequest with the given primary key."""
        self.request_obj = get_object_or_404(ClusterAcctDeletionRequest,
                                             pk=pk)


class ClusterAcctDeletionRequestDetailView(LoginRequiredMixin,
                                           UserPassesTestMixin,
                                           ClusterAcctDeletionRequestMixin,
                                           DetailView):
    model = ClusterAcctDeletionRequest
    template_name = 'cluster_acct_deletion/cluster_acct_deletion_detail.html'
    login_url = '/'
    context_object_name = 'cluster_acct_deletion_request'

    logger = logging.getLogger(__name__)

    error_message = 'Unexpected failure. Please contact an administrator.'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm(
                'allocation.view_ClusterAcctDeletionrequest'):
            return True

        if self.request.user == self.request_obj.user:
            return True

        # if the user is a pi of a project the user belongs to. if we
        # delete/disable project users, we need a way to keep track of this.
        projects = ProjectUser.objects.filter(
            user=self.request.user).values_list('project', flat=True)
        for project in projects:
            if self.request.user in project.pis():
                return True

        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_request_obj(pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            latest_update_timestamp = \
                self.request_obj.latest_update_timestamp()
            if not latest_update_timestamp:
                latest_update_timestamp = 'No updates yet.'
            else:
                # TODO: Upgrade to Python 3.7+ to use this.
                # latest_update_timestamp = datetime.datetime.fromisoformat(
                #     latest_update_timestamp)
                latest_update_timestamp = iso8601.parse_date(
                    latest_update_timestamp)
        except Exception as e:
            self.logger.exception(e)
            messages.error(self.request, self.error_message)
            latest_update_timestamp = 'Failed to determine timestamp.'
        context['latest_update_timestamp'] = latest_update_timestamp

        context['checklist'] = self.get_checklist()
        # context['setup_status'] = self.get_setup_status()
        # context['is_checklist_complete'] = self.is_checklist_complete()

        context['is_allowed_to_manage_request'] = \
            self.request.user.is_superuser

        context['request_obj'] = self.request_obj

        projects = ProjectUser.objects.filter(
            user=self.request_obj.user).values_list('project__name', flat=True)
        context['user_projects'] = ', '.join(projects)

        return context

    def get_checklist(self):
        """Return a nested list, where each row contains the details of
        one item on the checklist.
        Each row is of the form: [task text, status name, latest update
        timestamp, is "Manage" button available, URL of "Manage"
        button.]"""
        pk = self.request_obj.pk
        state = self.request_obj.state
        checklist = []

        # TODO: need to know what processing steps are.

        # rdm = state['rdm_consultation']
        # checklist.append([
        #     'Confirm that the PI has consulted with RDM.',
        #     rdm['status'],
        #     rdm['timestamp'],
        #     True,
        #     reverse(
        #         'secure-dir-request-review-rdm-consultation', kwargs={'pk': pk})
        # ])
        # rdm_consulted = rdm['status'] == 'Approved'
        #
        # mou = state['mou']
        # checklist.append([
        #     'Confirm that the PI has signed the Memorandum of Understanding.',
        #     mou['status'],
        #     mou['timestamp'],
        #     True,
        #     reverse(
        #         'secure-dir-request-review-mou', kwargs={'pk': pk})
        # ])
        # mou_signed = mou['status'] == 'Approved'
        #
        # setup = state['setup']
        # checklist.append([
        #     'Perform secure directory setup on the cluster.',
        #     self.get_setup_status(),
        #     setup['timestamp'],
        #     rdm_consulted and mou_signed,
        #     reverse('secure-dir-request-review-setup', kwargs={'pk': pk})
        # ])

        # THIS IS A PLACEHOLDER
        checklist.append([
            'This is a placeholder',
            'Pending',
            utc_now_offset_aware().isoformat(),
            True,
            reverse('cluster-account-deletion-request-detail',
                    kwargs={'pk': pk})
        ])

        return checklist

    def post(self, request, *args, **kwargs):
        """Approve the request."""
        # if not self.request.user.is_superuser:
        #     message = 'You do not have permission to access this page.'
        #     messages.error(request, message)
        #     pk = self.request_obj.pk
        #
        #     return HttpResponseRedirect(
        #         reverse('secure-dir-request-detail', kwargs={'pk': pk}))
        #
        # if not self.is_checklist_complete():
        #     message = 'Please complete the checklist before final activation.'
        #     messages.error(request, message)
        #     pk = self.request_obj.pk
        #     return HttpResponseRedirect(
        #         reverse('secure-dir-request-detail', kwargs={'pk': pk}))
        #
        # # Check that the project does not have any Secure Directories yet.
        # sec_dir_allocations = get_secure_dir_allocations()
        # if sec_dir_allocations.filter(
        #         project=self.request_obj.project).exists():
        #     message = f'The project {self.request_obj.project.name} already ' \
        #               f'has a secure directory associated with it.'
        #     messages.error(self.request, message)
        #     pk = self.request_obj.pk
        #     return HttpResponseRedirect(
        #         reverse('secure-dir-request-detail', kwargs={'pk': pk}))
        #
        # # Approve the request and send emails to the PI and requester.
        # runner = SecureDirRequestApprovalRunner(self.request_obj)
        # runner.run()
        #
        # success_messages, error_messages = runner.get_messages()
        #
        # for message in success_messages:
        #     messages.success(self.request, message)
        # for message in error_messages:
        #     messages.error(self.request, message)
        return HttpResponseRedirect('home')
        return HttpResponseRedirect(self.redirect)

    # def get_setup_status(self):
    #     """Return one of the following statuses for the 'setup' step of
    #     the request: 'N/A', 'Pending', 'Completed'."""
    #     state = self.request_obj.state
    #     if (state['rdm_consultation']['status'] == 'Denied' or
    #             state['mou']['status'] == 'Denied'):
    #         return 'N/A'
    #     return state['setup']['status']

    # def is_checklist_complete(self):
    #     status_choice = secure_dir_request_state_status(self.request_obj)
    #     return (status_choice.name == 'Approved - Processing' and
    #             self.request_obj.state['setup']['status'] == 'Completed')
