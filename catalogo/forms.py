from django import forms
from .models import Supplier

class UploadImportForm(forms.Form):
    supplier = forms.ModelChoiceField(queryset=Supplier.objects.all(), label="Proveedor")
    file = forms.FileField(label="Archivo Excel (.xlsx) o CSV (.csv)")
