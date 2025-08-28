from typing import Optional
from catalogo.models import Product
from django.db.models import Q

def find_existing_product(gtin:str="", mpn:str="", name:str="", socket:str="")->Optional[Product]:
    gtin=(gtin or "").strip(); mpn=(mpn or "").strip(); name=(name or "").strip(); socket=(socket or "").strip().upper()
    if gtin:
        p=Product.objects.filter(gtin__iexact=gtin).first()
        if p: return p
    if mpn:
        p=Product.objects.filter(mpn__iexact=mpn).first()
        if p: return p
    if name:
        q=Product.objects.all()
        tokens=[t for t in name.replace("/"," ").split() if len(t)>2]
        for t in tokens[:4]: q=q.filter(name__icontains=t)
        if socket: q=q.filter(Q(socket__iexact=socket)|Q(description__icontains=socket))
        return q.first()
    return None
