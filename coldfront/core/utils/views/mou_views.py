import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponse
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic.edit import UpdateView
from django.conf import settings
from coldfront.core.utils.common import utc_now_offset_aware

from flags.state import flag_enabled

from coldfront.core.allocation.models import AllocationAdditionRequest
from coldfront.core.allocation.models import SecureDirRequest
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.utils_.permissions_utils import is_user_manager_or_pi_of_project
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.utils.forms.file_upload_forms import model_pdf_upload_form_factory
from coldfront.core.utils.mou import get_mou_filename
from coldfront.core.utils.mail import send_email_template


logger = logging.getLogger(__name__)


class BaseMOUView(LoginRequiredMixin, UserPassesTestMixin):

    REQUEST_TYPES = \
        {'new-project': ('New Project Request',
                         SavioProjectAllocationRequest,
                         'Memorandum of Understanding',
                         'new-project-request-detail'),

         'secure-dir': ('Secure Directory Request',
                        SecureDirRequest,
                        'Researcher Use Agreement',
                        'secure-dir-request-detail'),

         'service-units-purchase': ('Service Units Purchase Request',
                                    AllocationAdditionRequest,
                                    'Memorandum of Understanding',
                                    'service-units-purchase-request-detail')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_type = None
        self.request_type_long = None
        self.request_obj = None

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True
        if self.request.user.has_perm('project.can_view_all_projects'):
            return True
        if self.request.user == self.request_obj.requester:
            return True
        if (self.request_type == 'service-units-purchase' and
                is_user_manager_or_pi_of_project(
                    self.request.user, self.request_obj.project)):
            return True
        if (self.request_type == 'secure-dir' and
                self.request.user in self.request_obj.project.pis()):
            return True
        if (self.request_type == 'new-project' and
                self.request.user == self.request_obj.pi):
            return True
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_attributes(pk)
        return super().dispatch(request, *args, **kwargs)

    def set_attributes(self, pk):
        """Set this instance's request_obj to be the
        SavioProjectAllocationRequest with the given primary key."""
        self.request_type = self.kwargs['request_type']

        self.request_type_long, self.request_class, self.mou_type = \
            self.REQUEST_TYPES[self.request_type][:3]

        self.request_obj = get_object_or_404(self.request_class, pk=pk)

    def get_success_url(self, **kwargs):
        ret = self.REQUEST_TYPES[self.request_type][3]
        return reverse(ret, kwargs={'pk': self.kwargs.get('pk')})


class MOUUploadView(BaseMOUView, UpdateView):
    template_name = 'upload_mou.html'
    context_object_name = 'object'

    def form_valid(self, form):
        form.save()

        file_name = form.cleaned_data['mou_file'].name

        message = f'Successfully uploaded file {file_name}.'
        messages.success(self.request, message)

        log_message = (
            f'User {self.request.user} uploaded signed MOU file {file_name} '
            f'for {self.request_class.__name__} {self.kwargs["pk"]}.')
        logger.info(log_message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['mou_type'] = self.mou_type
        context['request_type'] = self.request_type
        context['request_type_long'] = self.request_type_long
        context['return_url'] = self.get_success_url()
        return context

    def get_form_class(self):
        return model_pdf_upload_form_factory(self.request_class)

    def get_object(self, queryset=None):
        return self.request_class.objects.get(pk=self.kwargs['pk'])

    def get_queryset(self):
        return self.request_class.objects.all()


class MOUDownloadView(BaseMOUView, View):
    
    def get(self, request, *args, **kwargs):
        filename = get_mou_filename(self.request_obj)
        response = FileResponse(self.request_obj.mou_file)
        response['Content-Type'] = 'application/pdf'
        response['Content-Disposition'] = f'attachment;filename="{filename}"'
        return response


class UnsignedMOUDownloadView(BaseMOUView, View):

    def get(self, request, *args, **kwargs):
        request_type = ''
        mou_kwargs = {}
        if self.request_type == 'new-project' and ComputingAllowance(
                       self.request_obj.computing_allowance).is_instructional():
            request_type = 'instructional'
            mou_kwargs['service_units'] = int(float(self.request_obj \
                        .computing_allowance.get_attribute('Service Units')))
            mou_kwargs['extra_fields'] = self.request_obj.extra_fields
            allowance_end = self.request_obj.allocation_period.end_date
            mou_kwargs['allowance_end'] = allowance_end
        elif self.request_type == 'service-units-purchase' or \
                    (self.request_type == 'new-project' and ComputingAllowance(
                        self.request_obj.computing_allowance).is_recharge()):
            request_type = 'recharge'
            mou_kwargs['extra_fields'] = self.request_obj.extra_fields
            if self.request_type == 'service-units-purchase':
                mou_kwargs['service_units'] = int(self.request_obj.num_service_units)
            else:
                mou_kwargs['service_units'] = int(self.request_obj \
                                            .extra_fields['num_service_units'])
        elif self.request_type == 'secure-dir':
            request_type = 'secure-dir'
            mou_kwargs['department'] = self.request_obj.department
        
        if self.request_type == 'new-project':
            first_name = self.request_obj.pi.first_name
            last_name = self.request_obj.pi.last_name
        else:
            first_name = self.request_obj.requester.first_name
            last_name = self.request_obj.requester.last_name
        
        if flag_enabled('MOU_GENERATION_ENABLED'):
            from mou_generator import generate_pdf
            project_name = self.request_obj.project.name
            pdf = generate_pdf(
                request_type, first_name, last_name, project_name, **mou_kwargs)
        else:
            pdf = b''

        filename = get_mou_filename(self.request_obj)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

class MOURequestNotifyPIViewMixIn:
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['notify_pi'] = True
        return context
    
    def _email_pi(self, subject, to_name, mou_type, mou_for, email):
        """Send an email to the PI."""
        try:
            send_email_template(subject,
                                'request_mou_email.html',
                                {'to_name': to_name,
                                 'savio_request': self.request_obj,
                                 'mou_type': mou_type,
                                 'mou_for': mou_for,
                                 'base_url': settings.CENTER_BASE_URL,
                                 'signature': settings.EMAIL_SIGNATURE, },
                                settings.DEFAULT_FROM_EMAIL,
                                [email])
        except Exception as e:
            self.logger.error(
                f'Failed to send email to PI {email} for request '
                f'{self.request_obj.pk}: {e}')
            message = 'Failed to send email to PI.'
            messages.error(self.request, message)

    def form_valid(self, form):
        """Save the form."""
        #TODO
        #email_pi()
        self.email_pi()
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state['notified'] = {
            'status': 'Complete',
            'timestamp': timestamp,
        }
        self.request_obj.save()
        return super().form_valid(form)