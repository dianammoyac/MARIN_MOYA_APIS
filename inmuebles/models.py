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
