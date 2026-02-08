from rest_framework import viewsets
from .models import Inmueble
from .serializers import InmuebleSerializer
from django.shortcuts import render, get_object_or_404, redirect
from .models import Inmueble
from .forms import InmuebleForm


class InmuebleViewSet(viewsets.ModelViewSet):
    queryset = Inmueble.objects.all().order_by('-id')
    serializer_class = InmuebleSerializer

def inmuebles_listado(request):
    inmuebles = Inmueble.objects.all().order_by("-id")
    return render(request, "inmuebles/listado.html", {"inmuebles": inmuebles})

def inmuebles_detalle(request, pk):
    inmueble = get_object_or_404(Inmueble, pk=pk)
    return render(request, "inmuebles/detalle.html", {"inmueble": inmueble})

def inmuebles_crear(request):
    if request.method == "POST":
        form = InmuebleForm(request.POST)
        if form.is_valid():
            inmueble = form.save()
            return redirect("inmuebles_detalle", pk=inmueble.pk)
    else:
        form = InmuebleForm()

    return render(request, "inmuebles/form.html", {"form": form})