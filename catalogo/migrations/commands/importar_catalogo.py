from django.core.management.base import BaseCommand, CommandError
from catalogo.models import Supplier
from catalogo.services.importers import import_for_supplier

class Command(BaseCommand):
    help = "Importa un Excel/CSV de un proveedor para actualizar precios e inventario (sin pandas)"

    def add_arguments(self, parser):
        parser.add_argument("supplier_slug", type=str)
        parser.add_argument("path", type=str)

    def handle(self, *args, **opts):
        slug=opts["supplier_slug"]; path=opts["path"]
        try:
            supplier=Supplier.objects.get(slug=slug)
        except Supplier.DoesNotExist:
            raise CommandError(f"No existe Supplier con slug={slug}")

        job = import_for_supplier(supplier, path)
        self.stdout.write(self.style.SUCCESS(
            f"Import terminado: filas={job.processed_rows}, nuevos={job.created_products}, vínculos creados={job.created_links}, actualizados={job.updated_links}"
        ))
