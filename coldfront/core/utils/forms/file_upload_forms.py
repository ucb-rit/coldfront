from django import forms
from django.core.validators import MinLengthValidator

class FileUploadForm(forms.Form):
    file = forms.FileField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file'].validators.append(MinLengthValidator(1))