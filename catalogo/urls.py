from django.urls import path
from . import views

urlpatterns = [
    path("productos/", views.product_list, name="product_list"),
    path("productos/<slug:slug>/", views.product_detail, name="product_detail"),
    path("catalogo/importar/", views.importar, name="importar_catalogo"),
]
