from django.contrib import admin
from .models import Supplier, Product, SupplierProduct, ImportJob

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name","slug")
    search_fields = ("name",)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name","brand","mpn","gtin","socket")
    search_fields = ("name","brand","mpn","gtin")

@admin.register(SupplierProduct)
class SupplierProductAdmin(admin.ModelAdmin):
    list_display = ("supplier","product","supplier_sku","mpn","gtin","price","stock","updated_at")
    search_fields = ("supplier__name","supplier_sku","mpn","gtin","product__name")
    list_filter = ("supplier",)

@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):
    list_display = ("supplier","filename","started_at","finished_at","processed_rows")
    readonly_fields = ("started_at","finished_at")
