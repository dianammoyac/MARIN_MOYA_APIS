from django.utils import timezone
from .catalogo import obtener_catalogo_publico, ficha
from .compatibilidad import evaluar_inmueble, PESOS, PESOS_INVERSION, PESOS_AMBAS
from .moneda import obtener_cambio_vigente
from .preguntas import cobertura, aplicables, siguiente, valor
from .ubicaciones import coincide_ubicacion


def evaluar_perfil(respuestas, catalogo=None):
    catalogo = catalogo if catalogo is not None else obtener_catalogo_publico()
    cambio = obtener_cambio_vigente()
    candidatas, inmueble_por_id, total, excluidas = [], {}, 0, 0
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
        candidatas.append(opcion)
        inmueble_por_id[inmueble.pk] = inmueble
    opciones = candidatas
    preferencia_ubicacion = valor(respuestas, 'ciudad')
    ciudad_deseada = preferencia_ubicacion.get('ciudad', '') if isinstance(preferencia_ubicacion, dict) else ''
    departamento_deseado = preferencia_ubicacion.get('departamento', '') if isinstance(preferencia_ubicacion, dict) else ''
    coincidencias_exactas = None
    if ciudad_deseada:
        coincidencias_exactas = [o for o in candidatas
                                 if coincide_ubicacion(inmueble_por_id[o['id']], departamento_deseado, ciudad_deseada)]
        exactas_ids = {o['id'] for o in coincidencias_exactas}
        mismo_departamento = [o for o in candidatas if o['id'] not in exactas_ids and
                              coincide_ubicacion(inmueble_por_id[o['id']], departamento_deseado, '')]
        for opcion in coincidencias_exactas:
            opcion['tipo_coincidencia_ubicacion'] = 'EXACTA'
        for opcion in mismo_departamento:
            opcion['tipo_coincidencia_ubicacion'] = 'ALTERNATIVA_DEPARTAMENTO'
        opciones = coincidencias_exactas + mismo_departamento
    opciones.sort(key=lambda item: (item.get('tipo_coincidencia_ubicacion') == 'ALTERNATIVA_DEPARTAMENTO',
                                    item['afinidad'] is None, -(item['afinidad'] or 0), -item['peso_evaluable'],
                                    float(item['precio_comparacion_cop']) if item['precio_comparacion_cop'] is not None else float('inf'), item['id']))
    ubicacion_exacta = bool(coincidencias_exactas) if coincidencias_exactas is not None else None
    solo_alternativas_ubicacion = bool(opciones) and coincidencias_exactas is not None and not coincidencias_exactas
    sin_alternativas_ubicacion = not opciones and excluidas == 0 and coincidencias_exactas is not None
    financiero = valor(respuestas, 'perfil_financiero')
    return {
        'estado': 'CATALOGO_VACIO' if not total else 'SIN_COINCIDENCIAS_UBICACION' if sin_alternativas_ubicacion else 'ALTERNATIVAS_UBICACION' if solo_alternativas_ubicacion else 'SIN_COINCIDENCIAS' if not opciones else 'PRELIMINAR',
        'total_catalogo': total, 'total_opciones': len(opciones), 'excluidas_requisitos': excluidas,
        'coincidencias_ubicacion': len(coincidencias_exactas) if coincidencias_exactas is not None else None,
        'alternativas_mismo_departamento': len(opciones) - len(coincidencias_exactas) if coincidencias_exactas is not None else 0,
        'ubicacion_deseada': {'ciudad': ciudad_deseada, 'departamento': departamento_deseado} if ciudad_deseada else None,
        'cobertura': cobertura(respuestas), 'siguiente_pregunta': siguiente(respuestas),
        'pendientes_cliente': pendientes_cliente, 'opciones': opciones,
        'resumen_financiero': {'aportantes': 1 if financiero['modalidad'] == 'SOLO' else 2,
                              'ingresos_total': financiero['ingresos_total'],
                              'obligaciones_total': financiero['obligaciones_total']} if financiero else None,
        'principal': next((o['id'] for o in opciones if o.get('tipo_coincidencia_ubicacion') != 'ALTERNATIVA_DEPARTAMENTO'), opciones[0]['id'] if opciones and coincidencias_exactas is None else None),
        'alternativa': next((o['id'] for o in opciones[1:] if o.get('tipo_coincidencia_ubicacion') != 'ALTERNATIVA_DEPARTAMENTO' and (o['precio'] != opciones[0]['precio'] or o['ciudad'] != opciones[0]['ciudad'])), None) if opciones else None,
        'pesos': PESOS_INVERSION if valor(respuestas, 'proposito') == 'INVERTIR' else PESOS_AMBAS if valor(respuestas, 'proposito') == 'AMBAS' else PESOS,
        'cambio': {'cop_por_usd': str(cambio.cop_por_usd), 'fecha': cambio.fecha.isoformat(), 'fuente': cambio.fuente} if cambio else None,
        'fecha_corte': timezone.now().isoformat(),
        'aviso': 'Afinidad orientativa, no probabilidad de compra ni aprobación bancaria. Entrega y condiciones comerciales requieren confirmación.',
    }
