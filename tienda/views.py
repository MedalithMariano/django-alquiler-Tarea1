import datetime
import random

from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncMonth
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import AlquilerCreateForm, MarcarPagadoForm, SimularVentasForm
from .models import Alquiler, Categoria, Cliente, Pelicula


#  DASHBOARD
def index(request: HttpRequest) -> HttpResponse:
    total_peliculas = Pelicula.objects.count()
    total_clientes = Cliente.objects.count()

    #  cambiado: ahora usamos estado
    alquileres_pendientes = Alquiler.objects.filter(estado='pendiente').count()

    ingresos = (
        Alquiler.objects.filter(estado='pagado')
        .aggregate(total=Sum("precio"))
        .get("total")
        or 0
    )

    #  Bloque B extra
    top_peliculas = Pelicula.objects.annotate(
        total_alquileres=Count('alquileres')
    ).order_by('-total_alquileres')[:5]

    ticket_promedio = Alquiler.objects.filter(
        estado='pagado'
    ).aggregate(promedio=Avg('precio'))["promedio"]

    return render(
        request,
        "tienda/index.html",
        {
            "total_peliculas": total_peliculas,
            "total_clientes": total_clientes,
            "alquileres_pendientes": alquileres_pendientes,
            "ingresos": ingresos,
            "top_peliculas": top_peliculas,
            "ticket_promedio": ticket_promedio,
        },
    )


# =========================
# CATEGORÍA
# =========================

class CategoriaListView(ListView):
    model = Categoria
    template_name = "tienda/categoria_list.html"
    context_object_name = "categorias"


class CategoriaCreateView(CreateView):
    model = Categoria
    fields = ["nombre", "descripcion"]
    template_name = "tienda/categoria_form.html"
    success_url = reverse_lazy("categoria_list")


class CategoriaUpdateView(UpdateView):
    model = Categoria
    fields = ["nombre", "descripcion"]
    template_name = "tienda/categoria_form.html"
    success_url = reverse_lazy("categoria_list")


class CategoriaDeleteView(DeleteView):
    model = Categoria
    template_name = "tienda/categoria_confirm_delete.html"
    success_url = reverse_lazy("categoria_list")


# =========================
# CLIENTE
# =========================

class ClienteListView(ListView):
    model = Cliente
    template_name = "tienda/cliente_list.html"
    context_object_name = "clientes"


class ClienteCreateView(CreateView):
    model = Cliente
    fields = ["nombre", "email", "telefono", "dni"]  #  agregado dni
    template_name = "tienda/cliente_form.html"
    success_url = reverse_lazy("cliente_list")


class ClienteUpdateView(UpdateView):
    model = Cliente
    fields = ["nombre", "email", "telefono", "dni"]  #  agregado dni
    template_name = "tienda/cliente_form.html"
    success_url = reverse_lazy("cliente_list")


# =========================
# PELÍCULA
# =========================

class PeliculaListView(ListView):
    model = Pelicula
    template_name = "tienda/pelicula_list.html"
    context_object_name = "peliculas"

    #  optimización
    def get_queryset(self):
        return Pelicula.objects.select_related("categoria")


class PeliculaCreateView(CreateView):
    model = Pelicula
    fields = [
        "titulo", "anio", "categoria", "precio_alquiler",
        "stock", "duracion_minutos", "director", "pais_origen"
    ]
    template_name = "tienda/pelicula_form.html"
    success_url = reverse_lazy("pelicula_list")


class PeliculaUpdateView(UpdateView):
    model = Pelicula
    fields = [
        "titulo", "anio", "categoria", "precio_alquiler",
        "stock", "duracion_minutos", "director", "pais_origen"
    ]
    template_name = "tienda/pelicula_form.html"
    success_url = reverse_lazy("pelicula_list")


class PeliculaDeleteView(DeleteView):
    model = Pelicula
    template_name = "tienda/pelicula_confirm_delete.html"
    success_url = reverse_lazy("pelicula_list")


# =========================
# ALQUILER
# =========================

class AlquilerListView(ListView):
    model = Alquiler
    template_name = "tienda/alquiler_list.html"
    context_object_name = "alquileres"

    #  optimización (Bloque B)
    def get_queryset(self):
        return Alquiler.objects.select_related("cliente", "pelicula")


class AlquilerCreateView(CreateView):
    model = Alquiler
    form_class = AlquilerCreateForm
    template_name = "tienda/alquiler_form.html"
    success_url = reverse_lazy("alquiler_list")


class MarcarPagadoView(View):
    def post(self, request, pk):
        alquiler = get_object_or_404(Alquiler, pk=pk)
        alquiler.estado = 'pagado'
        alquiler.fecha_pago = timezone.now()
        alquiler.save()
        return redirect("alquiler_list")


# =========================
# CONSULTAS AVANZADAS (BLOQUE B)
# =========================

def reportes(request):
    hoy = timezone.localdate()

    #  vencidos
    vencidos = Alquiler.objects.filter(
        estado='pendiente',
        fecha_devolucion__lt=hoy
    )

    #  ingresos por categoría
    ingresos_categoria = Alquiler.objects.values(
        'pelicula__categoria__nombre'
    ).annotate(
        total=Sum('precio')
    )

    #  ranking mensual
    ranking = Alquiler.objects.filter(
        estado='pagado'
    ).annotate(
        mes=TruncMonth('fecha_alquiler')
    ).values(
        'mes', 'cliente__nombre'
    ).annotate(
        total=Sum('precio')
    ).order_by('-mes', '-total')

    return render(
        request,
        "tienda/reportes.html",
        {
            "vencidos": vencidos,
            "ingresos_categoria": ingresos_categoria,
            "ranking": ranking,
        }
    )