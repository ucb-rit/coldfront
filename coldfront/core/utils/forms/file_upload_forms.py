from django import forms
from django.core.validators import (MinLengthValidator, 
                                    MaxLengthValidator,
                                    FileExtensionValidator)

class PDFUploadForm(forms.Form):
    file = forms.FileField(validators=[MinLengthValidator(1),
                                       MaxLengthValidator(1024*1024*20), # 20 MB
                                       FileExtensionValidator(['pdf'])])
