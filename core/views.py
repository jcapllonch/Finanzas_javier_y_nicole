from datetime import date
import os
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
import json
from .models import Movimiento, Categoria
from .forms import MovimientoForm
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
import google.generativeai as genai


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

def _get_dashboard_aggregates(user, anio, mes):
    qs_mes = Movimiento.objects.filter(user=user, fecha__year=anio, fecha__month=mes)

    total_ingresos = float(qs_mes.filter(tipo="INGRESO").aggregate(s=Sum("monto"))["s"] or 0)
    total_gastos = float(qs_mes.filter(tipo="GASTO").aggregate(s=Sum("monto"))["s"] or 0)
    balance = total_ingresos - total_gastos
    tasa_ahorro = None
    if total_ingresos != 0:
        tasa_ahorro = (balance / total_ingresos) * 100.0

    gastos_por_categoria = list(
        qs_mes.filter(tipo="GASTO")
        .values("categoria__nombre")
        .annotate(total=Sum("monto"))
        .order_by("-total")[:8]
    )
    # serializable
    top_cats = [{"categoria": x["categoria__nombre"], "total": float(x["total"] or 0)} for x in gastos_por_categoria]

    return {
        "anio": int(anio),
        "mes": int(mes),
        "total_ingresos": total_ingresos,
        "total_gastos": total_gastos,
        "balance": balance,
        "tasa_ahorro": tasa_ahorro,
        "top_gastos_categoria": top_cats,
    }


@login_required
def asistente(request):
    """
    Página del chat. Solo renderiza el template.
    """
    return render(request, "core/asistente.html")


@require_POST
@csrf_protect
@login_required
def asistente_preguntar(request):
    """
    Endpoint AJAX: recibe una pregunta y devuelve respuesta de Gemini.
    Solo envía datos agregados del mes/año (no movimientos).
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "JSON inválido"}, status=400)

    pregunta = (data.get("pregunta") or "").strip()
    if not pregunta:
        return JsonResponse({"ok": False, "error": "Escribe una pregunta"}, status=400)

    # Mes/año opcional (si no viene, usa actuales)
    from datetime import date
    hoy = date.today()
    mes = int(data.get("mes") or hoy.month)
    anio = int(data.get("anio") or hoy.year)

    # Datos agregados
    resumen = _get_dashboard_aggregates(request.user, anio, mes)

    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    print("[IA] GEMINI_API_KEY cargada:", "SI" if api_key else "NO")
    if not api_key:
        return JsonResponse({"ok": False, "error": "Falta GEMINI_API_KEY en variables de entorno"}, status=500)

    # Config Gemini
    model_name = (os.getenv("GEMINI_MODEL") or "models/gemini-2.0-flash").strip()
    if not model_name.startswith("models/"):
        model_name = "models/" + model_name
    print(f"[IA] Modelo Gemini usado: {model_name}")
    model = genai.GenerativeModel(model_name)

    system_style = f"""
Eres un asistente financiero CASERO para Chile.
Hablas en español chileno neutro, claro y amable.
No das asesoría legal/tributaria profesional. Das orientación general.
NO pidas ni reveles datos sensibles. No inventes montos.
Si falta info, pregunta 1 cosa concreta.
Entrega respuestas en formato:
- Resumen (1-2 líneas)
- Consejos (3 bullets)
- Siguiente paso (1 acción)
"""

    context = f"""
DATOS AGREGADOS DEL USUARIO (NO SON MOVIMIENTOS DETALLADOS):
Año: {resumen["anio"]}, Mes: {resumen["mes"]}
Total ingresos: {resumen["total_ingresos"]}
Total gastos: {resumen["total_gastos"]}
Balance: {resumen["balance"]}
Tasa ahorro (%): {resumen["tasa_ahorro"]}
Top gastos por categoría (máx 8): {resumen["top_gastos_categoria"]}
"""

    prompt = f"""{system_style}

{context}

PREGUNTA DEL USUARIO:
{pregunta}
"""

    try:
        print(f"[IA] Gemini model usado: {model_name}")
        resp = model.generate_content(prompt)
        texto = (resp.text or "").strip()
        if not texto:
            texto = "No pude generar una respuesta. Intenta de nuevo con otra pregunta."
        return JsonResponse({"ok": True, "respuesta": texto, "resumen": resumen})
    except Exception as e:
         msg = str(e)

    # ✅ Si es cuota / rate limit: fallback sin IA (100% gratis)
    if "429" in msg or "quota" in msg.lower() or "exceeded your current quota" in msg.lower():
        # respuestas útiles sin IA, basadas en resumen agregado
        tips = []
        if resumen["total_ingresos"] > 0:
            gasto_pct = (resumen["total_gastos"] / resumen["total_ingresos"]) * 100
            tips.append(f"Estás gastando aprox. {gasto_pct:.1f}% de tus ingresos este mes.")
        if resumen["balance"] < 0:
            tips.append("Tu balance está NEGATIVO. Prioriza bajar gastos variables esta semana.")
        else:
            tips.append("Vas con balance POSITIVO. Intenta mantener el ritmo y separar un % a ahorro.")

        top = resumen.get("top_gastos_categoria", [])[:3]
        if top:
            cats = ", ".join([f'{x["categoria"]} (${x["total"]:.0f})' for x in top])
            tips.append(f"Top gastos por categoría: {cats}.")

        fallback = (
            "⚠️ La IA está temporalmente sin cuota (free tier en 0 / rate limit).\n\n"
            "✅ Resumen rápido:\n"
            f"- Ingresos: ${resumen['total_ingresos']:.0f}\n"
            f"- Gastos: ${resumen['total_gastos']:.0f}\n"
            f"- Balance: ${resumen['balance']:.0f}\n\n"
            "💡 Consejos (sin IA):\n"
            + "\n".join([f"- {t}" for t in tips]) +
            "\n\n👉 Siguiente paso: dime tu meta (ej: ahorrar $100.000) y te digo cuánto debes recortar por semana."
        )

        return JsonResponse({"ok": True, "respuesta": fallback, "resumen": resumen})

    # otros errores normales
    return JsonResponse({"ok": False, "error": f"Error llamando a Gemini: {msg}"}, status=500)