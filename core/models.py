from django.conf import settings
from django.db import models

class Categoria(models.Model):
    TIPO_CHOICES = (
        ("GASTO", "Gasto"),
        ("INGRESO", "Ingreso"),
        ("AMBOS", "Ambos"),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="categorias")
    nombre = models.CharField(max_length=60)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default="AMBOS")

    class Meta:
        unique_together = ("user", "nombre")
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Movimiento(models.Model):
    TIPO_CHOICES = (
        ("GASTO", "Gasto"),
        ("INGRESO", "Ingreso"),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="movimientos")
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    fecha = models.DateField()
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="movimientos")
    descripcion = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"{self.tipo} {self.monto} ({self.fecha})"

