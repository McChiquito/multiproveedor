from django.db import models
from django.utils import timezone

class Supplier(models.Model):
    name = models.CharField(max_length=120, unique=True)
    website = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    base_sku = models.CharField(max_length=64, blank=True, null=True, help_text="SKU interno opcional")
    description = models.TextField(blank=True)

    class Meta:
        unique_together = [("name", "base_sku")]

    def __str__(self):
        return self.name


class ProductIdentifier(models.Model):
    MPN = "MPN"
    UPC_EAN = "UPC_EAN"
    SKU_ALT = "SKU_ALT"

    TYPE_CHOICES = [
        (MPN, "MPN"),
        (UPC_EAN, "UPC/EAN"),
        (SKU_ALT, "SKU alterno"),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="identifiers")
    id_type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    value = models.CharField(max_length=64, db_index=True)

    class Meta:
        unique_together = [("id_type", "value")]

    def __str__(self):
        return f"{self.product.name} [{self.id_type}:{self.value}]"


class SupplierProduct(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="supplier_items")
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="items")
    identifier_value = models.CharField(max_length=64, help_text="Valor exacto encontrado en el catálogo del proveedor")
    price = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.IntegerField(default=0)
    last_seen = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("supplier", "identifier_value")]

    def __str__(self):
        return f"{self.supplier.name} → {self.product.name} (${self.price})"
