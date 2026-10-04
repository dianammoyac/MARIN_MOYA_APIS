from django.utils import timezone
from .catalogo import obtener_catalogo_publico, ficha
from .compatibilidad import evaluar_inmueble, PESOS, PESOS_INVERSION, PESOS_AMBAS
from .moneda import obtener_cambio_vigente
from .preguntas import cobertura, aplicables, siguiente, valor


def evaluar_perfil(respuestas, catalogo=None):
    catalogo = catalogo if catalogo is not None else obtener_catalogo_publico()
    cambio = obtener_cambio_vigente()
    opciones, total, excluidas = [], 0, 0
    pendientes_cliente = [pregunta['texto'] for clave, pregunta in aplicables(respuestas).items()
                          if respuestas.get(clave, {}).get('estado') not in ('RESPONDIDA', 'SIN_PREFERENCIA')]
    for inmueble in catalogo:
        total += 1
        ajuste = evaluar_inmueble(respuestas, inmueble, cambio)
        if ajuste['exclusiones']:
            excluidas += 1
            continue
        opcion = {**ficha(inmueble), **ajuste}
        from .moneda import a_cop
        precio_cop = a_cop(inmueble.precio, inmueble.moneda, cambio)
        opcion['precio_comparacion_cop'] = str(precio_cop) if precio_cop is not None else None
        opciones.append(opcion)
    opciones.sort(key=lambda item: (item['afinidad'] is None, -(item['afinidad'] or 0), -item['peso_evaluable'], float(item['precio_comparacion_cop']) if item['precio_comparacion_cop'] is not None else float('inf'), item['id']))
    return {
        'estado': 'CATALOGO_VACIO' if not total else 'SIN_COINCIDENCIAS' if not opciones else 'PRELIMINAR',
        'total_catalogo': total, 'total_opciones': len(opciones), 'excluidas_requisitos': excluidas,
        'cobertura': cobertura(respuestas), 'siguiente_pregunta': siguiente(respuestas),
        'pendientes_cliente': pendientes_cliente, 'opciones': opciones,
        'principal': opciones[0]['id'] if opciones else None,
        'alternativa': next((o['id'] for o in opciones[1:] if o['precio'] != opciones[0]['precio'] or o['ciudad'] != opciones[0]['ciudad']), opciones[1]['id'] if len(opciones) > 1 else None) if opciones else None,
        'pesos': PESOS_INVERSION if valor(respuestas, 'proposito') == 'INVERTIR' else PESOS_AMBAS if valor(respuestas, 'proposito') == 'AMBAS' else PESOS,
        'cambio': {'cop_por_usd': str(cambio.cop_por_usd), 'fecha': cambio.fecha.isoformat(), 'fuente': cambio.fuente} if cambio else None,
        'fecha_corte': timezone.now().isoformat(),
        'aviso': 'Afinidad orientativa, no probabilidad de compra ni aprobación bancaria. Entrega y condiciones comerciales requieren confirmación.',
    }
