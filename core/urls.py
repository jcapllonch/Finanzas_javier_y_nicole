from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("movimientos/", views.movimientos_list, name="movimientos"),
    path("movimientos/nuevo/", views.movimiento_crear, name="movimiento_nuevo"),

    # NUEVAS
    path("movimientos/<int:pk>/editar/", views.movimiento_editar, name="movimiento_editar"),
    path("movimientos/<int:pk>/eliminar/", views.movimiento_eliminar, name="movimiento_eliminar"),

    path("categorias/", views.categorias_list, name="categorias"),
    path("categorias/nueva-rapida/", views.categoria_crear_rapida, name="categoria_nueva_rapida"),
]
