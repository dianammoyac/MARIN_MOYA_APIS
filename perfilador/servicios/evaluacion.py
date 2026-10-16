from decimal import Decimal

from django.utils import timezone
from .catalogo import obtener_catalogo_publico, ficha
from .compatibilidad import evaluar_inmueble, PESOS, PESOS_INVERSION, PESOS_AMBAS
from .moneda import obtener_cambio_vigente
from .preguntas import cobertura, aplicables, siguiente, valor
from .ubicaciones import coincide_ubicacion

# Margen interno: una alternativa solo puede superar el presupuesto en esta
# proporción. Nunca se muestra ni se envía al cliente.
MARGEN_PRECIO_ALTERNATIVA = Decimal('1.20')



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
    exactas = [o for o in candidatas if not o['incumplimientos']]
    exactas_ids = {o['id'] for o in exactas}
    resto = [o for o in candidatas if o['id'] not in exactas_ids]
    alternativas_precio = []
    if valor(respuestas, 'presupuesto') is not None:
        for opcion in resto:
            if [c for c in opcion['incumplimientos'] if c != 'presupuesto']:
                continue
            razon_precio = next((r for r in opcion['razones'] if r['criterio'] == 'presupuesto'), None)
            if not razon_precio or not razon_precio['datos']:
                continue
            precio = Decimal(str(razon_precio['datos']['precio']))
            maximo = Decimal(str(razon_precio['datos']['presupuesto']))
            if maximo > 0 and precio <= maximo * MARGEN_PRECIO_ALTERNATIVA:
                opcion['es_alternativa_precio'] = True
                opcion['exceso_presupuesto'] = str(precio - maximo)
                alternativas_precio.append(opcion)
    preferencia_ubicacion = valor(respuestas, 'ciudad')
    ciudad_deseada = preferencia_ubicacion.get('ciudad', '') if isinstance(preferencia_ubicacion, dict) else ''
    departamento_deseado = preferencia_ubicacion.get('departamento', '') if isinstance(preferencia_ubicacion, dict) else ''
    if ciudad_deseada:
        alternativas_precio = [o for o in alternativas_precio
                               if coincide_ubicacion(inmueble_por_id[o['id']], departamento_deseado, ciudad_deseada)]
        for opcion in alternativas_precio:
            opcion['tipo_coincidencia_ubicacion'] = 'EXACTA'
    alternativas_ids = {o['id'] for o in alternativas_precio}
    # Las que están en tu ciudad pero no cumplen todo NO se muestran:
    # solo se cuenta cuántas hay para el mensaje. Ver botón de precio aparte.
    cercanas = 0
    if ciudad_deseada:
        cercanas = sum(1 for o in resto if o['id'] not in alternativas_ids
                       and coincide_ubicacion(inmueble_por_id[o['id']], departamento_deseado, ciudad_deseada))
    opciones = exactas
    coincidencias_exactas = None
    mismo_departamento = []
    if ciudad_deseada:
        coincidencias_exactas = [o for o in exactas
                                 if coincide_ubicacion(inmueble_por_id[o['id']], departamento_deseado, ciudad_deseada)]
        mostrar_ids = {o['id'] for o in coincidencias_exactas}
        mismo_departamento = [o for o in resto if o['id'] not in mostrar_ids
                              and o['id'] not in alternativas_ids
                              and 'presupuesto' not in o['incumplimientos']
                              and not coincide_ubicacion(inmueble_por_id[o['id']], departamento_deseado, ciudad_deseada)
                              and coincide_ubicacion(inmueble_por_id[o['id']], departamento_deseado, '')]
        for opcion in coincidencias_exactas:
            opcion['tipo_coincidencia_ubicacion'] = 'EXACTA'
        for opcion in mismo_departamento:
            opcion['tipo_coincidencia_ubicacion'] = 'ALTERNATIVA_DEPARTAMENTO'
        opciones = coincidencias_exactas + mismo_departamento
    opciones.sort(key=lambda item: (item.get('tipo_coincidencia_ubicacion') == 'ALTERNATIVA_DEPARTAMENTO',
                                    item['afinidad'] is None, -(item['afinidad'] or 0), -item['peso_evaluable'],
                                    float(item['precio_comparacion_cop']) if item['precio_comparacion_cop'] is not None else float('inf'), item['id']))
    hay_alternativas_precio = bool(alternativas_precio)
    hay_cercanas = bool(cercanas)
    hay_dept = bool(mismo_departamento)
    hay_exactas = bool(exactas)
    solo_alternativas_ubicacion = hay_dept and not hay_exactas and not hay_cercanas and not hay_alternativas_precio
    sin_alternativas_ubicacion = (not opciones and not hay_cercanas and not hay_dept
                                  and not hay_alternativas_precio
                                  and excluidas == 0 and coincidencias_exactas is not None)
    sin_exactas = not hay_exactas and (hay_cercanas or hay_dept)
    financiero = valor(respuestas, 'perfil_financiero')
    exactas_ordenadas = [o for o in opciones if o['id'] in exactas_ids]
    principal = exactas_ordenadas[0]['id'] if exactas_ordenadas else None
    alternativa = next((o['id'] for o in exactas_ordenadas[1:]
                        if o['precio'] != exactas_ordenadas[0]['precio']
                        or o['ciudad'] != exactas_ordenadas[0]['ciudad']), None) if exactas_ordenadas else None
    return {
        'estado': 'CATALOGO_VACIO' if not total else 'SIN_COINCIDENCIAS_UBICACION' if sin_alternativas_ubicacion else 'ALTERNATIVAS_UBICACION' if solo_alternativas_ubicacion else 'SIN_COINCIDENCIA_EXACTA' if sin_exactas else 'SIN_COINCIDENCIAS' if not opciones else 'PRELIMINAR',
        'total_catalogo': total, 'total_opciones': len(opciones), 'excluidas_requisitos': excluidas,
        'hay_alternativas_precio': hay_alternativas_precio,
        'alternativas_precio': alternativas_precio,
        'cercanas_ciudad': cercanas,
        'coincidencias_ubicacion': len(coincidencias_exactas) if coincidencias_exactas is not None else None,
        'alternativas_mismo_departamento': len(mismo_departamento),
        'ubicacion_deseada': {'ciudad': ciudad_deseada, 'departamento': departamento_deseado} if ciudad_deseada else None,
        'cobertura': cobertura(respuestas), 'siguiente_pregunta': siguiente(respuestas),
        'pendientes_cliente': pendientes_cliente, 'opciones': opciones,
        'resumen_financiero': {'aportantes': 1 if financiero['modalidad'] == 'SOLO' else 2,
                              'ingresos_total': financiero['ingresos_total'],
                              'obligaciones_total': financiero['obligaciones_total']} if financiero else None,
        'principal': principal,
        'alternativa': alternativa,
        'pesos': PESOS_INVERSION if valor(respuestas, 'proposito') == 'INVERTIR' else PESOS_AMBAS if valor(respuestas, 'proposito') == 'AMBAS' else PESOS,
        'cambio': {'cop_por_usd': str(cambio.cop_por_usd), 'fecha': cambio.fecha.isoformat(), 'fuente': cambio.fuente} if cambio else None,
        'fecha_corte': timezone.now().isoformat(),
        'aviso': 'Afinidad orientativa, no probabilidad de compra ni aprobación bancaria. Entrega y condiciones comerciales requieren confirmación.',
    }
