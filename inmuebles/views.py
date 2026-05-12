from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from rest_framework import viewsets

from .forms import InmuebleForm
from .forms_auth import LoginForm, RegistroForm
from .models import Inmueble
from .serializers import InmuebleSerializer


class InmuebleViewSet(viewsets.ModelViewSet):
    queryset = Inmueble.objects.all().order_by('-id')
    serializer_class = InmuebleSerializer


def index2_view(request):
    inmuebles = Inmueble.objects.all().order_by('?')
    return render(request, "inmuebles/index2.html", {"inmuebles": inmuebles})


def login_view(request):
    if request.user.is_authenticated:
        if request.user.username == 'dianamoya':
            return redirect("admin_dashboard")
        return redirect("mis_inmuebles")

    form = LoginForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"]
        password = form.cleaned_data["password"]

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "Bienvenido al sistema.")
            if user.username == 'dianamoya':
                return redirect("admin_dashboard")
            return redirect("mis_inmuebles")

        messages.error(request, "Usuario o contraseña incorrectos.")

    return render(request, "auth/login.html", {"form": form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("inmuebles_listado")

    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Cuenta creada exitosamente. ¡Bienvenido!")
            return redirect("mis_inmuebles")
    else:
        form = RegistroForm()
    return render(request, "auth/register.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "Sesión cerrada correctamente.")
    return redirect("index2")


def inmuebles_listado(request):
    inmuebles = Inmueble.objects.all().order_by("-id")
    return render(request, "inmuebles/listado.html", {"inmuebles": inmuebles})


@login_required
def mis_inmuebles(request):
    # El Agente es is_staff=True pero is_superuser=False
    es_agente = request.user.is_staff and not request.user.is_superuser
    lista_propietarios = []

    if es_agente:
        # Los agentes ven todos los inmuebles para supervisión
        inmuebles_query = Inmueble.objects.all().order_by("-id")
        # Obtener lista de nombres de usuario únicos que tienen inmuebles para las sugerencias
        lista_propietarios = Inmueble.objects.exclude(usuario__isnull=True).values_list('usuario__username', flat=True).distinct()

        usuario_filtro = request.GET.get('usuario_filtro')
        if usuario_filtro:
            inmuebles_query = inmuebles_query.filter(usuario__username__icontains=usuario_filtro)
    else:
        # Usuarios normales solo ven su inventario personal
        inmuebles_query = Inmueble.objects.filter(usuario=request.user).order_by("-id")

    stats = {
        'total': inmuebles_query.count(),
        'activos': inmuebles_query.filter(estatus='DISPONIBLE').count(),
        'pausados': inmuebles_query.filter(estatus='INACTIVO').count(),
        'finalizados': inmuebles_query.filter(estatus__in=['VENDIDO', 'ARRENDADO']).count(),
    }
    return render(request, "inmuebles/dashboard.html", {
        "inmuebles": inmuebles_query, 
        "stats": stats, 
        "es_agente": es_agente,
        "lista_propietarios": lista_propietarios
    })


@login_required
def perfil_view(request):
    inmuebles_user = Inmueble.objects.filter(usuario=request.user)
    stats = {
        'total': inmuebles_user.count(),
        'activos': inmuebles_user.filter(estatus='DISPONIBLE').count(),
    }
    return render(request, "inmuebles/perfil.html", {"stats": stats})


def inmuebles_detalle(request, pk):
    inmueble = get_object_or_404(Inmueble, pk=pk)
    return render(request, "inmuebles/detalle.html", {"inmueble": inmueble})


@login_required
def inmuebles_crear(request):
    if request.method == "POST":
        form = InmuebleForm(request.POST, request.FILES) # Añadir request.FILES
        if form.is_valid():
            inmueble = form.save(commit=False)
            inmueble.usuario = request.user
            inmueble.save()
            return redirect("mis_inmuebles")
    else:
        form = InmuebleForm()

    return render(request, "inmuebles/form.html", {"form": form})

@login_required
def inmuebles_editar(request, pk):
    inmueble = get_object_or_404(Inmueble, pk=pk)

    # Seguridad: Aunque el agente vea el inmueble, solo el dueño o Diana pueden editar
    if inmueble.usuario != request.user and request.user.username != 'dianamoya':
        messages.error(request, "No tienes permiso para editar un inmueble que no te pertenece.")
        return redirect("mis_inmuebles")

    if request.method == "POST":
        form = InmuebleForm(request.POST, request.FILES, instance=inmueble)
        if form.is_valid():
            inmueble = form.save(commit=False)
            if not inmueble.usuario: # Si el inmueble no tenía dueño (era antiguo), se le asigna el actual
                inmueble.usuario = request.user
            inmueble.save()
            messages.success(request, "Inmueble actualizado correctamente.")
            return redirect("inmuebles_detalle", pk=inmueble.pk)
    else:
        form = InmuebleForm(instance=inmueble)
    return render(request, "inmuebles/form.html", {"form": form, "editando": True})

@login_required
def inmuebles_eliminar(request, pk):
    inmueble = get_object_or_404(Inmueble, pk=pk)

    # Seguridad: Solo el dueño o Diana pueden eliminar
    if inmueble.usuario != request.user and request.user.username != 'dianamoya':
        messages.error(request, "No tienes permiso para eliminar un inmueble que no te pertenece.")
        return redirect("mis_inmuebles")

    if request.method == "POST":
        inmueble.delete()
        messages.success(request, "Inmueble eliminado correctamente.")
        return redirect("inmuebles_listado")
    return render(request, "inmuebles/eliminar.html", {"inmueble": inmueble})