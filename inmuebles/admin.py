from django.contrib import admin
from .models import Inmueble


@admin.register(Inmueble)
class InmuebleAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'titulo', 'tipo', 'operacion', 'estado', 'modalidad_entrega',
                    'meses_entrega', 'empresa', 'ciudad', 'departamento', 'precio', 'estatus')
    list_filter = ('tipo', 'operacion', 'estado', 'modalidad_entrega', 'estatus', 'departamento')
    search_fields = ('codigo', 'titulo', 'ciudad', 'barrio')
    list_editable = ('modalidad_entrega', 'meses_entrega')
    readonly_fields = ('codigo', 'fecha_publicacion', 'fecha_actualizacion')
