from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from .ubicaciones import obtener_ubicaciones

VERSION = '4'
ESTADOS = ('RESPONDIDA', 'SIN_PREFERENCIA', 'NO_SE', 'PREFIERO_DESPUES', 'OMITIDA')
FUENTES = ('CLIENTE', 'ACOMPANAMIENTO')

# Los pesos informativos NO son los pesos de compatibilidad.
PREGUNTAS = {
    'proposito': {'texto': '¿Busca vivienda para vivir, invertir o ambas?', 'tipo': 'opcion', 'opciones': ['VIVIR', 'INVERTIR', 'AMBAS'], 'peso': 10, 'obligatoria': True, 'alternativas': []},
    'objetivo_inversion': {'texto': '¿Qué busca principalmente con esta inversión?', 'tipo': 'opcion', 'opciones': ['INGRESOS_ARRIENDO', 'RENTA_CORTA', 'VALORIZACION', 'REVENTA', 'DIVERSIFICACION'], 'peso': 8, 'obligatoria': True, 'alternativas': ['NO_SE']},
    'horizonte_inversion': {'texto': '¿Por cuánto tiempo considera mantener la inversión?', 'tipo': 'opcion', 'opciones': ['MENOS_3', 'DE_3_A_7', 'MAS_7'], 'peso': 6, 'obligatoria': True, 'alternativas': ['NO_SE']},
    'prioridad_inversion': {'texto': '¿Qué prioriza al elegir una inversión inmobiliaria?', 'tipo': 'opcion', 'opciones': ['MENOR_INVERSION', 'UBICACION', 'ESPACIO', 'AUN_NO_SE'], 'peso': 5, 'obligatoria': True, 'alternativas': ['NO_SE']},
    'experiencia_inversion': {'texto': '¿Es su primera inversión inmobiliaria?', 'tipo': 'opcion', 'opciones': ['PRIMERA', 'YA_INVIERTO'], 'peso': 3, 'obligatoria': False, 'alternativas': ['NO_SE', 'PREFIERO_DESPUES', 'OMITIDA']},
    'gestion_inversion': {'texto': '¿Cómo piensa administrar la propiedad?', 'tipo': 'opcion', 'opciones': ['DIRECTA', 'DELEGADA', 'POR_DEFINIR'], 'peso': 3, 'obligatoria': False, 'alternativas': ['NO_SE', 'PREFIERO_DESPUES', 'OMITIDA']},
    'ciudad': {'texto': '¿En qué departamento y ciudad desea buscar?', 'tipo': 'ubicacion', 'peso': 10, 'obligatoria': True, 'alternativas': ['SIN_PREFERENCIA', 'NO_SE']},
    'entrega': {'texto': '¿En cuántos meses desea que le entreguen el inmueble? (0 = entrega inmediata)', 'tipo': 'numero', 'peso': 6, 'obligatoria': True, 'alternativas': ['NO_SE']},
    'habitaciones': {'texto': '¿Cuántas habitaciones necesita?', 'tipo': 'numero', 'peso': 10, 'obligatoria': True, 'alternativas': ['NO_SE']},
    'familia': {'texto': 'Si aún no sabe cuántas habitaciones necesita, ¿cómo está conformado su hogar?', 'tipo': 'familia', 'peso': 8, 'obligatoria': True, 'alternativas': ['NO_SE']},
    'area_m2': {'texto': '¿Qué área mínima busca? (m²)', 'tipo': 'numero', 'peso': 8, 'obligatoria': True, 'alternativas': ['NO_SE']},
    'parqueadero': {'texto': '¿Necesita parqueadero?', 'tipo': 'opcion', 'opciones': ['SI', 'NO'], 'peso': 6, 'obligatoria': True, 'alternativas': ['SIN_PREFERENCIA', 'NO_SE']},
    'presupuesto': {'texto': '¿Cuál es su presupuesto máximo?', 'tipo': 'dinero', 'peso': 12, 'obligatoria': True, 'alternativas': []},
    'pago': {'texto': '¿Cómo piensa pagar?', 'tipo': 'opcion', 'opciones': ['CONTADO', 'CREDITO'], 'peso': 8, 'obligatoria': True, 'alternativas': ['NO_SE']},
    'recursos': {'texto': '¿Con cuánto cuenta hoy para la compra o cuota inicial?', 'tipo': 'dinero_perfil', 'peso': 8, 'obligatoria': True, 'alternativas': ['NO_SE']},
    'fuentes_recursos': {'texto': '¿Dónde se encuentran esos recursos? Escriba el monto en cada opción', 'tipo': 'montos', 'peso': 5, 'obligatoria': True, 'alternativas': ['NO_SE']},
    'aporte_mensual': {'texto': 'Aparte de lo que ya tiene, ¿cuánto podría aportar cada mes hasta recibir el inmueble?', 'tipo': 'dinero_perfil', 'peso': 6, 'obligatoria': True, 'alternativas': ['NO_SE']},
    'ingresos': {'texto': '¿Cuáles son los ingresos mensuales de su hogar?', 'tipo': 'dinero_perfil', 'peso': 4, 'obligatoria': False, 'alternativas': ['NO_SE', 'PREFIERO_DESPUES']},
    'obligaciones': {'texto': '¿Cuánto paga al mes en otras obligaciones?', 'tipo': 'dinero_perfil', 'peso': 4, 'obligatoria': False, 'alternativas': ['NO_SE', 'PREFIERO_DESPUES']},
}


def valor(respuestas, clave):
    dato = respuestas.get(clave, {})
    return dato.get('valor') if dato.get('estado') == 'RESPONDIDA' else None


def aplicables(respuestas):
    proposito = valor(respuestas, 'proposito')
    recursos = valor(respuestas, 'recursos')
    mostrar_ayuda = respuestas.get('aporte_mensual', {}).get('estado') == 'NO_SE'
    return {clave: pregunta for clave, pregunta in PREGUNTAS.items()
            if (clave != 'familia' or (proposito in ('VIVIR', 'AMBAS') and respuestas.get('habitaciones', {}).get('estado') == 'NO_SE'))
            and (clave not in ('objetivo_inversion', 'horizonte_inversion', 'prioridad_inversion', 'experiencia_inversion', 'gestion_inversion') or proposito in ('INVERTIR', 'AMBAS'))
            and (clave != 'fuentes_recursos' or recursos is not None and Decimal(str(recursos)) > 0)
            and (clave not in ('ingresos', 'obligaciones') or mostrar_ayuda)}


def pendientes_obligatorias(respuestas):
    return [clave for clave, pregunta in aplicables(respuestas).items()
            if pregunta['obligatoria'] and respuestas.get(clave, {}).get('estado') not in ('RESPONDIDA', 'SIN_PREFERENCIA', 'NO_SE')]


def numero_positivo(bruto, clave, permitir_cero=True):
    if isinstance(bruto, bool) or bruto is None:
        raise ValueError(f'{clave}: indique un número válido.')
    try:
        numero = Decimal(str(bruto))
    except (InvalidOperation, ValueError):
        raise ValueError(f'{clave}: indique un número válido.') from None
    if not numero.is_finite() or numero < 0 or (not permitir_cero and numero == 0) or numero > Decimal('1000000000000'):
        raise ValueError(f'{clave}: valor fuera de rango.')
    return numero


def normalizar_respuestas(datos, actuales):
    if not isinstance(datos, dict) or not datos:
        raise ValueError('Envíe al menos una respuesta.')
    resultado = dict(actuales)
    moneda_anterior = valor(actuales, 'presupuesto')
    moneda_anterior = moneda_anterior.get('moneda') if isinstance(moneda_anterior, dict) else None
    for clave, entrada in datos.items():
        if clave not in PREGUNTAS or not isinstance(entrada, dict):
            raise ValueError(f'{clave}: pregunta o formato inválido.')
        pregunta = PREGUNTAS[clave]
        estado = entrada.get('estado')
        if estado not in ESTADOS or (estado != 'RESPONDIDA' and estado not in pregunta['alternativas']):
            raise ValueError(f'{clave}: elija una respuesta válida para esta pregunta.')
        fuente = entrada.get('fuente', 'CLIENTE')
        if fuente not in FUENTES:
            raise ValueError(f'{clave}: fuente inválida.')
        indispensable = entrada.get('indispensable', False)
        if type(indispensable) is not bool or (indispensable and clave not in {'ciudad', 'habitaciones', 'area_m2', 'parqueadero', 'presupuesto', 'entrega'}):
            raise ValueError(f'{clave}: requisito indispensable inválido.')
        dato = {'estado': estado, 'fuente': fuente, 'indispensable': indispensable if estado == 'RESPONDIDA' else False}
        if estado == 'RESPONDIDA':
            bruto = entrada.get('valor')
            tipo = pregunta['tipo']
            if tipo == 'opcion':
                if bruto not in pregunta['opciones']:
                    raise ValueError(f'{clave}: elija una opción válida.')
                dato['valor'] = bruto
            elif tipo == 'ubicacion':
                if not isinstance(bruto, dict) or set(bruto) != {'departamento', 'ciudad'}:
                    raise ValueError('ciudad: elija departamento y ciudad, o indique que no tiene preferencia de ciudad.')
                dep, ciudad = bruto['departamento'], bruto['ciudad']
                if not isinstance(dep, str) or not dep.strip() or len(dep) > 60 or not isinstance(ciudad, str) or len(ciudad) > 60:
                    raise ValueError('ciudad: elija un departamento y, si desea, una ciudad.')
                ubicaciones = obtener_ubicaciones()
                if dep not in ubicaciones or (ciudad and ciudad not in ubicaciones[dep]):
                    raise ValueError('ciudad: elija un departamento y ciudad válidos del listado.')
                dato['valor'] = {'departamento': dep.strip(), 'ciudad': ciudad.strip()}
            elif tipo == 'familia':
                if not isinstance(bruto, dict) or set(bruto) != {'adultos', 'menores', 'adultos_mayores'}:
                    raise ValueError('familia: indique adultos, menores y adultos mayores.')
                composicion = {}
                for campo in ('adultos', 'menores', 'adultos_mayores'):
                    numero = numero_positivo(bruto[campo], campo)
                    if numero != numero.to_integral_value() or numero > 20:
                        raise ValueError(f'familia.{campo}: indique un entero de 0 a 20.')
                    composicion[campo] = int(numero)
                if sum(composicion.values()) < 1:
                    raise ValueError('familia: indique al menos una persona.')
                dato['valor'] = composicion
            elif tipo == 'montos':
                if isinstance(bruto, dict) and set(bruto) == {'montos', 'porcentajes', 'moneda', 'total'}:
                    bruto = bruto['montos']
                if not isinstance(bruto, dict) or set(bruto) != {'cesantias', 'cdt', 'cuenta', 'otros'}:
                    raise ValueError('fuentes_recursos: indique el monto en cesantías, CDT, cuenta y otros.')
                if isinstance(datos.get('recursos'), dict) and datos['recursos'].get('estado') == 'RESPONDIDA':
                    total_bruto = datos['recursos'].get('valor')
                else:
                    total_bruto = valor(resultado, 'recursos')
                if total_bruto is None:
                    raise ValueError('fuentes_recursos: primero indique con cuánto cuenta para la compra.')
                total = numero_positivo(total_bruto, 'recursos', permitir_cero=False)
                montos = {}
                for campo in ('cesantias', 'cdt', 'cuenta', 'otros'):
                    monto = numero_positivo(bruto[campo], f'fuentes_recursos.{campo}')
                    if monto != monto.to_integral_value():
                        raise ValueError(f'fuentes_recursos.{campo}: indique un valor entero, sin centavos.')
                    montos[campo] = monto
                suma = sum(montos.values())
                if suma != total:
                    raise ValueError(f'fuentes_recursos: los montos deben sumar exactamente el total declarado ({total}). Ahora suman {suma}.')
                presupuesto = valor(resultado, 'presupuesto')
                moneda = presupuesto.get('moneda', 'COP') if isinstance(presupuesto, dict) else 'COP'
                porcentajes, acumulado = {}, Decimal('0')
                for campo in ('cesantias', 'cdt', 'cuenta'):
                    pct = (montos[campo] * 100 / total).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
                    porcentajes[campo] = pct
                    acumulado += pct
                porcentajes['otros'] = Decimal('100.0') - acumulado
                dato['valor'] = {'montos': {campo: str(monto) for campo, monto in montos.items()},
                                 'porcentajes': {campo: str(pct) for campo, pct in porcentajes.items()},
                                 'moneda': moneda, 'total': str(total)}
            elif tipo == 'dinero':
                if not isinstance(bruto, dict) or set(bruto) != {'monto', 'moneda'} or bruto['moneda'] not in ('COP', 'USD'):
                    raise ValueError('presupuesto: indique monto y moneda COP o USD.')
                dato['valor'] = {'monto': str(numero_positivo(bruto['monto'], 'presupuesto', permitir_cero=False)), 'moneda': bruto['moneda']}
            else:
                numero = numero_positivo(bruto, clave)
                if clave in {'habitaciones', 'entrega'} and (numero != numero.to_integral_value() or numero > 100):
                    raise ValueError(f'{clave}: indique un número entero válido.')
                dato['valor'] = str(numero)
        resultado[clave] = dato
    moneda_nueva = valor(resultado, 'presupuesto')
    moneda_nueva = moneda_nueva.get('moneda') if isinstance(moneda_nueva, dict) else None
    if moneda_anterior and moneda_nueva and moneda_nueva != moneda_anterior:
        for clave in ('recursos', 'fuentes_recursos', 'aporte_mensual', 'ingresos', 'obligaciones'):
            if clave not in datos:
                resultado.pop(clave, None)
    if (isinstance(datos.get('recursos'), dict) and datos['recursos'].get('estado') == 'RESPONDIDA'
            and valor(actuales, 'recursos') is not None
            and str(datos['recursos'].get('valor')) != str(valor(actuales, 'recursos'))
            and 'fuentes_recursos' not in datos):
        resultado.pop('fuentes_recursos', None)
    # No admitir preguntas de la rama equivocada (tampoco datos heredados al cambiar de propósito).
    aplicadas = set(aplicables(resultado))
    for clave in list(resultado):
        if clave not in aplicadas:
            if clave in datos:
                raise ValueError(f'{clave}: esta pregunta no aplica a sus respuestas actuales.')
            resultado.pop(clave)
    return resultado


def cobertura(respuestas):
    preguntas = aplicables(respuestas)
    total = sum(p['peso'] for p in preguntas.values())
    contestadas = sum(p['peso'] for clave, p in preguntas.items()
                      if respuestas.get(clave, {}).get('estado') in ('RESPONDIDA', 'SIN_PREFERENCIA'))
    return round(100 * contestadas / total) if total else 0


def siguiente(respuestas):
    return next((clave for clave in aplicables(respuestas) if clave not in respuestas), None)
