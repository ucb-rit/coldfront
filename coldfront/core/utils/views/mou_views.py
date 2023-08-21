from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic.edit import FormView
from django.views import View
from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationAdditionRequest
from coldfront.core.allocation.models import SecureDirRequest
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.utils.forms.file_upload_forms import PDFUploadForm
from coldfront.core.utils.mou import get_mou_html

from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.http import HttpResponse

import coldfront_mou_gen

class BaseMOUView(LoginRequiredMixin, UserPassesTestMixin):

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True
        if self.request.user.has_perm('project.can_view_all_projects'):
            return True
        return True

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_attributes(pk)
        return super().dispatch(request, *args, **kwargs)

    def set_attributes(self, pk):
        """Set this instance's request_obj to be the
        SavioProjectAllocationRequest with the given primary key."""
        self.mou_type = self.kwargs['mou_type']
        self.mou_type_long, self.request_class = \
            {'new-project': ('New Project Request',
                             SavioProjectAllocationRequest),
             'secure-dir': ('Secure Directory Request',
                            SecureDirRequest),
             'service-units-purchase': ('Service Unit Purchase Request',
                              AllocationAdditionRequest)}[self.mou_type]
        self.request_obj = get_object_or_404(
            self.request_class, pk=pk)

    def get_success_url(self, **kwargs):
        ret = {'new-project': 'new-project-request-detail',
               'secure-dir': 'secure-dir-request-detail',
               'service-units-purchase': 'service-units-purchase-request-detail'}[self.mou_type]
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
        context['request_obj'] = self.request_obj
        context['mou_type'] = self.mou_type
        context['mou_type_long'] = self.mou_type_long
        return context

class MOUDownloadView(BaseMOUView, View):
    
    def get(self, request, *args, **kwargs):
        from django.http import FileResponse
        response = FileResponse(self.request_obj.mou_file)
        response['Content-Type'] = 'application/pdf'
        response['Content-Disposition'] = 'attachment;filename="mou.pdf"'
        return response

class UnsignedMOUDownloadView(BaseMOUView, View):
    
    def get(self, request, *args, **kwargs):
        mou_kwargs = {}
        if self.mou_type == 'new-project':
            mou_kwargs['service_units'] = int(float(self.request_obj \
                        .computing_allowance.get_attribute('Service Units')))
            mou_kwargs['extra_fields'] = self.request_obj.extra_fields
            allowance_end = self.request_obj.allocation_period.end_date
            mou_kwargs['allowance_end'] = allowance_end
            mou_kwargs['allowance_year'] = AllocationPeriod.objects.get(
                     name__startswith='Allowance Year',
                     start_date__lte=allowance_end,
                     end_date__gte=allowance_end).name
        elif self.mou_type == 'service-units-purchase':
            mou_kwargs['extra_fields'] = self.request_obj.extra_fields
            if isinstance(self.request_obj, AllocationAdditionRequest):
                mou_kwargs['service_units'] = int(self.request_obj.num_service_units)
            else:
                mou_kwargs['service_units'] = int(self.request_obj \
                                            .extra_fields['num_service_units'])
        elif self.mou_type == 'secure-dir':
            mou_kwargs['department'] = self.request_obj.department

        pdf = coldfront_mou_gen.generate_pdf(self.mou_type_long,
                                        self.request_obj.requester.first_name,
                                        self.request_obj.requester.last_name,
                                        self.request_obj.project.name,
                                        **mou_kwargs)
        response = HttpResponse(pdf,
                                content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="mou.pdf"'
        return response
