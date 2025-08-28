import os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .models import Product, SupplierProduct
from .forms import UploadImportForm
from .services.importers import import_for_supplier

def product_list(request):
    q = request.GET.get("q","")
    qs = Product.objects.all().order_by("brand","name")
    if q: qs = qs.filter(name__icontains=q)
    return render(request,"catalogo/product_list.html",{"products":qs,"q":q})

def product_detail(request, slug):
    p = get_object_or_404(Product, slug=slug)
    offers = SupplierProduct.objects.filter(product=p).select_related("supplier").order_by("price")
    return render(request,"catalogo/product_detail.html",{"product":p,"offers":offers})

@staff_member_required
def importar(request):
    if request.method == "POST":
        form = UploadImportForm(request.POST, request.FILES)
        if form.is_valid():
            supplier = form.cleaned_data["supplier"]
            f = form.cleaned_data["file"]
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(f.name)[1]) as tmp:
                for chunk in f.chunks(): tmp.write(chunk)
                tmp_path = tmp.name
            job = import_for_supplier(supplier, tmp_path)
            messages.success(request, f"Importado: filas={job.processed_rows}, nuevos={job.created_products}, vínculos +={job.created_links}/{job.updated_links}")
            return redirect("product_list")
    else:
        form = UploadImportForm()
    return render(request, "catalogo/importar.html", {"form": form})
