from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User


class Inmueble(models.Model):
    TIPO_INMUEBLE = [
        ('APARTAMENTO', 'Apartamento'),
        ('CASA', 'Casa'),
        ('LOCAL', 'Local comercial'),
        ('OFICINA', 'Oficina'),
        ('LOTE', 'Lote'),
        ('BODEGA', 'Bodega'),
    ]

    OPERACION = [
        ('VENTA', 'Venta'),
        ('ARRIENDO', 'Arriendo'),
        ('CESION', 'Cesión'),
    ]

    ESTADO_INMUEBLE = [
        ('NUEVO', 'Nuevo'),
        ('USADO', 'Usado'),
        ('EN_CONSTRUCCION', 'En construcción'),
    ]

    MODALIDAD_ENTREGA = [
        ('TERMINADO', 'Terminada / entrega inmediata'),
        ('SOBRE_PLANOS', 'Sobre planos'),
    ]

    ESTATUS_PUBLICACION = [
        ('DISPONIBLE', 'Disponible'),
        ('RESERVADO', 'Reservado'),
        ('VENDIDO', 'Vendido'),
        ('ARRENDADO', 'Arrendado'),
        ('INACTIVO', 'Inactivo'),
    ]

    id = models.BigAutoField(primary_key=True)

    # Identidad comercial (portal)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    codigo = models.CharField(max_length=30, unique=True)  # Ej: MM-BOG-0001
    titulo = models.CharField(max_length=150)
    descripcion = models.TextField()

    # Clasificación
    tipo = models.CharField(max_length=20, choices=TIPO_INMUEBLE)
    operacion = models.CharField(max_length=15, choices=OPERACION, default='VENTA')
    estado = models.CharField(max_length=20, choices=ESTADO_INMUEBLE, default='USADO')

    # Ubicación
    pais = models.CharField(max_length=60, default='Colombia')
    departamento = models.CharField(max_length=60)
    ciudad = models.CharField(max_length=60)
    barrio = models.CharField(max_length=80)
    direccion = models.CharField(max_length=150, blank=True)

    # Características
    area_m2 = models.DecimalField(max_digits=10, decimal_places=2)
    area_construida_m2 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    habitaciones = models.IntegerField(default=0)
    banos = models.IntegerField(default=0)
    parqueaderos = models.IntegerField(default=0)
    estrato = models.IntegerField(null=True, blank=True)
    piso = models.IntegerField(null=True, blank=True)
    ano_construccion = models.IntegerField(null=True, blank=True)

    # Entrega (para diferenciar proyecto terminado de sobre planos en el perfilador).
    # Solo los sobre planos tienen meses, % exigido y separación; las terminadas, fecha de entrega.
    modalidad_entrega = models.CharField(max_length=15, choices=MODALIDAD_ENTREGA, default='TERMINADO')
    meses_entrega = models.PositiveIntegerField(null=True, blank=True)
    fecha_entrega_constructora = models.DateField(null=True, blank=True)
    porcentaje_inicial_exigido = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    valor_separacion = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    empresa = models.CharField(max_length=120, blank=True)

    # Valores
    precio = models.DecimalField(max_digits=14, decimal_places=2)
    administracion = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    moneda = models.CharField(max_length=10, default='COP')

    # Publicación
    estatus = models.CharField(max_length=12, choices=ESTATUS_PUBLICACION, default='DISPONIBLE')
    destacado = models.BooleanField(default=False)

    # Contacto
    nombre_contacto = models.CharField(max_length=100, blank=True)
    telefono_contacto = models.CharField(max_length=30, blank=True)
    email_contacto = models.EmailField(blank=True)

    # Imágenes
    imagen1 = models.ImageField(upload_to='inmuebles/', blank=True, null=True)
    imagen2 = models.ImageField(upload_to='inmuebles/', blank=True, null=True)
    imagen3 = models.ImageField(upload_to='inmuebles/', blank=True, null=True)
    imagen4 = models.ImageField(upload_to='inmuebles/', blank=True, null=True)

    # Fechas
    fecha_publicacion = models.DateField(auto_now_add=True)
    fecha_actualizacion = models.DateField(auto_now=True)

    class Meta:
        db_table = 'inmuebles'
        verbose_name = "Inmueble"
        verbose_name_plural = "Inmuebles"

    def clean(self):
        errores = {}
        if self.estado == 'USADO' and self.modalidad_entrega == 'SOBRE_PLANOS':
            errores['modalidad_entrega'] = 'Un inmueble usado no puede publicarse como sobre planos.'
        if self.modalidad_entrega == 'SOBRE_PLANOS':
            if not self.meses_entrega:
                errores['meses_entrega'] = 'Indique en cuántos meses está la entrega del proyecto sobre planos.'
            if self.fecha_entrega_constructora:
                errores['fecha_entrega_constructora'] = 'La fecha de entrega por constructora solo aplica a proyectos terminados.'
            if self.porcentaje_inicial_exigido is not None and not 0 < self.porcentaje_inicial_exigido <= 100:
                errores['porcentaje_inicial_exigido'] = 'Indique un porcentaje entre 0 y 100.'
            if self.valor_separacion is not None and self.valor_separacion < 0:
                errores['valor_separacion'] = 'La separación no puede ser negativa.'
        else:
            for campo in ('meses_entrega', 'porcentaje_inicial_exigido', 'valor_separacion'):
                if getattr(self, campo) not in (None, ''):
                    errores[campo] = 'Un proyecto terminado se entrega de inmediato; este dato solo aplica a sobre planos.'
        if errores:
            raise ValidationError(errores)

    def __str__(self):
        return f"{self.codigo} - {self.titulo}"

    def save(self, *args, **kwargs):
        # Solo generamos el código si no existe (creación)
        if not self.codigo:
            # Extraemos las iniciales (asegurando que existan)
            p = self.pais[0].upper() if self.pais else 'X'
            d = self.departamento[0].upper() if self.departamento else 'X'
            c = self.ciudad[0].upper() if self.ciudad else 'X'
            prefix = f"{p}{d}{c}-"

            # Buscamos el último inmueble con ese mismo prefijo para incrementar el número
            ultimo = Inmueble.objects.filter(codigo__startswith=prefix).order_by('id').last()
            
            if ultimo:
                # Intentamos extraer el número final después del guion
                try:
                    ultimo_numero = int(ultimo.codigo.split('-')[-1])
                    nuevo_numero = ultimo_numero + 1
                except (ValueError, IndexError):
                    nuevo_numero = 1
            else:
                nuevo_numero = 1

            self.codigo = f"{prefix}{nuevo_numero}"
        
        super().save(*args, **kwargs)
