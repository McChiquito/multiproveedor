from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect
from django.utils import timezone
from django.conf import settings

from .forms import CatalogUploadForm
from .models import Supplier, ProductIdentifier, SupplierProduct
from .utils.parsers import parse_catalog_auto


@login_required
@transaction.atomic
def upload_catalog(request):
    if request.method == "POST":
        form = CatalogUploadForm(request.POST, request.FILES)
        if form.is_valid():
            supplier: Supplier = form.cleaned_data["supplier"]

            # Archivo subido
            uploaded = request.FILES["file"]
            file_name = uploaded.name
            file_bytes = uploaded.read()

            # Tipo de cambio (configurable en settings.py)
            usd_mxn = float(getattr(settings, "USD_MXN_RATE", 18.5))

            # Router: XLSX para A/B, PDF para C (con conversión de moneda)
            rows = list(
                parse_catalog_auto(
                    supplier.name,
                    file_name,
                    file_bytes,
                    usd_mxn_rate=usd_mxn,
                )
            )

            updated, created, unmatched = 0, 0, []

            # Mapa de identificadores -> product_id
            id_map = {pi.value: pi.product_id for pi in ProductIdentifier.objects.all()}
            id_map_norm = {k.upper().replace(" ", ""): v for k, v in id_map.items()}

            for r in rows:
                ident = r["identifier_value"].strip()
                product_id = id_map.get(ident) or id_map_norm.get(ident.upper().replace(" ", ""))

                if not product_id:
                    unmatched.append(ident)
                    continue

                _, was_created = SupplierProduct.objects.update_or_create(
                    supplier=supplier,
                    identifier_value=ident,
                    defaults={
                        "product_id": product_id,
                        "price": r["price"],
                        "stock": r["stock"],
                        "last_seen": timezone.now(),
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

            messages.success(
                request,
                f"Catálogo procesado: {created} nuevos, {updated} actualizados, {len(unmatched)} sin coincidencia",
            )
            if unmatched:
                messages.warning(
                    request,
                    "Sin coincidencia para: "
                    + ", ".join(unmatched[:20])
                    + (" ..." if len(unmatched) > 20 else "")
                )

            return redirect("catalogo:upload")
    else:
        form = CatalogUploadForm()

    return render(request, "catalogo/upload.html", {"form": form})
