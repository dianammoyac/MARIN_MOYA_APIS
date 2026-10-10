import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Perfilacion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    clave_sesion = models.CharField(max_length=40, db_index=True)
    respuestas = models.JSONField(default=dict)
    revision = models.PositiveIntegerField(default=0)
    version_preguntas = models.CharField(max_length=12, default='6')
    estado = models.CharField(max_length=24, default='EXPLORACION', choices=[('EXPLORACION', 'Exploración'), ('PRELIMINAR', 'Resultado preliminar'), ('SOLICITUD', 'Solicitud registrada')])
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Perfil {self.id}'


class EvaluacionPerfil(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    perfilacion = models.ForeignKey(Perfilacion, on_delete=models.CASCADE, related_name='evaluaciones')
    revision = models.PositiveIntegerField()
    respuestas = models.JSONField()
    resultados = models.JSONField()
    version_reglas = models.CharField(max_length=12, default='1')
    fecha = models.DateTimeField(auto_now_add=True)


class ReferenciaFinanciera(models.Model):
    entidad = models.CharField(max_length=120)
    producto = models.CharField(max_length=120)
    tasa_ea = models.DecimalField(max_digits=7, decimal_places=5)
    fuente = models.URLField(blank=True)
    condiciones = models.TextField(blank=True)
    verificada = models.DateField()
    vence = models.DateField()
    plazo_minimo = models.PositiveSmallIntegerField(default=5)
    plazo_maximo = models.PositiveSmallIntegerField(default=20)
    porcentaje_maximo = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    activa = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.entidad} — {self.producto}'

    def clean(self):
        errores = {}
        if self.tasa_ea is not None and not 0 <= self.tasa_ea <= 1:
            errores['tasa_ea'] = 'La tasa E.A. decimal debe estar entre 0 y 1.'
        if self.verificada and self.vence and self.vence < self.verificada:
            errores['vence'] = 'La fecha de revisión no puede preceder la verificación.'
        if self.plazo_minimo and self.plazo_maximo and self.plazo_maximo < self.plazo_minimo:
            errores['plazo_maximo'] = 'El plazo máximo debe superar el mínimo.'
        if self.porcentaje_maximo is not None and not 0 <= self.porcentaje_maximo <= 100:
            errores['porcentaje_maximo'] = 'Indique un porcentaje entre 0 y 100.'
        if self.activa and not self.fuente:
            errores['fuente'] = 'La fuente verificable es obligatoria para referencias activas.'
        if errores:
            raise ValidationError(errores)


class ReferenciaCambio(models.Model):
    """Tasa verificable de COP por USD; nunca se genera automáticamente."""
    cop_por_usd = models.DecimalField(max_digits=14, decimal_places=4)
    fecha = models.DateField(db_index=True)
    fuente = models.URLField()
    activa = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['fecha', 'fuente'], name='cambio_unico_por_fuente_fecha')]

    def clean(self):
        if self.cop_por_usd is not None and self.cop_por_usd <= 0:
            raise ValidationError({'cop_por_usd': 'La tasa COP/USD debe ser mayor que cero.'})

    def __str__(self):
        return f'{self.fecha}: {self.cop_por_usd} COP/USD'


class SimulacionFinanciera(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    perfilacion = models.ForeignKey(Perfilacion, on_delete=models.CASCADE, related_name='simulaciones')
    evaluacion = models.ForeignKey(EvaluacionPerfil, on_delete=models.PROTECT)
    inmueble = models.ForeignKey('inmuebles.Inmueble', null=True, on_delete=models.SET_NULL)
    revision = models.PositiveIntegerField()
    referencia = models.ForeignKey(ReferenciaFinanciera, null=True, blank=True, on_delete=models.SET_NULL)
    parametros = models.JSONField()
    resultado = models.JSONField()
    fecha = models.DateTimeField(auto_now_add=True)


class SolicitudAsesoria(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    perfilacion = models.ForeignKey(Perfilacion, on_delete=models.PROTECT, related_name='solicitudes')
    evaluacion = models.ForeignKey(EvaluacionPerfil, on_delete=models.PROTECT)
    inmueble = models.ForeignKey('inmuebles.Inmueble', null=True, blank=True, on_delete=models.SET_NULL)
    nombre = models.CharField(max_length=120)
    telefono = models.CharField(max_length=40, blank=True)
    correo = models.EmailField(blank=True)
    preferencia_contacto = models.CharField(max_length=12, choices=[('TELEFONO', 'Teléfono'), ('CORREO', 'Correo')])
    accion = models.CharField(max_length=24, choices=[('VISITA', 'Visita'), ('FINANCIACION', 'Revisar financiación'), ('CONDICIONES', 'Confirmar condiciones'), ('ACOMPANAMIENTO', 'Acompañamiento')])
    consentimiento = models.BooleanField(default=False)
    clave_idempotencia = models.UUIDField(unique=True)
    estado = models.CharField(max_length=15, default='NUEVA')
    creada = models.DateTimeField(auto_now_add=True)

