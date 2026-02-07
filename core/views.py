from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404

from .models import Movimiento, Categoria
from .forms import MovimientoForm


MESES = [
    (1, "Enero"), (2, "Febrero"), (3, "Marzo"), (4, "Abril"),
    (5, "Mayo"), (6, "Junio"), (7, "Julio"), (8, "Agosto"),
    (9, "Septiembre"), (10, "Octubre"), (11, "Noviembre"), (12, "Diciembre"),
]

def _prev_month(anio, mes):
    return (anio - 1, 12) if mes == 1 else (anio, mes - 1)

def _next_month(anio, mes):
    return (anio + 1, 1) if mes == 12 else (anio, mes + 1)

def _pct_change(actual, previo):
    # evita división por 0
    if previo in (0, None):
        return None if actual != 0 else 0
    return float((actual - previo) / previo) * 100

@login_required
def dashboard(request):
    hoy = date.today()
    mes = int(request.GET.get("mes", hoy.month))
    anio = int(request.GET.get("anio", hoy.year))

    qs_mes = Movimiento.objects.filter(user=request.user, fecha__year=anio, fecha__month=mes)

    total_ingresos = qs_mes.filter(tipo="INGRESO").aggregate(s=Sum("monto"))["s"] or 0
    total_gastos = qs_mes.filter(tipo="GASTO").aggregate(s=Sum("monto"))["s"] or 0
    balance = total_ingresos - total_gastos

    # tasa de ahorro
    tasa_ahorro = None
    if total_ingresos != 0:
        tasa_ahorro = float(balance / total_ingresos) * 100

    # mes anterior
    anio_prev, mes_prev = _prev_month(anio, mes)
    qs_prev = Movimiento.objects.filter(user=request.user, fecha__year=anio_prev, fecha__month=mes_prev)
    ingresos_prev = qs_prev.filter(tipo="INGRESO").aggregate(s=Sum("monto"))["s"] or 0
    gastos_prev = qs_prev.filter(tipo="GASTO").aggregate(s=Sum("monto"))["s"] or 0

    ingresos_var_pct = _pct_change(total_ingresos, ingresos_prev)
    gastos_var_pct = _pct_change(total_gastos, gastos_prev)

    # listados del mes
    movimientos_mes = qs_mes.order_by("-fecha", "-id")[:20]
    top_gastos = qs_mes.filter(tipo="GASTO").order_by("-monto")[:5]

    gastos_por_categoria = (
        qs_mes.filter(tipo="GASTO")
        .values("categoria__nombre")
        .annotate(total=Sum("monto"))
        .order_by("-total")
    )

    # Años disponibles
    anios_disponibles = list(
        Movimiento.objects.filter(user=request.user).dates("fecha", "year", order="DESC")
    )
    if anios_disponibles:
        anios = [d.year for d in anios_disponibles]
    else:
        anios = list(range(hoy.year - 2, hoy.year + 1))

    # nav mes anterior / siguiente
    anio_next, mes_next = _next_month(anio, mes)

    return render(request, "core/dashboard.html", {
        "total_ingresos": total_ingresos,
        "total_gastos": total_gastos,
        "balance": balance,
        "tasa_ahorro": tasa_ahorro,

        "ingresos_var_pct": ingresos_var_pct,
        "gastos_var_pct": gastos_var_pct,

        "ultimos": movimientos_mes,
        "top_gastos": top_gastos,
        "gastos_por_categoria": gastos_por_categoria,

        "anio": anio,
        "mes": mes,
        "meses": MESES,
        "anios": anios,

        "anio_prev": anio_prev,
        "mes_prev": mes_prev,
        "anio_next": anio_next,
        "mes_next": mes_next,
    })


@login_required
def movimiento_crear(request):
    if request.method == "POST":
        form = MovimientoForm(request.POST, user=request.user)
        if form.is_valid():
            mov = form.save(commit=False)
            mov.user = request.user
            mov.save()
            return redirect("core:dashboard")
    else:
        form = MovimientoForm(user=request.user)
    return render(request, "core/movimiento_form.html", {"form": form})


@login_required
def movimientos_list(request):
    movimientos = Movimiento.objects.filter(user=request.user)
    return render(request, "core/movimiento_list.html", {"movimientos": movimientos})


@login_required
def categorias_list(request):
    categorias = Categoria.objects.filter(user=request.user)
    return render(request, "core/categoria_list.html", {"categorias": categorias})


@login_required
def categoria_crear_rapida(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        tipo = request.POST.get("tipo", "AMBOS")
        if nombre:
            Categoria.objects.get_or_create(
                user=request.user,
                nombre=nombre,
                defaults={"tipo": tipo}
            )
    return redirect("core:categorias")


@login_required
def movimiento_editar(request, pk):
    mov = get_object_or_404(Movimiento, pk=pk, user=request.user)

    if request.method == "POST":
        form = MovimientoForm(request.POST, instance=mov, user=request.user)
        if form.is_valid():
            form.save()
            return redirect("core:movimientos")
    else:
        form = MovimientoForm(instance=mov, user=request.user)

    return render(request, "core/movimiento_form.html", {"form": form, "editando": True})


@login_required
def movimiento_eliminar(request, pk):
    mov = get_object_or_404(Movimiento, pk=pk, user=request.user)

    if request.method == "POST":
        mov.delete()
        return redirect("core:movimientos")

    return render(request, "core/movimiento_confirm_delete.html", {"mov": mov})
