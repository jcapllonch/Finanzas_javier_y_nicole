from django import forms
from .models import Movimiento, Categoria

class MovimientoForm(forms.ModelForm):
    class Meta:
        model = Movimiento
        fields = ["tipo", "fecha", "monto", "categoria", "descripcion"]
        widgets = {"fecha": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["categoria"].queryset = Categoria.objects.filter(user=user)
