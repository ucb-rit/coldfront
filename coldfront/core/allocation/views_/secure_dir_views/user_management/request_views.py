import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.forms import formset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic.base import TemplateView

from coldfront.core.allocation.forms_.secure_dir_forms import SecureDirManageUsersForm
from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.utils_.secure_dir_utils import SecureDirectory
from coldfront.core.allocation.utils_.secure_dir_utils.user_management import get_secure_dir_manage_user_request_objects


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
        secure_directory = SecureDirectory(alloc_obj)
        return secure_directory.user_can_manage(self.request.user)

    def dispatch(self, request, *args, **kwargs):
        # TODO: Store this so that get_context_data, post can use it without
        #  performing another lookup.
        alloc_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        get_secure_dir_manage_user_request_objects(self,
                                                   self.kwargs.get('action'))

        # TODO: This is accessible from the allocation, which is already stored
        #  in the SecureDirAddUserRequest and SecureDirRemoveUserRequest models.
        #  Why do this?
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        pk = self.kwargs.get('pk')
        alloc_obj = get_object_or_404(Allocation, pk=pk)

        secure_directory = SecureDirectory(alloc_obj)

        if self.add_bool:
            users = secure_directory.get_addable_users()
        else:
            users = secure_directory.get_removable_users()
        user_list = self._get_user_data(users)

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

        return context

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
            user_list = self._get_users_to_add(alloc_obj)
        else:
            user_list = self._get_users_to_remove(alloc_obj)

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

    @staticmethod
    def _get_user_data(users):
        """Given a queryset of Users, return a list of dicts containing
        data about each User."""
        user_data_list = []
        for user in users:
            user_data = {
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email
            }
            user_data_list.append(user_data)
        return user_data_list
