from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic.edit import FormView
from django.views import View
from coldfront.core.allocation.models import AllocationAdditionRequest, SecureDirRequest
from coldfront.core.utils.forms.file_upload_forms import FileUploadForm
from coldfront.core.project.models import SavioProjectAllocationRequest

from django.shortcuts import get_object_or_404
from django.urls import reverse

class MOUUploadView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = 'upload_mou.html'
    form_class = FileUploadForm

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
             'service-units': ('Service Unit Purchase Request',
                              AllocationAdditionRequest)}[self.mou_type]
        self.request_obj = get_object_or_404(
            self.request_class.objects, pk=pk)

    def form_valid(self, form):
        '''set request's MOU to the uploaded file'''
        self.request_obj.mou_file = form.cleaned_data['file']
        self.request_obj.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = {}
        context['form'] = FileUploadForm()
        context['request_obj'] = self.request_obj
        context['mou_type_long'] = self.mou_type_long
        return context
    
    def get_success_url(self, **kwargs):
        ret = {'new-project': 'new-project-request-detail',
               'secure-dir': 'secure-dir-request-detail',
               'service-units': 'service-units-purchase-request-detail'}[self.mou_type]
        return reverse(
            ret,
            kwargs={'pk': self.kwargs.get('pk')})

class MOUDownloadView(LoginRequiredMixin, UserPassesTestMixin, View):
    
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
        self.request_class = \
            {'new-project': SavioProjectAllocationRequest,
             'secure-dir': SecureDirRequest,
             'service-units': AllocationAdditionRequest}[self.mou_type]
        self.request_obj = get_object_or_404(
            self.request_class.objects, pk=pk)
    
    def get(self, request, *args, **kwargs):
        from django.http import FileResponse
        response = FileResponse(self.request_obj.mou_file)
        response['Content-Type'] = 'application/pdf'
        response['Content-Disposition'] = 'attachment;filename="mou.pdf"'
        return response

    def get_success_url(self, **kwargs):
        ret = {'new-project': 'new-project-request-detail',
               'secure-dir': 'secure-dir-request-detail',
               'service-units': 'service-units-purchase-request-detail'}[self.mou_type]
        return reverse(
            ret,
            kwargs={'pk': self.kwargs.get('pk')})