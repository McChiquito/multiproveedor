from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator

class Supplier(models.Model):
    name = models.CharField("Nombre", max_length=120, unique=True)
    slug = models.SlugField("Identificador", max_length=140, unique=True, blank=True)
    config = models.JSONField("Configuración", default=dict, blank=True)

    def save(self, *a, **k):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*a, **k)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"


class Product(models.Model):
    name = models.CharField("Nombre", max_length=255)
    slug = models.SlugField("Identificador", max_length=280, unique=True, blank=True)
    brand = models.CharField("Marca", max_length=120, blank=True)
    mpn = models.CharField("Número de parte (MPN)", max_length=120, blank=True, db_index=True)
    gtin = models.CharField("Código GTIN/UPC/EAN", max_length=20, blank=True, db_index=True)
    socket = models.CharField("Socket", max_length=80, blank=True)
    short_description = models.CharField("Descripción corta", max_length=280, blank=True)
    description = models.TextField("Descripción", blank=True)
    created_at = models.DateTimeField("Creado en", auto_now_add=True)
    updated_at = models.DateTimeField("Actualizado en", auto_now=True)

    def save(self, *a, **k):
        if not self.slug:
            base = self.mpn or self.gtin or self.name
            self.slug = slugify(f"{self.brand} {base}")[:280]
        super().save(*a, **k)

    def __str__(self):
        return f"{self.brand} {self.name}".strip()

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"


class SupplierProduct(models.Model):
    supplier = models.ForeignKey(Supplier, verbose_name="Proveedor", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, verbose_name="Producto", on_delete=models.CASCADE, related_name="supplier_links")
    supplier_sku = models.CharField("SKU del proveedor", max_length=120, db_index=True, blank=True)
    mpn = models.CharField("Número de parte (MPN)", max_length=120, blank=True, db_index=True)
    gtin = models.CharField("GTIN/UPC/EAN", max_length=20, blank=True, db_index=True)
    name_in_feed = models.CharField("Nombre en catálogo", max_length=255, blank=True)
    price = models.DecimalField("Precio", max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    currency = models.CharField("Moneda", max_length=10, default="MXN")
    stock = models.IntegerField("Existencias", default=0)
    availability = models.CharField("Disponibilidad", max_length=60, blank=True)
    updated_at = models.DateTimeField("Actualizado en", auto_now=True)

    class Meta:
        unique_together = (
            ("supplier", "supplier_sku"),
            ("supplier", "mpn"),
            ("supplier", "gtin"),
        )
        verbose_name = "Producto de proveedor"
        verbose_name_plural = "Productos de proveedores"

    def __str__(self):
        return f"{self.supplier.name} → {self.product}"


class ImportJob(models.Model):
    supplier = models.ForeignKey(Supplier, verbose_name="Proveedor", on_delete=models.CASCADE)
    filename = models.CharField("Nombre de archivo", max_length=255)
    started_at = models.DateTimeField("Iniciado en", auto_now_add=True)
    finished_at = models.DateTimeField("Finalizado en", null=True, blank=True)
    processed_rows = models.IntegerField("Filas procesadas", default=0)
    created_links = models.IntegerField("Vínculos creados", default=0)
    updated_links = models.IntegerField("Vínculos actualizados", default=0)
    created_products = models.IntegerField("Productos nuevos", default=0)

    def __str__(self):
        return f"Importación {self.supplier.name} ({self.filename})"

    class Meta:
        verbose_name = "Importación de catálogo"
        verbose_name_plural = "Importaciones de catálogos"
