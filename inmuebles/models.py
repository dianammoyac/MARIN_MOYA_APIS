from django.db import models


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
        ('VENTA_ARRIENDO', 'Venta y Arriendo'),
    ]

    ESTADO_INMUEBLE = [
        ('NUEVO', 'Nuevo'),
        ('USADO', 'Usado'),
        ('EN_CONSTRUCCION', 'En construcción'),
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

    # Fechas
    fecha_publicacion = models.DateField()
    fecha_actualizacion = models.DateField()

    class Meta:
        db_table = 'inmuebles'
        verbose_name = "Inmueble"
        verbose_name_plural = "Inmuebles"

    def __str__(self):
        return f"{self.codigo} - {self.titulo}"
