from django import forms
from django.core.validators import (MinLengthValidator, 
                                    FileExtensionValidator)

def file_size_validator(file):
    limit = 20 * 1024 * 1024
    if file.size > limit:
        raise forms.ValidationError('File too large. Size should not exceed 20 MiB.')

class PDFUploadForm(forms.Form):
    file = forms.FileField(validators=[MinLengthValidator(1),
                                       FileExtensionValidator(['pdf']),
                                       file_size_validator])


# TODO: Call this in the view's get_form_class to avoid having to create
#  separate forms.
def model_pdf_upload_form_factory(_model):
    class ModelForm(forms.ModelForm):
        class Meta:
            model = _model
            fields = ['mou_file']

        mou_file = forms.FileField(validators=[MinLengthValidator(1),
                                       FileExtensionValidator(['pdf']),
                                       file_size_validator])

    return ModelForm


# TODO: Assuming the above doesn't work, create additional forms like this one
#  for the other models.
# TODO: Rename the form too.
from coldfront.core.project.models import SavioProjectAllocationRequest
class SModelForm(forms.ModelForm):
    class Meta:
        model = SavioProjectAllocationRequest
        fields = ['mou_file']

    mou_file = forms.FileField(validators=[MinLengthValidator(1),
                                   FileExtensionValidator(['pdf']),
                                   file_size_validator])
