from django.urls import path
from . import views

urlpatterns = [
    path("inmuebles/", views.inmuebles_listado, name="inmuebles_listado"),
    path("inmuebles/crear/", views.inmuebles_crear, name="inmuebles_crear"),
    path("inmuebles/<int:pk>/", views.inmuebles_detalle, name="inmuebles_detalle"),
]
