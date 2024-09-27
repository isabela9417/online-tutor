from django import forms

class DocumentUploadForm(forms.Form):
    document = forms.FileField()
