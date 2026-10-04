from inmuebles.models import Inmueble


def obtener_catalogo_publico():
    """Única fuente de candidatos fase 1; aislable por contexto en una versión futura."""
    return Inmueble.objects.filter(
        tipo__in=['CASA', 'APARTAMENTO'], operacion='VENTA', estatus='DISPONIBLE'
    ).order_by('id')


def ficha(inmueble):
    return {
        'id': inmueble.pk, 'titulo': inmueble.titulo, 'tipo': inmueble.get_tipo_display(),
        'departamento': inmueble.departamento, 'ciudad': inmueble.ciudad, 'barrio': inmueble.barrio,
        'area_m2': str(inmueble.area_m2), 'habitaciones': inmueble.habitaciones,
        'parqueaderos': inmueble.parqueaderos, 'precio': str(inmueble.precio),
        'administracion': str(inmueble.administracion) if inmueble.administracion is not None else None,
        'moneda': inmueble.moneda, 'imagen': inmueble.imagen1.url if inmueble.imagen1 else None,
        'actualizado': inmueble.fecha_actualizacion.isoformat() if inmueble.fecha_actualizacion else None,
        'url': f'/inmuebles/{inmueble.pk}/',
        'pendientes_catalogo': ['Fecha de entrega', 'Condición de cuota inicial', 'Inclusiones y gastos de compra'],
    }
