import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.db import transaction
from django.forms import formset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic.base import TemplateView

from coldfront.core.allocation.forms_.secure_dir_forms import SecureDirManageUsersForm
from coldfront.core.allocation.models import Allocation

from coldfront.core.allocation.utils_.secure_dir_utils import SecureDirectory
from coldfront.core.allocation.utils_.secure_dir_utils.user_management import get_secure_dir_manage_user_request_objects
from coldfront.core.allocation.utils_.secure_dir_utils.user_management import SecureDirectoryManageUserRequestRunnerFactory

from coldfront.core.utils.email.email_strategy import EnqueueEmailStrategy


logger = logging.getLogger(__name__)


class SecureDirManageUsersView(LoginRequiredMixin, UserPassesTestMixin,
                               TemplateView):

    template_name = 'secure_dir/secure_dir_manage_users.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._allocation_obj = None
        self._secure_directory = None

        # These attributes are set by get_secure_dir_manage_user_request_objects
        # in the dispatch method. TODO: Use a mixin instead.
        self.action = None
        self.add_bool = None
        self.request_obj = None
        self.request_status_obj = None
        self.language_dict = None

    def test_func(self):
        """Allow users with permissions to manage the directory to
        manage users."""
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        secure_directory = SecureDirectory(allocation_obj)
        return secure_directory.user_can_manage(self.request.user)

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self._allocation_obj = get_object_or_404(Allocation, pk=pk)

        if self._allocation_obj.status.name != 'Active':
            message = 'You may only manage users under an active directory.'
            messages.error(request, message)
            return self._redirect_to_directory_allocation_detail()

        self._secure_directory = SecureDirectory(self._allocation_obj)

        # Set instance attributes based on the specified action.
        get_secure_dir_manage_user_request_objects(
            self, self.kwargs.get('action'))

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.add_bool:
            users = self._secure_directory.get_addable_users()
        else:
            users = self._secure_directory.get_removable_users()
        user_list = self._get_user_data(users)

        if user_list:
            formset = formset_factory(
                SecureDirManageUsersForm, max_num=len(user_list))
            formset = formset(initial=user_list, prefix='userform')
            context['formset'] = formset

        context['action'] = self.action
        context['preposition'] = self.language_dict['preposition']
        context['directory'] = self._secure_directory.get_path()
        context['manage_users_url'] = reverse(
            'secure-dir-manage-users',
            kwargs={'pk': self._allocation_obj.pk, 'action': self.action})
        context['allocation_url'] = reverse(
            'allocation-detail', kwargs={'pk': self._allocation_obj.pk})
        context['button_class'] = (
            'btn-success' if self.add_bool else 'btn-danger')

        return context

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        alloc_obj = get_object_or_404(Allocation, pk=pk)

        secure_directory = SecureDirectory(alloc_obj)
        if self.add_bool:
            user_list = secure_directory.get_addable_users()
        else:
            user_list = secure_directory.get_removable_users()

        formset = formset_factory(
            SecureDirManageUsersForm, max_num=len(user_list))
        formset = formset(
            request.POST, initial=user_list, prefix='userform')

        if formset.is_valid():
            try:
                selected_user_objs = self._get_selected_users(formset)
                self._process_users(secure_directory, selected_user_objs)
            except Exception as e:
                logger.exception(e)
                message = 'Unexpected failure. Please contact an administrator.'
                messages.error(request, message)
            else:
                num_users = len(formset)
                message = (
                    f'Successfully requested to {self.action} {num_users} '
                    f'user(s) {self.language_dict["preposition"]} the secure '
                    f'directory {secure_directory.get_path()}. Administrators '
                    f'have been notified, and will review and process the '
                    f'requests.')
                messages.success(request, message)
        else:
            for error in formset.errors:
                messages.error(request, error)

        return self._redirect_to_directory_allocation_detail()

    def _redirect_to_directory_allocation_detail(self):
        """Return a redirect to the detail view for the Allocation
        representing the secure directory."""
        url = reverse(
            'allocation-detail', kwargs={'pk': self._allocation_obj.pk})
        return HttpResponseRedirect(url)

    @staticmethod
    def _get_selected_users(formset):
        """Given a formset containing usernames that may have been
        selected, return the corresponding User objects of the ones that
        were."""
        user_objs = []
        for form in formset:
            user_form_data = form.cleaned_data
            if user_form_data.get('selected', False):
                user_obj = User.objects.get(
                    username=user_form_data.get('username'))
                user_objs.append(user_obj)
        return user_objs

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

    def _process_users(self, secure_directory, user_objs):
        """Given a list of User objects that were selected to be
        added/removed to/from the given SecureDirectory, process them in
        an atomic transaction.

        Only send emails if all succeeded.
        """
        email_strategy = EnqueueEmailStrategy()
        with transaction.atomic():
            for user_obj in user_objs:
                runner = \
                    SecureDirectoryManageUserRequestRunnerFactory.get_runner(
                        self.action, secure_directory, user_obj,
                        email_strategy=email_strategy)
                runner.run()
        email_strategy.send_queued_emails()
