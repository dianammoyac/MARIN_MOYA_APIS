from rest_framework import viewsets
from .models import Inmueble
from .serializers import InmuebleSerializer


class InmuebleViewSet(viewsets.ModelViewSet):
    queryset = Inmueble.objects.all().order_by('-id')
    serializer_class = InmuebleSerializer
