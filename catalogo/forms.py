from django import forms
from .models import Supplier, SupplierProduct, ProductIdentifier

class CatalogUploadForm(forms.Form):
    supplier = forms.ModelChoiceField(queryset=Supplier.objects.all(), label="Proveedor")
    file = forms.FileField(label="Archivo del proveedor (.xlsx o .pdf)")  # ← antes decía solo .xlsx
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
class SupplierProductInlineForm(forms.ModelForm):
    """
    Reemplaza 'identifier_value' por un Select con opciones =
    los ProductIdentifier del producto que se está editando.
    Si no hay identificadores, deja TextInput normal.
    """
    identifier_value = forms.CharField(label="Identifier", required=True)

    class Meta:
        model = SupplierProduct
        fields = ["supplier", "identifier_value", "price", "stock"]

    def __init__(self, *args, **kwargs):
        # 'product_instance' la inyectaremos desde el admin
        product_instance = kwargs.pop("product_instance", None)
        super().__init__(*args, **kwargs)

        # Proveedor: dropdown normal
        self.fields["supplier"].label = "Proveedor"

        # Si tenemos el producto, armamos choices con sus identificadores
        if product_instance is not None:
            ids_qs = ProductIdentifier.objects.filter(product=product_instance).values_list("value", flat=True)
            id_values = list(ids_qs)
            if id_values:
                self.fields["identifier_value"] = forms.ChoiceField(
                    label="Identifier",
                    choices=[("", "— elegir —")] + [(v, v) for v in id_values],
                    required=True,
                )