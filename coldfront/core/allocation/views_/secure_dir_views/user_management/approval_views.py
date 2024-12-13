import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.paginator import EmptyPage
from django.core.paginator import PageNotAnInteger
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import FormView
from django.views.generic import ListView
from django.views.generic.base import View

from coldfront.core.allocation.forms_.secure_dir_forms import SecureDirManageUsersRequestCompletionForm
from coldfront.core.allocation.forms_.secure_dir_forms import SecureDirManageUsersRequestUpdateStatusForm
from coldfront.core.allocation.forms_.secure_dir_forms import SecureDirManageUsersSearchForm
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.models import AllocationUserStatusChoice
from coldfront.core.allocation.utils_.secure_dir_utils.user_management import get_secure_dir_manage_user_request_objects

from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.mail import send_email_template


logger = logging.getLogger(__name__)


class SecureDirManageUsersRequestListView(LoginRequiredMixin,
                                          UserPassesTestMixin,
                                          ListView):
    template_name = 'secure_dir/secure_dir_manage_user_request_list.html'
    paginate_by = 30

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm(
                'allocation.view_securediradduserrequest') and \
                self.request.user.has_perm(
                    'allocation.view_securedirremoveuserrequest'):
            return True

        message = (
            f'You do not have permission to review secure directory '
            f'{self.action} user requests.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        get_secure_dir_manage_user_request_objects(self,
                                                   self.kwargs.get('action'))
        self.status = self.kwargs.get('status')
        self.completed = self.status == 'completed'
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            if direction == 'asc':
                direction = ''
            else:
                direction = '-'
            order_by = direction + order_by
        else:
            order_by = '-modified'

        pending_status = self.request_status_obj.objects.filter(
            Q(name__icontains='Pending') | Q(name__icontains='Processing'))

        complete_status = self.request_status_obj.objects.filter(
            name__in=['Complete', 'Denied'])

        secure_dir_request_search_form = \
            SecureDirManageUsersSearchForm(self.request.GET)

        if self.completed:
            request_list = self.request_obj.objects.filter(
                status__in=complete_status)
        else:
            request_list = self.request_obj.objects.filter(
                status__in=pending_status)

        if secure_dir_request_search_form.is_valid():
            data = secure_dir_request_search_form.cleaned_data

            if data.get('username'):
                request_list = request_list.filter(
                    user__username__icontains=data.get('username'))

            if data.get('email'):
                request_list = request_list.filter(
                    user__email__icontains=data.get('email'))

            if data.get('project_name'):
                request_list = \
                    request_list.filter(
                        allocation__project__name__icontains=data.get(
                            'project_name'))

            if data.get('directory_name'):
                request_list = \
                    request_list.filter(
                        directory__icontains=data.get(
                            'directory_name'))

        return request_list.order_by(order_by)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        secure_dir_request_search_form = \
            SecureDirManageUsersSearchForm(self.request.GET)
        if secure_dir_request_search_form.is_valid():
            data = secure_dir_request_search_form.cleaned_data
            filter_parameters = ''
            for key, value in data.items():
                if value:
                    if isinstance(value, list):
                        for ele in value:
                            filter_parameters += '{}={}&'.format(key, ele)
                    else:
                        filter_parameters += '{}={}&'.format(key, value)
            context['secure_dir_request_search_form'] = \
                secure_dir_request_search_form
        else:
            filter_parameters = None
            context['secure_dir_request_search_form'] = \
                SecureDirManageUsersSearchForm()

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
        else:
            context['expand_accordion'] = 'toggle'

        context['filter_parameters'] = filter_parameters
        context['filter_parameters_with_order_by'] = \
            filter_parameters_with_order_by

        context['request_filter'] = (
            'completed' if self.completed else 'pending')

        request_list = self.get_queryset()
        paginator = Paginator(request_list, self.paginate_by)

        page = self.request.GET.get('page')

        try:
            request_list = paginator.page(page)
        except PageNotAnInteger:
            request_list = paginator.page(1)
        except EmptyPage:
            request_list = paginator.page(paginator.num_pages)

        context['request_list'] = request_list

        context['actions_visible'] = not self.completed

        context['action'] = self.action

        context['preposition'] = self.language_dict['preposition']

        return context


class SecureDirManageUsersUpdateStatusView(LoginRequiredMixin,
                                           UserPassesTestMixin,
                                           FormView):
    form_class = SecureDirManageUsersRequestUpdateStatusForm
    template_name = \
        'secure_dir/secure_dir_manage_user_request_update_status.html'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm(
                'allocation.change_securediradduserrequest') or \
                self.request.user.has_perm(
                    'allocation.change_securedirremoveuserrequest'):
            return True

        message = (
            'You do not have permission to update secure directory '
            'join or removal requests.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        get_secure_dir_manage_user_request_objects(self,
                                                   self.kwargs.get('action'))
        self.secure_dir_request = get_object_or_404(
            self.request_obj, pk=self.kwargs.get('pk'))

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        cur_status = self.secure_dir_request.status.name
        if 'Pending' not in cur_status:
            message = f'Secure directory user {self.language_dict["noun"]} ' \
                      f'request has unexpected status "{cur_status}."'
            messages.error(self.request, message)
            return HttpResponseRedirect(
                reverse('secure-dir-manage-users-request-list',
                        kwargs={'action': self.action, 'status': 'pending'}))

        form_data = form.cleaned_data
        status = form_data.get('status')

        secure_dir_status_choice = \
            self.request_status_obj.objects.filter(
                name__icontains=status).first()
        self.secure_dir_request.status = secure_dir_status_choice
        self.secure_dir_request.save()

        message = (
            f'Secure directory {self.language_dict["noun"]} request for user '
            f'{self.secure_dir_request.user.username} for '
            f'{self.secure_dir_request.directory} has been '
            f'marked as "{status}".')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['request'] = self.secure_dir_request
        context['action'] = self.action
        context['noun'] = self.language_dict['noun']
        context['step'] = 'pending'
        return context

    def get_initial(self):
        initial = {
            'status': self.secure_dir_request.status.name,
        }
        return initial

    def get_success_url(self):
        return reverse('secure-dir-manage-users-request-list',
                       kwargs={'action': self.action, 'status': 'pending'})


class SecureDirManageUsersCompleteStatusView(LoginRequiredMixin,
                                             UserPassesTestMixin,
                                             FormView):
    form_class = SecureDirManageUsersRequestCompletionForm
    template_name = \
        'secure_dir/secure_dir_manage_user_request_update_status.html'

    # TODO: Much of the code in this and the denial view is duplicated.
    #  Some uncommitted utility classes are in the progress of being
    #  written to house the business logic and minimize duplication.

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm(
                'allocation.change_securediradduserrequest') or \
                self.request.user.has_perm(
                    'allocation.change_securedirremoveuserrequest'):
            return True

        message = (
            'You do not have permission to update secure directory '
            'join or removal requests.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        get_secure_dir_manage_user_request_objects(self,
                                                   self.kwargs.get('action'))
        self.secure_dir_request = get_object_or_404(
            self.request_obj, pk=self.kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        cur_status = self.secure_dir_request.status.name
        if 'Processing' not in cur_status:
            message = f'Secure directory user {self.language_dict["noun"]} ' \
                      f'request has unexpected status "{cur_status}."'
            messages.error(self.request, message)
            return HttpResponseRedirect(
                reverse(f'secure-dir-manage-users-request-list',
                        kwargs={'action': self.action, 'status': 'pending'}))

        form_data = form.cleaned_data
        status = form_data.get('status')
        complete = 'Complete' in status

        with transaction.atomic():
            secure_dir_status_choice = \
                self.request_status_obj.objects.filter(
                    name__icontains=status).first()
            self.secure_dir_request.status = secure_dir_status_choice
            if complete:
                self.secure_dir_request.completion_time = utc_now_offset_aware()
            self.secure_dir_request.save()

            if complete:
                if self.add_bool:
                    active_allocation_user_status = \
                        AllocationUserStatusChoice.objects.get(name='Active')
                else:
                    active_allocation_user_status = \
                        AllocationUserStatusChoice.objects.get(name='Removed')
                AllocationUser.objects.update_or_create(
                    allocation=self.secure_dir_request.allocation,
                    user=self.secure_dir_request.user,
                    defaults={'status': active_allocation_user_status})

            try:
                self._send_emails()
            except Exception as e:
                logger.exception(
                    f'Failed to send notification emails. Details:\n{e}')
                message = 'Failed to send notification emails to users.'
                messages.error(self.request, message)

        message = (
            f'Secure directory {self.language_dict["noun"]} request for user '
            f'{self.secure_dir_request.user.username} for '
            f'{self.secure_dir_request.directory} has been marked '
            f'as "{status}".')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['request'] = self.secure_dir_request
        context['action'] = self.action
        context['noun'] = self.language_dict['noun']
        context['step'] = 'processing'
        return context

    def get_initial(self):
        initial = {
            'status': self.secure_dir_request.status.name,
        }
        return initial

    def get_success_url(self):
        return reverse(f'secure-dir-manage-users-request-list',
                       kwargs={'action': self.action, 'status': 'pending'})

    def _send_emails(self):
        """Send notification emails to the user and relevant project
        administrators."""
        if not settings.EMAIL_ENABLED:
            return

        managed_user = self.secure_dir_request.user

        context = {
            'center_name': settings.CENTER_NAME,
            'managed_user_str': (
                f'{managed_user.first_name} {managed_user.last_name} '
                f'({managed_user.username})'),
            'verb': self.language_dict['verb'],
            'preposition': self.language_dict['preposition'],
            'directory': self.secure_dir_request.directory,
            'removed': 'now' if self.add_bool else 'no longer',
            'signature': settings.EMAIL_SIGNATURE,
            'support_email': settings.CENTER_HELP_EMAIL,
        }

        subject = (
            f'Secure Directory {self.language_dict["noun"].title()} Request '
            f'Complete')
        template_name = (
            'email/secure_dir_request/'
            'secure_dir_manage_user_request_complete.txt')
        sender = settings.EMAIL_SENDER
        receiver_list = [managed_user.email]

        # Include project administrators on the email.
        users_to_cc = set()
        allocation = self.secure_dir_request.allocation
        project = allocation.project
        pis = project.pis(active_only=True)
        users_to_cc.update(set(pis))
        managers = project.managers(active_only=True)
        active_allocation_user_status = \
            AllocationUserStatusChoice.objects.get(name='Active')
        for manager in managers:
            manager_in_directory = AllocationUser.objects.filter(
                allocation=allocation,
                user=manager,
                status=active_allocation_user_status).exists()
            if manager_in_directory:
                users_to_cc.add(manager)

        kwargs = {}
        if users_to_cc:
            kwargs['cc'] = [user.email for user in users_to_cc]

        send_email_template(
            subject, template_name, context, sender, receiver_list, **kwargs)


class SecureDirManageUsersDenyRequestView(LoginRequiredMixin,
                                          UserPassesTestMixin,
                                          View):

    # TODO: Much of the code in this and the complete view is
    #  duplicated. Some uncommitted utility classes are in the progress
    #  of being written to house the business logic and minimize
    #  duplication.

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        message = (
            'You do not have permission to deny a secure directory join or '
            'removal request.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        get_secure_dir_manage_user_request_objects(self,
                                                   self.kwargs.get('action'))
        self.secure_dir_request = get_object_or_404(
            self.request_obj, pk=self.kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        status = self.secure_dir_request.status.name
        if ('Processing' not in status) and ('Pending' not in status):
            message = f'Secure directory user {self.language_dict["noun"]} ' \
                      f'request has unexpected status "{status}."'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse(f'secure-dir-manage-users-request-list',
                        kwargs={'action': self.action, 'status': 'pending'}))

        reason = self.request.POST['reason']
        self.secure_dir_request.status = \
            self.request_status_obj.objects.get(name='Denied')
        self.secure_dir_request.completion_time = utc_now_offset_aware()
        self.secure_dir_request.save()

        message = (
            f'Secure directory {self.language_dict["noun"]} request for user '
            f'{self.secure_dir_request.user.username} for the secure directory '
            f'{self.secure_dir_request.directory} has been '
            f'denied.')
        messages.success(request, message)

        try:
            self._send_emails(reason)
        except Exception as e:
            logger.exception(
                f'Failed to send notification emails. Details:\n{e}')
            message = 'Failed to send notification emails to users.'
            messages.error(self.request, message)

        return HttpResponseRedirect(
            reverse(f'secure-dir-manage-users-request-list',
                    kwargs={'action': self.action, 'status': 'pending'}))

    def _send_emails(self, denial_reason):
        """Send notification emails to the user and relevant project
        administrators."""
        if not settings.EMAIL_ENABLED:
            return

        managed_user = self.secure_dir_request.user

        context = {
            'center_name': settings.CENTER_NAME,
            'managed_user_str': (
                f'{managed_user.first_name} {managed_user.last_name} '
                f'({managed_user.username})'),
            'verb': self.language_dict['verb'],
            'preposition': self.language_dict['preposition'],
            'directory': self.secure_dir_request.directory,
            'reason': denial_reason,
            'signature': settings.EMAIL_SIGNATURE,
            'support_email': settings.CENTER_HELP_EMAIL,
        }

        subject = (
            f'Secure Directory {self.language_dict["noun"].title()} Request '
            f'Denied')
        template_name = (
            'email/secure_dir_request/'
            'secure_dir_manage_user_request_denied.txt')
        sender = settings.EMAIL_SENDER
        receiver_list = [managed_user.email]

        # Include project administrators on the email.
        users_to_cc = set()
        allocation = self.secure_dir_request.allocation
        project = allocation.project
        pis = project.pis(active_only=True)
        users_to_cc.update(set(pis))
        managers = project.managers(active_only=True)
        active_allocation_user_status = \
            AllocationUserStatusChoice.objects.get(name='Active')
        for manager in managers:
            manager_in_directory = AllocationUser.objects.filter(
                allocation=allocation,
                user=manager,
                status=active_allocation_user_status).exists()
            if manager_in_directory:
                users_to_cc.add(manager)

        kwargs = {}
        if users_to_cc:
            kwargs['cc'] = [user.email for user in users_to_cc]

        send_email_template(
            subject, template_name, context, sender, receiver_list, **kwargs)
