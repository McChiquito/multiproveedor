from django.contrib import admin
from .models import Supplier, Product, ProductIdentifier, SupplierProduct
from .forms import SupplierProductInlineForm

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "website")
    search_fields = ("name",)

class ProductIdentifierInline(admin.TabularInline):
    model = ProductIdentifier
    extra = 1

class SupplierProductInline(admin.TabularInline):
    model = SupplierProduct
    form = SupplierProductInlineForm
    extra = 1
    autocomplete_fields = ("supplier",)  # opcional, si tu admin usa autocomplete

    # Pasamos el producto actual al form para construir choices
    def get_formset(self, request, obj=None, **kwargs):
        FormSet = super().get_formset(request, obj, **kwargs)
        product_instance = obj  # el Product que se está editando

        # Cerramos sobre el Form original para inyectar el product_instance
        original_init = FormSet.form.__init__

        def form_init(form_self, *args, **kw):
            kw.setdefault("product_instance", product_instance)
            return original_init(form_self, *args, **kw)

        FormSet.form.__init__ = form_init
        return FormSet

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "base_sku")
    search_fields = ("name", "base_sku", "identifiers__value")
    inlines = [ProductIdentifierInline, SupplierProductInline]

@admin.register(SupplierProduct)
class SupplierProductAdmin(admin.ModelAdmin):
    list_display = ("supplier", "product", "identifier_value", "price", "stock", "last_seen")
    search_fields = ("product__name", "identifier_value")
    list_filter = ("supplier",)
