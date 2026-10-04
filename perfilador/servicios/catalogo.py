from inmuebles.models import Inmueble
from .financiacion import MESES_ES, meses_restantes, sumar_meses, texto_mes_ano


def obtener_catalogo_publico():
    """Única fuente de candidatos fase 1; aislable por contexto en una versión futura."""
    return Inmueble.objects.filter(
        tipo__in=['CASA', 'APARTAMENTO'], operacion='VENTA', estatus='DISPONIBLE'
    ).order_by('id')


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
    fecha_fija = entrega_fija = restantes = None
    if modalidad == 'SOBRE_PLANOS' and meses is None:
        entrega_texto = 'Entrega por confirmar con la constructora'
    elif modalidad == 'SOBRE_PLANOS':
        entrega_fija = sumar_meses(inmueble.fecha_publicacion, int(meses))
        fecha_fija = entrega_fija.isoformat()
        restantes = meses_restantes(inmueble.fecha_publicacion, int(meses))
        if restantes > 0:
            entrega_texto = (f'Sobre planos: entrega declarada en {int(meses)} meses '
                             f'({texto_mes_ano(entrega_fija)}); quedan {restantes}')
        else:
            entrega_texto = (f'Sobre planos: la entrega declarada ({texto_mes_ano(entrega_fija)}) ya llegó; '
                             'la inicial debe cubrirse con los recursos actuales')
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
        'fecha_entrega_fija': fecha_fija, 'meses_restantes': restantes,
        'empresa': (inmueble.empresa or '').strip() or None,
        'origen_texto': texto_origen(inmueble, modalidad),
        'porcentaje_inicial_exigido': str(inmueble.porcentaje_inicial_exigido) if inmueble.porcentaje_inicial_exigido is not None else None,
        'valor_separacion': str(inmueble.valor_separacion) if inmueble.valor_separacion is not None else None,
        'pendientes_catalogo': pendientes,
    }
