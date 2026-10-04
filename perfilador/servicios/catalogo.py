from inmuebles.models import Inmueble


def obtener_catalogo_publico():
    """Única fuente de candidatos fase 1; aislable por contexto en una versión futura."""
    return Inmueble.objects.filter(
        tipo__in=['CASA', 'APARTAMENTO'], operacion='VENTA', estatus='DISPONIBLE'
    ).order_by('id')


MESES_ES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
            'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


def texto_origen(inmueble, modalidad):
    empresa = (getattr(inmueble, 'empresa', '') or '').strip()
    fecha = getattr(inmueble, 'fecha_entrega_constructora', None)
    if modalidad == 'SOBRE_PLANOS':
        return f'Proyecto de {empresa}' if empresa else None
    if empresa and fecha:
        return f'Construido por {empresa}, entregado en {MESES_ES[fecha.month - 1]} de {fecha.year}'
    if empresa:
        return f'Comercializado por {empresa}'
    return None


def ficha(inmueble):
    modalidad = getattr(inmueble, 'modalidad_entrega', 'TERMINADO') or 'TERMINADO'
    meses = getattr(inmueble, 'meses_entrega', None)
    if modalidad == 'SOBRE_PLANOS' and meses is None:
        entrega_texto = 'Entrega por confirmar con la constructora'
    elif modalidad == 'SOBRE_PLANOS':
        entrega_texto = f'Sobre planos: entrega declarada en {int(meses)} meses'
    else:
        entrega_texto = 'Entrega inmediata (proyecto terminado)'
    pendientes = ['Condición de cuota inicial', 'Inclusiones y gastos de compra']
    if modalidad == 'SOBRE_PLANOS' and meses is None:
        pendientes.insert(0, 'Fecha de entrega')
    return {
        'id': inmueble.pk, 'titulo': inmueble.titulo, 'tipo': inmueble.get_tipo_display(),
        'departamento': inmueble.departamento, 'ciudad': inmueble.ciudad, 'barrio': inmueble.barrio,
        'area_m2': str(inmueble.area_m2), 'habitaciones': inmueble.habitaciones,
        'parqueaderos': inmueble.parqueaderos, 'precio': str(inmueble.precio),
        'administracion': str(inmueble.administracion) if inmueble.administracion is not None else None,
        'moneda': inmueble.moneda, 'imagen': inmueble.imagen1.url if inmueble.imagen1 else None,
        'actualizado': inmueble.fecha_actualizacion.isoformat() if inmueble.fecha_actualizacion else None,
        'url': f'/inmuebles/{inmueble.pk}/',
        'modalidad_entrega': modalidad, 'meses_entrega': meses, 'entrega_texto': entrega_texto,
        'empresa': (inmueble.empresa or '').strip() or None,
        'origen_texto': texto_origen(inmueble, modalidad),
        'porcentaje_inicial_exigido': str(inmueble.porcentaje_inicial_exigido) if inmueble.porcentaje_inicial_exigido is not None else None,
        'valor_separacion': str(inmueble.valor_separacion) if inmueble.valor_separacion is not None else None,
        'pendientes_catalogo': pendientes,
    }
