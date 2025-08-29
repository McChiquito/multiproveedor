from django import forms
from .models import Supplier

class CatalogUploadForm(forms.Form):
    supplier = forms.ModelChoiceField(queryset=Supplier.objects.all(), label="Proveedor")
    file = forms.FileField(label="Archivo Excel del proveedor (.xlsx)")
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
