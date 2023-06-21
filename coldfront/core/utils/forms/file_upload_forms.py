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
