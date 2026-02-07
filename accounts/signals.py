from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models import Categoria


CATEGORIAS_POR_DEFECTO = [
    ("Bono", "INGRESO"),
    ("Comida Delivery", "GASTO"),
    ("Comida Eiko", "GASTO"),
    ("Comida Mall", "GASTO"),
    ("Cuenta Agua", "GASTO"),
    ("Cuenta Gas", "GASTO"),
    ("Cuenta Internet Hogar", "GASTO"),
    ("Cuenta Luz", "GASTO"),
    ("Cuota Auto Javier", "GASTO"),
    ("Gastos Donita", "GASTO"),
    ("Gastos Extraordinarios", "GASTO"),
    ("Mercadería Feria", "GASTO"),
    ("Mercadería Super Mercado", "GASTO"),
    ("Planes Moviles", "GASTO"),
    ("Salida Cine", "GASTO"),
    ("Sueldo", "INGRESO"),
    ("Suscripciones", "GASTO"),
    ("Transporte Escolar Gaspar", "GASTO"),
    ("Transporte Público", "GASTO"),
]


@receiver(post_save, sender=User)
def crear_categorias_por_defecto(sender, instance, created, **kwargs):
    if not created:
        return

    for nombre, tipo in CATEGORIAS_POR_DEFECTO:
        Categoria.objects.get_or_create(
            user=instance,
            nombre=nombre,
            defaults={"tipo": tipo},
        )
