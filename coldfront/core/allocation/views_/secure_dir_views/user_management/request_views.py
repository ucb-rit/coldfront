import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.db.models import Q
from django.forms import formset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.urls import reverse
from django.views.generic.base import TemplateView

from coldfront.core.allocation.forms_.secure_dir_forms import SecureDirManageUsersForm
from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import SecureDirAddUserRequest
from coldfront.core.allocation.models import SecureDirRemoveUserRequest
from coldfront.core.allocation.utils import has_cluster_access
from coldfront.core.allocation.utils_.secure_dir_utils.user_management import can_manage_secure_directory
from coldfront.core.allocation.utils_.secure_dir_utils.user_management import get_secure_dir_manage_user_request_objects

from coldfront.core.project.models import ProjectUser

from coldfront.core.utils.mail import send_email_template


logger = logging.getLogger(__name__)


class SecureDirManageUsersView(LoginRequiredMixin,
                               UserPassesTestMixin,
                               TemplateView):
    template_name = 'secure_dir/secure_dir_manage_users.html'

    def test_func(self):
        """Allow users with permissions to manage the directory to
        manage users."""
        alloc_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        return can_manage_secure_directory(alloc_obj, self.request.user)

    def dispatch(self, request, *args, **kwargs):
        alloc_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        get_secure_dir_manage_user_request_objects(self,
                                                   self.kwargs.get('action'))
        self.directory = \
            alloc_obj.allocationattribute_set.get(
                allocation_attribute_type__name='Cluster Directory Access').value

        if alloc_obj.status.name not in ['Active', 'New', ]:
            messages.error(
                request, f'You can only {self.language_dict["verb"]} users '
                         f'{self.language_dict["preposition"]} an '
                         f'active allocation.')
            return HttpResponseRedirect(
                reverse('allocation-detail', kwargs={'pk': alloc_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_users_to_add(self, alloc_obj):
        # Users in any projects that the PI runs should be available to add.
        alloc_pis = [proj_user.user for proj_user in
                     alloc_obj.project.projectuser_set.filter(
                         Q(role__name__in=['Manager',
                                           'Principal Investigator']) &
                         Q(status__name='Active'))]

        projects = [proj_user.project for proj_user in
                    ProjectUser.objects.filter(
                        Q(role__name__in=['Manager',
                                          'Principal Investigator']) &
                        Q(status__name='Active') &
                        Q(user__in=alloc_pis))]

        # Users must have active cluster access to be added.
        users_to_add = set([proj_user.user for proj_user in
                            ProjectUser.objects.filter(project__in=projects,
                                                       status__name='Active')
                            if has_cluster_access(proj_user.user)])

        # Excluding active users that are already part of the allocation.
        users_to_exclude = set(alloc_user.user for alloc_user in
                               alloc_obj.allocationuser_set.filter(
                                   status__name='Active'))

        # Excluding users that have active join requests.
        users_to_exclude |= \
            set(request.user for request in
                SecureDirAddUserRequest.objects.filter(
                    allocation=alloc_obj,
                    status__name__in=['Pending',
                                      'Processing']))

        # Excluding users that have active removal requests.
        users_to_exclude |= \
            set(request.user for request in
                SecureDirRemoveUserRequest.objects.filter(
                    allocation=alloc_obj,
                    status__name__in=['Pending',
                                      'Processing']))

        users_to_add -= users_to_exclude

        user_data_list = []
        for user in users_to_add:
            user_data = {
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email
            }
            user_data_list.append(user_data)

        return user_data_list

    def get_users_to_remove(self, alloc_obj):
        users_to_remove = set(alloc_user.user for alloc_user in
                              alloc_obj.allocationuser_set.filter(
                                  status__name='Active'))

        # Exclude users that have active removal requests.
        users_to_remove -= set(request.user for request in
                               SecureDirRemoveUserRequest.objects.filter(
                                   allocation=alloc_obj,
                                   status__name__in=['Pending',
                                                     'Processing']))

        # PIs cannot request to remove themselves from their
        # own secure directories.
        users_to_remove -= set(proj_user.user for proj_user in
                               alloc_obj.project.projectuser_set.filter(
                                   role__name='Principal Investigator',
                                   status__name='Active'))

        user_data_list = []
        for user in users_to_remove:
            user_data = {
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email
            }
            user_data_list.append(user_data)

        return user_data_list

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        alloc_obj = get_object_or_404(Allocation, pk=pk)

        if self.add_bool:
            user_list = self.get_users_to_add(alloc_obj)
        else:
            user_list = self.get_users_to_remove(alloc_obj)

        context = {}

        if user_list:
            formset = formset_factory(
                SecureDirManageUsersForm, max_num=len(user_list))
            formset = formset(initial=user_list, prefix='userform')
            context['formset'] = formset

        context['allocation'] = alloc_obj

        context['can_manage_users'] = False
        if self.request.user.is_superuser:
            context['can_manage_users'] = True

        if alloc_obj.project.projectuser_set.filter(
                user=self.request.user,
                role__name='Principal Investigator',
                status__name='Active').exists():
            context['can_manage_users'] = True

        context['directory'] = self.directory

        context['action'] = self.action
        context['url'] = f'secure-dir-manage-users'

        context['button'] = 'btn-success' if self.add_bool else 'btn-danger'

        context['preposition'] = self.language_dict['preposition']

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        alloc_obj = get_object_or_404(Allocation, pk=pk)

        allowed_to_manage_users = False
        if alloc_obj.project.projectuser_set.filter(
                user=self.request.user,
                role__name='Principal Investigator',
                status__name='Active').exists():
            allowed_to_manage_users = True

        if self.request.user.is_superuser:
            allowed_to_manage_users = True

        if not allowed_to_manage_users:
            message = 'You do not have permission to view the this page.'
            messages.error(request, message)

            return HttpResponseRedirect(
                reverse('allocation-detail', kwargs={'pk': pk}))

        if self.add_bool:
            user_list = self.get_users_to_add(alloc_obj)
        else:
            user_list = self.get_users_to_remove(alloc_obj)

        formset = formset_factory(
            SecureDirManageUsersForm, max_num=len(user_list))
        formset = formset(
            request.POST, initial=user_list, prefix='userform')

        reviewed_users_count = 0
        if formset.is_valid():
            pending_status = \
                self.request_status_obj.objects.get(name__icontains='Pending')

            for form in formset:
                user_form_data = form.cleaned_data
                if user_form_data['selected']:
                    reviewed_users_count += 1
                    user_obj = User.objects.get(
                        username=user_form_data.get('username'))

                    # Create the request object
                    self.request_obj.objects.create(
                        user=user_obj,
                        allocation=alloc_obj,
                        status=pending_status,
                        directory=self.directory
                    )

            # Email admins that there are new request(s)
            if settings.EMAIL_ENABLED:
                context = {
                    'noun': self.language_dict['noun'],
                    'verb': 'are' if reviewed_users_count > 1 else 'is',
                    'plural': 's' if reviewed_users_count > 1 else '',
                    'determiner': 'these' if reviewed_users_count > 1 else 'this',
                    'num_requests': reviewed_users_count,
                    'project_name': alloc_obj.project.name,
                    'directory_name': self.directory,
                    'review_url': 'secure-dir-manage-users-request-list',
                    'action': self.action
                }

                try:
                    subject = f'Pending Secure Directory '\
                              f'{self.language_dict["noun"]} Requests'
                    plain_template = 'email/secure_dir_request/'\
                                     'pending_secure_dir_manage_' \
                                     'user_requests.txt'
                    html_template = 'email/secure_dir_request/' \
                                    'pending_secure_dir_manage_' \
                                    'user_requests.html'
                    send_email_template(subject,
                                        plain_template,
                                        context,
                                        settings.EMAIL_SENDER,
                                        settings.EMAIL_ADMIN_LIST,
                                        html_template=html_template)

                except Exception as e:
                    message = f'Failed to send notification email.'
                    messages.error(request, message)
                    logger.error(message)
                    logger.exception(e)

            message = (
                f'Successfully requested to {self.action} '
                f'{reviewed_users_count} user'
                f'{"s" if reviewed_users_count > 1 else ""} '
                f'{self.language_dict["preposition"]} the secure directory '
                f'{self.directory}. {settings.PROGRAM_NAME_SHORT} staff have '
                f'been notified.')
            messages.success(request, message)

        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(
            reverse('allocation-detail', kwargs={'pk': pk}))
