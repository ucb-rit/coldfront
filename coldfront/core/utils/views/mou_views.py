from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic.edit import FormView
from django.views import View
from coldfront.core.allocation.models import AllocationAdditionRequest, SecureDirRequest
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.utils.forms.file_upload_forms import PDFUploadForm
from coldfront.core.utils.mou import get_context

from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.http import HttpResponse

import datetime
import os
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (NameObject, NumberObject,
                          BooleanObject, IndirectObject)
from io import BytesIO

class MOUUploadView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = 'upload_mou.html'
    form_class = PDFUploadForm

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
            self.request_class, pk=pk)

    def form_valid(self, form):
        '''set request's MOU to the uploaded file'''
        self.request_obj.mou_file = form.cleaned_data['file']
        self.request_obj.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['request_obj'] = self.request_obj
        context['mou_type'] = self.mou_type
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
            self.request_class, pk=pk)
    
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

class UnsignedMOUDownloadView(LoginRequiredMixin, UserPassesTestMixin, View):
    
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
            self.request_class, pk=pk)
    
    def get(self, request, *args, **kwargs):
        context = get_context(self.request_obj)
        
        reader = PdfReader('mou_template.pdf', strict=False)
        # if "/AcroForm" in reader.trailer["/Root"]:
        #     reader.trailer["/Root"]["/AcroForm"].update(
        #         {NameObject("/NeedAppearances"): BooleanObject(True)}
        #     )
        writer = PdfWriter()
        # set_need_appearances_writer(writer)
        # if "/AcroForm" in writer._root_object:
        #     writer._root_object["/AcroForm"].update(
        #         {NameObject("/NeedAppearances"): BooleanObject(True)}
        #     )

        writer.add_page(reader.pages[0])
        page = writer.pages[0]
        writer.update_page_form_field_values(
           page, context
        )

        # setting form fields to read-only and multiline and no spell check
        for i in range(len(page['/Annots'])):
            writer_annot = page['/Annots'][i].get_object()
            for field in context:
                if writer_annot.get('/T') == field:
                    writer_annot.update({
                        NameObject("/Ff"): NumberObject(1+(1<<12)+(1<<22)),
                    })

        output_stream = BytesIO()
        writer.write(output_stream)
        response = HttpResponse(output_stream.getvalue(),
                                content_type='application/pdf')
        response['Content-Disposition'] = 'attachment;filename="mou.pdf"'
        return response

    def get_success_url(self, **kwargs):
        ret = {'new-project': 'new-project-request-detail',
               'secure-dir': 'secure-dir-request-detail',
               'service-units': 'service-units-purchase-request-detail'}[self.mou_type]
        return reverse(
            ret,
            kwargs={'pk': self.kwargs.get('pk')})

def set_need_appearances_writer(writer):
    # See 12.7.2 and 7.7.2 for more information:
    # http://www.adobe.com/content/dam/acom/en/devnet/acrobat/
    #     pdfs/PDF32000_2008.pdf
    try:
        catalog = writer._root_object
        # get the AcroForm tree and add "/NeedAppearances attribute
        if "/AcroForm" not in catalog:
            writer._root_object.update(
                {
                    NameObject("/AcroForm"): IndirectObject(
                        len(writer._objects), 0, writer
                    )
                }
            )

        need_appearances = NameObject("/NeedAppearances")
        writer._root_object["/AcroForm"][need_appearances] = BooleanObject(True)
        return writer

    except Exception as e:
        print("set_need_appearances_writer() catch : ", repr(e))
        return writer