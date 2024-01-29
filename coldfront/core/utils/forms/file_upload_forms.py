from django import forms
from django.core.validators import FileExtensionValidator
from django.core.validators import MinLengthValidator


def file_size_validator(file):
    limit_mebibytes = 20
    limit_bytes = limit_mebibytes * 1024 * 1024
    if file.size > limit_bytes:
        raise forms.ValidationError(
            f'File too large. Size should not exceed {limit_mebibytes} MiB.')


def model_pdf_upload_form_factory(model_class):
    """Return a form class that accepts an MOU file for the Django model
    of the given class."""

    class ModelPDFUploadForm(forms.ModelForm):
        class Meta:
            model = model_class
            fields = ['mou_file']

        mou_file = forms.FileField(
            label='File',
            validators=[
                MinLengthValidator(1),
                FileExtensionValidator(['pdf']),
                file_size_validator,
            ])

    return ModelPDFUploadForm
