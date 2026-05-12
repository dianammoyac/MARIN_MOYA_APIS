from django.urls import path
from . import views
from .views_admin import admin_dashboard, update_user_role

urlpatterns = [
    path("", views.login_view, name="login"),
    path("index2/", views.index2_view, name="index2"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),

    path("inmuebles/", views.inmuebles_listado, name="inmuebles_listado"),
    path("mis-inmuebles/", views.mis_inmuebles, name="mis_inmuebles"),
    path("inmuebles/crear/", views.inmuebles_crear, name="inmuebles_crear"),
    path("inmuebles/<int:pk>/", views.inmuebles_detalle, name="inmuebles_detalle"),
    path("inmuebles/<int:pk>/editar/", views.inmuebles_editar, name="inmuebles_editar"),
    path("inmuebles/<int:pk>/eliminar/", views.inmuebles_eliminar, name="inmuebles_eliminar"),
    path("admin-panel/", admin_dashboard, name="admin_dashboard"),
    path("admin-panel/update-role/<int:user_id>/", update_user_role, name="update_user_role"),
]