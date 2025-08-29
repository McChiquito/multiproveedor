from django.contrib import admin
from .models import Supplier, Product, ProductIdentifier, SupplierProduct

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "website")
    search_fields = ("name",)

class ProductIdentifierInline(admin.TabularInline):
    model = ProductIdentifier
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "base_sku")
    search_fields = ("name", "base_sku", "identifiers__value")
    inlines = [ProductIdentifierInline]

@admin.register(SupplierProduct)
class SupplierProductAdmin(admin.ModelAdmin):
    list_display = ("supplier", "product", "identifier_value", "price", "stock", "last_seen")
    search_fields = ("product__name", "identifier_value")
    list_filter = ("supplier",)
