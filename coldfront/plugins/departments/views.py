from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import FormView
from django.urls import reverse

from allauth.account.models import EmailAddress

from coldfront.core.utils.common import import_from_settings

from coldfront.plugins.departments.models import UserDepartment
from coldfront.plugins.departments.forms import NonAuthoritativeDepartmentSelectionForm
from coldfront.plugins.departments.utils.data_sources import fetch_departments_for_user
from coldfront.plugins.departments.utils.queries import create_or_update_department


class UpdateDepartmentsView(LoginRequiredMixin, FormView):

    form_class = NonAuthoritativeDepartmentSelectionForm
    template_name = 'user_update_departments.html'
    login_url = '/'

    error_message = 'Unexpected failure. Please contact an administrator.'

    def form_valid(self, form):
        user = self.request.user
        form_data = form.cleaned_data
        new_departments = form_data['departments']
        userprofile = user.userprofile
        for department in new_departments:
            UserDepartment.objects.get_or_create(userprofile=userprofile,
                                            department=department,
                                            defaults={'is_authoritative':False})
        
        for ud in UserDepartment.objects.filter(userprofile=userprofile,
                                                is_authoritative=False):
            if ud.department not in new_departments:
                ud.delete()

        # TODO: This is duplicated. Make a function.
        user_data = {
            'emails': list(
                EmailAddress.objects.filter(user=user).values_list(
                    'email', flat=True)),
            'first_name': user.first_name,
            'last_name': user.last_name,
        }
        user_department_data = fetch_departments_for_user(user_data)

        for code, name in user_department_data:
            department, department_created = create_or_update_department(
                code, name)
            user_department, user_department_created = \
                UserDepartment.objects.update_or_create(
                    userprofile=user.userprofile,
                    department=department.pk,
                    defaults={
                        'is_authoritative': True,
                    })

        return super().form_valid(form)

    def get_context_data(self, viewed_username=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['department_display_name'] = \
                                import_from_settings('DEPARTMENT_DISPLAY_NAME')
        context['auth_department_list'] = \
            [f'{ud.department.name} ({ud.department.code})'
            for ud in UserDepartment.objects.select_related('department') \
            .filter(userprofile=self.request.user.userprofile,
                    is_authoritative=True) \
            .order_by('department__name')]
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse('user-profile')
