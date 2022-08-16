from collections import defaultdict
from urllib.parse import urljoin

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.forms import formset_factory
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views.generic import DetailView
from django.views.generic.base import TemplateView, View
from django.views.generic.edit import FormView
from iso8601 import iso8601

from coldfront.config import settings
from coldfront.core.allocation.forms_.account_deletion_forms import \
    AccountDeletionRequestForm, AccountDeletionRequestSearchForm, \
    AccountDeletionEligibleUsersSearchForm, AccountDeletionProjectRemovalForm, \
    UpdateStatusForm, AccountDeletionCancelRequestForm
from coldfront.core.allocation.models import \
    (AccountDeletionRequest,
     AccountDeletionRequestStatusChoice,
     AccountDeletionRequestReasonChoice)
from coldfront.core.allocation.utils_.account_deletion_utils import \
    AccountDeletionRequestRunner, AccountDeletionRequestCompleteRunner, \
    send_account_deletion_cancellation_notification_emails

from coldfront.core.project.models import (ProjectUser)
from coldfront.core.project.utils_.removal_utils import \
    ProjectRemovalRequestRunner
from coldfront.core.utils.common import (import_from_settings,
                                         utc_now_offset_aware)

import logging

from coldfront.core.utils.email.email_strategy import SendEmailStrategy
from coldfront.core.utils.views import ListViewClass

EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED', False)

logger = logging.getLogger(__name__)


class AccountDeletionRequestMixin(object):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_obj = None

    @staticmethod
    def request_detail_url(pk):
        """Return the URL to the detail view for the request with the
        given primary key."""
        return reverse('cluster-account-deletion-request-detail',
                       kwargs={'pk': pk})

    def get_user_projects(self, user):
        user_projects = \
            ProjectUser.objects.filter(
                user=user).exclude(status__name='Denied').values_list(
                'project__name', flat=True)

        return ', '.join(user_projects)

    def set_request_obj(self, pk):
        """Set this instance's request_obj to be the
        AccountDeletionRequest with the given primary key."""
        self.request_obj = get_object_or_404(AccountDeletionRequest,
                                             pk=pk)

    def set_context_data(self, context):
        context['request_obj'] = self.request_obj
        context['user_str'] = f'{self.request_obj.user.first_name} ' \
                              f'{self.request_obj.user.last_name}'
        context['user_projects'] = self.get_user_projects(self.request_obj.user)


class AccountDeletionRequestFormView(LoginRequiredMixin,
                                     UserPassesTestMixin,
                                     AccountDeletionRequestMixin,
                                     FormView):
    form_class = AccountDeletionRequestForm
    template_name = \
        'account_deletion/request.html'

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        if self.request.user == self.user_obj:
            return True

        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        self.user_obj = get_object_or_404(User, pk=self.kwargs.get('pk'))

        if self.request.user.is_superuser:
            self.return_url = 'cluster-account-deletion-eligible-users'
        else:
            self.return_url = 'home'

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            if self.request.user == self.user_obj:
                reason = \
                    AccountDeletionRequestReasonChoice.objects.get(name='User')
            else:
                reason = \
                    AccountDeletionRequestReasonChoice.objects.get(name='Admin')

            runner = AccountDeletionRequestRunner(self.user_obj,
                                                  self.request.user,
                                                  reason)
            runner.run()
            for message in runner.get_warning_messages():
                messages.warning(self.request, message)

            request_obj = \
                AccountDeletionRequest.objects.get(user=self.user_obj)
            confirm_url = urljoin(settings.CENTER_BASE_URL,
                                  self.request_detail_url(request_obj.pk))

            if reason.name == 'User':
                message = f'You successfully requested to delete your ' \
                          f'cluster account. You may view details here ' \
                          f'<a href="{confirm_url}">here</a>.'
            else:
                message = f'You successfully requested to delete ' \
                          f'{self.user_obj.username}\'s cluster account. ' \
                          f'You may view details here ' \
                          f'<a href="{confirm_url}">here</a>.'
            messages.success(self.request, mark_safe(message))

            return HttpResponseRedirect(self.request_detail_url(request_obj.pk))

        except Exception as e:
            logger.exception(e)
            error_message = \
                'Unexpected error. Please contact an administrator.'
            messages.error(self.request, error_message)

        return HttpResponseRedirect(reverse(self.return_url))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_obj'] = self.user_obj
        context['user_str'] = f'{self.user_obj.first_name} ' \
                              f'{self.user_obj.last_name}'

        context['back_url'] = self.return_url

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['requester'] = self.request.user
        kwargs['user_obj'] = self.user_obj

        return kwargs


class AccountDeletionRequestEligibleUsersView(LoginRequiredMixin,
                                              UserPassesTestMixin,
                                              ListViewClass):
    template_name = \
        'account_deletion/eligible_users_list.html'
    paginate_by = 25
    context_object_name = 'eligible_users_to_delete'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def get_queryset(self):
        # TODO: ordery by
        proj_eligible_users_to_delete = ProjectUser.objects.filter(
            role__name='User').order_by('user__username')

        # Users with pending deletion requests cannot have a new request made.
        users_with_pending_deletion_requests = \
            AccountDeletionRequest.objects.filter(
                status__name__in=['Queued', 'Ready', 'Processing']). \
                values_list('user', flat=True)

        proj_eligible_users_to_delete = \
            proj_eligible_users_to_delete.exclude(
                user__in=users_with_pending_deletion_requests).exclude(
                user=self.request.user).order_by('user__username')

        search_form = AccountDeletionEligibleUsersSearchForm(
            self.request.GET)
        if search_form.is_valid():
            data = search_form.cleaned_data

            if data.get('username'):
                proj_eligible_users_to_delete = \
                    proj_eligible_users_to_delete.filter(
                        user__username__icontains=data.get('username'))

            if data.get('first_name'):
                proj_eligible_users_to_delete = \
                    proj_eligible_users_to_delete.filter(
                        user__first_name__icontains=data.get('first_name'))

            if data.get('last_name'):
                proj_eligible_users_to_delete = \
                    proj_eligible_users_to_delete.filter(
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

        # Filter on projects separately so that all projects are
        # still shown in table.
        project_filter = None
        if search_form.is_valid():
            project_filter = search_form.cleaned_data.get('project')

        # Making a user friendly string of the user's projects.
        for user, data in eligible_users_to_delete.copy().items():
            flag = False
            if project_filter:
                for project in data['projects']:
                    # Filter on user projects if a project filter was passed.
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
        kwargs.update({'search_form': AccountDeletionEligibleUsersSearchForm})
        context = super().get_context_data(**kwargs)
        return context


class AccountDeletionRequestListView(LoginRequiredMixin,
                                     UserPassesTestMixin,
                                     ListViewClass):
    model = AccountDeletionRequest
    template_name = \
        'account_deletion/request_list.html'
    context_object_name = 'account_deletion_requests'
    paginate_by = 25

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm(
                'allocation.view_accountdeletionrequest'):
            return True

        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def get_queryset(self):
        request_search_form = AccountDeletionRequestSearchForm(
            self.request.GET)
        if request_search_form.is_valid():
            # TODO: ordery by
            data = request_search_form.cleaned_data
            queryset = AccountDeletionRequest.objects.all()

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
                self.status = data.get('status')
                queryset = queryset.filter(status__name=data.get('status'))

            if data.get('reason'):
                queryset = queryset.filter(
                    reason__name=data.get('reason'))

        else:
            queryset = AccountDeletionRequest.objects.filter(
                status__name='Ready').order_by('created')
            self.status = 'Ready'

        return queryset

    def get_context_data(self, **kwargs):
        kwargs.update({'search_form': AccountDeletionRequestSearchForm})
        context = super().get_context_data(**kwargs)

        context['status'] = self.status

        context['actions_visible'] = self.request.user.is_superuser and \
                                     context['status'] not in ['Complete',
                                                               'Canceled']

        return context


class AccountDeletionRequestDetailView(LoginRequiredMixin,
                                       UserPassesTestMixin,
                                       AccountDeletionRequestMixin,
                                       DetailView):
    model = AccountDeletionRequest
    template_name = 'account_deletion/detail.html'
    login_url = '/'
    context_object_name = 'cluster_acct_deletion_request'

    logger = logging.getLogger(__name__)

    error_message = 'Unexpected failure. Please contact an administrator.'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm(
                'allocation.view_accountdeletionrequest'):
            return True

        if self.request.user == self.request_obj.user:
            return True

        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        self.set_request_obj(self.kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.set_context_data(context)

        try:
            latest_update_timestamp = \
                self.request_obj.latest_update_timestamp()
            if not latest_update_timestamp:
                latest_update_timestamp = 'No updates yet.'
            else:
                latest_update_timestamp = iso8601.parse_date(
                    latest_update_timestamp)
        except Exception as e:
            self.logger.exception(e)
            messages.error(self.request, self.error_message)
            latest_update_timestamp = 'Failed to determine timestamp.'
        context['latest_update_timestamp'] = latest_update_timestamp

        context['checklist'] = self.get_checklist()
        context['is_checklist_complete'] = self.is_checklist_complete()

        context['is_allowed_to_manage_request'] = \
            self.request.user.is_superuser

        context['user_is_allowed_to_cancel'] = \
            self.request.user == self.request_obj.user and \
            self.request_obj.status.name in ['Queued', 'Ready'] and \
            self.request_obj.reason.name == 'User'

        context['admin_is_allowed_to_cancel'] = \
            self.request.user.is_superuser and \
            self.request_obj.status.name in ['Queued', 'Ready']

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

        if self.request.user.is_superuser:
            project_removal = state['project_removal']
            checklist.append([
                'Confirm that the user has been removed from all projects.',
                project_removal['status'],
                project_removal['timestamp'],
                True,
                reverse(
                    'cluster-account-deletion-request-project-removal',
                    kwargs={'pk': pk})
            ])
            projects_removed = project_removal['status'] == 'Complete'

            data_deletion = state['data_deletion']
            checklist.append([
                'Confirm that the user\'s data has been deleted from '
                'the cluster.',
                data_deletion['status'],
                data_deletion['timestamp'],
                True,
                reverse(
                    'cluster-account-deletion-request-data-deletion',
                    kwargs={'pk': pk})
            ])
            data_deleted = data_deletion['status'] == 'Complete'

            account_deletion = state['account_deletion']
            checklist.append([
                'Confirm that the user\'s cluster account has been deleted.',
                state['account_deletion']['status'],
                account_deletion['timestamp'],
                projects_removed and data_deleted,
                reverse(
                    'cluster-account-deletion-request-account-deletion',
                    kwargs={'pk': pk})
            ])

        return checklist

    def post(self, request, *args, **kwargs):
        """Approve the request."""
        if not self.request.user.is_superuser:
            message = 'You do not have permission to access this page.'
            messages.error(request, message)
            pk = self.request_obj.pk

            return HttpResponseRedirect(self.request_detail_url(pk))

        if not self.is_checklist_complete():
            message = 'Please complete the checklist before final completion.'
            messages.error(request, message)
            pk = self.request_obj.pk

            return HttpResponseRedirect(self.request_detail_url(pk))

        # Complete the request and send the necessary emails.
        runner = AccountDeletionRequestCompleteRunner(self.request_obj)
        runner.run()

        for message in runner.get_warning_messages():
            messages.warning(self.request, message)

        message = f'Successfully completed account deletion request ' \
                  f'{self.request_obj} for user ' \
                  f'{self.request_obj.user.username}.'
        messages.success(self.request, message)

        return HttpResponseRedirect(
            reverse('cluster-account-deletion-request-list'))

    def is_checklist_complete(self):
        status_choice = self.request_obj.status.name
        return (status_choice == 'Processing' and
                self.request_obj.state['account_deletion'][
                    'status'] == 'Complete')


class AccountDeletionRequestRemoveProjectsView(LoginRequiredMixin,
                                               UserPassesTestMixin,
                                               AccountDeletionRequestMixin,
                                               TemplateView):
    template_name = (
        'account_deletion/project_removal.html')
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        self.set_request_obj(self.kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def get_projects(self, user_obj):
        # Get all projects that the user has been a part of.
        project_users = ProjectUser.objects.filter(user=user_obj). \
            exclude(status__name='Denied'). \
            order_by('status__name').order_by('project__name')

        project_list = []
        active_projects = 0
        for proj_user in project_users:
            pis = proj_user.project.pis().values_list('username', flat=True)
            data = {
                'project_name': proj_user.project.name,
                'role': proj_user.role.name,
                'status': proj_user.status.name,
                'pis': ', '.join(pis)
            }
            if data['status'] == 'Active':
                active_projects += 1
            project_list.append(data)

        return project_list, active_projects

    def get(self, request, *args, **kwargs):
        project_list, active_projects = self.get_projects(self.request_obj.user)

        context = {}

        if project_list:
            formset = formset_factory(
                AccountDeletionProjectRemovalForm, max_num=len(project_list))
            formset = formset(initial=project_list, prefix='projectform')

            for form in formset:
                if form['status'].value() in ['Removed', 'Pending - Remove']:
                    form.fields.pop('selected')

            context['formset'] = formset

        self.set_context_data(context)

        context['active_projects'] = active_projects

        # Show a button to complete this section after there are no more
        # projects to remove the user from.
        context['project_removal_complete'] = \
            not ProjectUser.objects.filter(
                user=self.request_obj.user,
                status__name__in=['Active',
                                  'Pending - Add',
                                  'Pending - Remove']).exists()

        context['project_removal_status'] = \
            self.request_obj.state['project_removal']['status']

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        project_list, _ = self.get_projects(self.request_obj.user)

        formset = formset_factory(
            AccountDeletionProjectRemovalForm, max_num=len(project_list))
        formset = formset(
            request.POST, initial=project_list, prefix='projectform')

        reviewed_projects_count = 0
        if formset.is_valid():
            for form in formset:
                form_data = form.cleaned_data
                if form_data['selected']:
                    reviewed_projects_count += 1

                    project_user = ProjectUser.objects.get(
                        user=self.request_obj.user,
                        project__name=form_data['project_name'],
                        role__name=form_data['role'],
                        status__name=form_data['status']
                    )

                    try:
                        request_runner = ProjectRemovalRequestRunner(
                            self.request.user,
                            self.request_obj.user,
                            project_user.project)
                        request_runner.run()
                        # Not sending project removal notification emails.

                    except Exception as e:
                        logger.exception(e)
                        error_message = \
                            'Unexpected error. Please contact an administrator.'
                        messages.error(self.request, error_message)

        message = f'Requested {reviewed_projects_count} project removals.'
        messages.success(self.request, message)

        return HttpResponseRedirect(
            reverse(
                'cluster-account-deletion-request-project-removal',
                kwargs={'pk': self.request_obj.pk}))


class AccountDeletionRequestRemoveProjectsConfirmView(LoginRequiredMixin,
                                                      UserPassesTestMixin,
                                                      AccountDeletionRequestMixin,
                                                      View):
    template_name = (
        'account_deletion/project_removal.html')
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        self.set_request_obj(self.kwargs.get('pk'))

        proj_users_exist = ProjectUser.objects.filter(
            user=self.request_obj.user) \
            .exclude(status__name__in=['Denied', 'Removed']).exists()

        if proj_users_exist:
            message = 'User has not been removed from all projects.'
            messages.error(self.request, message)

            return HttpResponseRedirect(
                reverse('cluster-account-deletion-request-project-removal',
                        kwargs={'pk': self.request_obj.pk}))

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.request_obj.state['project_removal'] = {
            'status': 'Complete',
            'timestamp': utc_now_offset_aware().isoformat(),
        }
        self.request_obj.status = \
            AccountDeletionRequestStatusChoice.objects.get(name='Processing')
        self.request_obj.save()

        message = (
            f'Project removal status for request {self.request_obj.pk} has '
            f'been set to Complete.')
        messages.success(self.request, message)

        return HttpResponseRedirect(
            self.request_detail_url(self.request_obj.pk))


class AccountDeletionRequestDataDeletionView(LoginRequiredMixin,
                                             UserPassesTestMixin,
                                             AccountDeletionRequestMixin,
                                             FormView):
    form_class = UpdateStatusForm
    template_name = 'account_deletion/data_deletion.html'
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        self.set_request_obj(self.kwargs.get('pk'))

        if self.request_obj.status.name not in ['Ready', 'Processing']:
            message = 'Request must be \"Ready\" or \"Processing\".'
            messages.error(self.request, message)
            return HttpResponseRedirect(
                self.request_detail_url(self.request_obj.pk))

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data['status']
        if status == 'Complete':
            self.request_obj.state['data_deletion'] = {
                'status': status,
                'timestamp': utc_now_offset_aware().isoformat(),
            }
            self.request_obj.status = \
                AccountDeletionRequestStatusChoice.objects.get(
                    name='Processing')
            self.request_obj.save()

        message = (
            f'Data deletion status for request {self.request_obj.pk} has been '
            f'set to {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.set_context_data(context)
        return context

    def get_initial(self):
        initial = super().get_initial()
        initial['status'] = self.request_obj.state['data_deletion']['status']
        return initial

    def get_success_url(self):
        return self.request_detail_url(self.kwargs.get('pk'))


class AccountDeletionRequestAccountDeletionView(LoginRequiredMixin,
                                                UserPassesTestMixin,
                                                AccountDeletionRequestMixin,
                                                FormView):
    form_class = UpdateStatusForm
    template_name = 'account_deletion/account_deletion.html'
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        self.set_request_obj(self.kwargs.get('pk'))

        request_ready = \
            self.request_obj.status.name == 'Processing' and \
            self.request_obj.state['data_deletion']['status'] == 'Complete' and \
            self.request_obj.state['project_removal']['status'] == 'Complete'

        if not request_ready:
            message = 'Request must be \"Processing\" and the Data Deletion ' \
                      'and Project Removal steps must be complete for the ' \
                      'Account Deletion step to be eligible for completion.'
            messages.error(self.request, message)
            return HttpResponseRedirect(
                self.request_detail_url(self.request_obj.pk))

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data['status']
        if status == 'Complete':
            self.request_obj.state['account_deletion'] = {
                'status': status,
                'timestamp': utc_now_offset_aware().isoformat(),
            }
            self.request_obj.status = \
                AccountDeletionRequestStatusChoice.objects.get(
                    name='Processing')
            self.request_obj.save()

        message = (
            f'Account deletion status for request {self.request_obj.pk} has '
            f'been set to {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.set_context_data(context)

        return context

    def get_initial(self):
        initial = super().get_initial()
        initial['status'] = self.request_obj.state['account_deletion']['status']
        return initial

    def get_success_url(self):
        return self.request_detail_url(self.kwargs.get('pk'))


class AccountDeletionRequestCancellationView(LoginRequiredMixin,
                                             UserPassesTestMixin,
                                             AccountDeletionRequestMixin,
                                             FormView):
    form_class = AccountDeletionCancelRequestForm
    template_name = 'account_deletion/request_cancellation.html'
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        if self.request.user == self.request_obj.user:
            return True

        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        self.set_request_obj(self.kwargs.get('pk'))

        if self.request_obj.status.name not in ['Queued', 'Ready']:
            message = 'Request must be \"Queued\" or \"Ready\" to be ' \
                      'eligible for cancellation.'
            messages.error(self.request, message)
            return HttpResponseRedirect(
                self.request_detail_url(self.request_obj.pk))

        if self.request_obj.user == self.request.user:
            if self.request_obj.reason.name != 'User':
                message = 'You can only cancel account deletion requests that ' \
                          'you initially requested.'
                messages.error(self.request, message)
                return HttpResponseRedirect(
                    self.request_detail_url(self.request_obj.pk))

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        justification = form_data['justification']
        self.request_obj.state['other'] = {
            'justification': justification,
            'timestamp': utc_now_offset_aware().isoformat(),
        }
        self.request_obj.status = \
            AccountDeletionRequestStatusChoice.objects.get(
                name='Cancelled')
        self.request_obj.save()

        message = (
            f'Account deletion request {self.request_obj.pk} has '
            f'been cancelled for the following reason: \"{justification}\".')
        messages.success(self.request, message)

        email_strategy = SendEmailStrategy()
        email_method = send_account_deletion_cancellation_notification_emails
        email_args = (self.request.user, self.request_obj)
        email_strategy.process_email(email_method, *email_args)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.set_context_data(context)

        return context

    def get_initial(self):
        initial = super().get_initial()
        initial['justification'] = self.request_obj.state['other'][
            'justification']
        return initial

    def get_success_url(self):
        return self.request_detail_url(self.kwargs.get('pk'))
