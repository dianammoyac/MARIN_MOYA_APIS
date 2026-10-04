from django.contrib import admin
from .models import Perfilacion, EvaluacionPerfil, SimulacionFinanciera, SolicitudAsesoria, ReferenciaFinanciera, ReferenciaCambio


@admin.register(ReferenciaFinanciera)
class ReferenciaFinancieraAdmin(admin.ModelAdmin):
    list_display = ('entidad', 'producto', 'tasa_ea', 'verificada', 'vence', 'activa')
    list_filter = ('activa', 'vence')
    search_fields = ('entidad', 'producto')


@admin.register(ReferenciaCambio)
class ReferenciaCambioAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'cop_por_usd', 'fuente', 'activa')
    list_filter = ('activa', 'fecha')
    search_fields = ('fuente',)


@admin.register(SolicitudAsesoria)
class SolicitudAsesoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'accion', 'estado', 'creada')
    list_filter = ('estado', 'accion', 'creada')
    search_fields = ('nombre', 'correo', 'telefono')
    readonly_fields = ('perfilacion', 'evaluacion', 'inmueble', 'nombre', 'telefono', 'correo', 'preferencia_contacto', 'accion', 'consentimiento', 'clave_idempotencia', 'creada')


@admin.register(Perfilacion)
class PerfilacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'estado', 'revision', 'creado')
    readonly_fields = ('id', 'usuario', 'clave_sesion', 'respuestas', 'revision', 'version_preguntas', 'estado', 'creado', 'actualizado')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EvaluacionPerfil, SimulacionFinanciera)
class HistorialAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
