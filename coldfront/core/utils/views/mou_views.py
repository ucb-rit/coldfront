from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic.edit import FormView
from django.views import View
from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationAdditionRequest
from coldfront.core.allocation.models import SecureDirRequest
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.utils.forms.file_upload_forms import PDFUploadForm
from coldfront.core.utils.mou import get_mou_filename

from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.http import HttpResponse
from django.http import FileResponse

from flags.state import flag_enabled
import datetime

class BaseMOUView(LoginRequiredMixin, UserPassesTestMixin):
    
    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True
        if self.request.user.has_perm('project.can_view_all_projects'):
            return True
        if self.request.user == self.request_obj.pi or \
                                self.request.user == self.request_obj.requester:
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
            {'new-project': ('New Project Request',
                            SavioProjectAllocationRequest,
                            'Memorandum of Understanding'),
             'secure-dir': ('Secure Directory Request',
                            SecureDirRequest,
                            'Researcher Use Agreement'),
             'service-units-purchase': ('Service Units Purchase Request',
                            AllocationAdditionRequest,
                            'Memorandum of Understanding')}[self.request_type]
        self.request_obj = get_object_or_404(
            self.request_class, pk=pk)

    def get_success_url(self, **kwargs):
        ret = {'new-project': 'new-project-request-detail',
               'secure-dir': 'secure-dir-request-detail',
               'service-units-purchase': 'service-units-purchase-request-detail'}[self.request_type]
        return reverse(ret, kwargs={'pk': self.kwargs.get('pk')})

class MOUUploadView(BaseMOUView, FormView):
    template_name = 'upload_mou.html'
    form_class = PDFUploadForm

    def form_valid(self, form):
        """set request's MOU to the uploaded file"""
        self.request_obj.mou_file = form.cleaned_data['file']
        self.request_obj.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['mou_type'] = self.mou_type
        context['request_type'] = self.request_type
        context['request_type_long'] = self.request_type_long
        context['return_url'] = self.get_success_url()
        return context

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
            pdf = generate_pdf(request_type,
                               first_name,
                               last_name,
                               project_name,
                               **mou_kwargs)
        else:
            pdf = b''

        filename = get_mou_filename(self.request_obj)
        response = HttpResponse(pdf,
                                content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
