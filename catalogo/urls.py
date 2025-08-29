from django.urls import path
from . import views

app_name = "catalogo"

urlpatterns = [
    path("upload/", views.upload_catalog, name="upload"),
]
