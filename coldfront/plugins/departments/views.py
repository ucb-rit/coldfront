import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import FormView
from django.urls import reverse

from coldfront.core.utils.common import import_from_settings

from coldfront.plugins.departments.forms import NonAuthoritativeDepartmentSelectionForm
from coldfront.plugins.departments.utils.queries import get_departments_for_user
from coldfront.plugins.departments.utils.queries import UserDepartmentUpdater


logger = logging.getLogger(__name__)


class UpdateDepartmentsView(LoginRequiredMixin, FormView):

    form_class = NonAuthoritativeDepartmentSelectionForm
    template_name = 'user_update_departments.html'
    login_url = '/'

    error_message = 'Unexpected failure. Please contact an administrator.'

    def form_valid(self, form):
        user = self.request.user
        non_authoritative_departments = form.cleaned_data['departments']

        # Update non-authoritative UserDepartments to those selected by the
        # user. Also fetch and set authoritative UserDepartments from the data
        # source.
        user_department_updater = UserDepartmentUpdater(
            user, non_authoritative_departments)
        user_department_updater.run(authoritative=True, non_authoritative=True)

        return super().form_valid(form)

    def get_context_data(self, viewed_username=None, **kwargs):
        context = super().get_context_data(**kwargs)

        context['department_display_name'] = import_from_settings(
            'DEPARTMENT_DISPLAY_NAME')

        # TODO: Account for viewed_username or not?

        authoritative_department_strs, _ = get_departments_for_user(
            self.request.user, strs_only=True)
        context['auth_department_list'] = authoritative_department_strs

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse('user-profile')
