from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import FormView
from django.shortcuts import render
from django.urls import reverse

from coldfront.core.department.models import UserDepartment
from coldfront.core.department.forms import DepartmentSelectionForm
from coldfront.core.utils.common import import_from_settings

# Create your views here.

class UpdateDepartmentsView(LoginRequiredMixin, FormView):

    form_class = DepartmentSelectionForm
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
        UserDepartment.objects.filter(userprofile=userprofile,
                                      is_authoritative=False) \
                              .exclude(department__in=new_departments).delete()
        
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, viewed_username=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['department_display_name'] = \
                                import_from_settings('DEPARTMENT_DISPLAY_NAME')
        return context

    def get_success_url(self):
        return reverse('user-profile')
