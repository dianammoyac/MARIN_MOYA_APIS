import calendar
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext, ROUND_HALF_UP

PESO = Decimal('1')

MESES_ES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
            'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


def texto_mes_ano(fecha):
    return f'{MESES_ES[fecha.month - 1]} de {fecha.year}'


def decimal_campo(valor, nombre, maximo=Decimal('1000000000000')):
    if isinstance(valor, bool) or valor is None:
        raise ValueError(f'{nombre}: indique un valor válido.')
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError):
        raise ValueError(f'{nombre}: indique un número válido.') from None
    if not numero.is_finite() or numero < 0 or numero > maximo:
        raise ValueError(f'{nombre}: valor fuera de rango.')
    return numero


def pesos(valor):
    return str(valor.quantize(PESO, rounding=ROUND_HALF_UP))


def inicial(precio, porcentaje, recursos, meses, aporte, separacion=0, hitos=None,
            separacion_incluida_en_recursos=False):
    """Separa la cuota 0 antes de distribuir el saldo entre meses, sin duplicar recursos."""
    precio = decimal_campo(precio, 'precio')
    porcentaje = decimal_campo(porcentaje, 'porcentaje', Decimal('100'))
    recursos = decimal_campo(recursos, 'recursos')
    meses = decimal_campo(meses, 'meses', Decimal('600'))
    aporte = decimal_campo(aporte, 'aporte_mensual')
    separacion = decimal_campo(separacion, 'separacion')
    if meses != int(meses):
        raise ValueError('meses: indique un entero.')
    meses = int(meses)
    cuota = precio * porcentaje / 100
    if separacion > cuota:
        raise ValueError('separacion: no puede superar la cuota inicial.')
    if separacion_incluida_en_recursos:
        separacion_desde_recursos = min(separacion, recursos)
        faltante_separacion = max(Decimal('0'), separacion - recursos)
        recursos_cuotas = min(max(Decimal('0'), recursos - separacion), max(Decimal('0'), cuota - separacion))
    else:
        separacion_desde_recursos = Decimal('0')
        faltante_separacion = Decimal('0')
        recursos_cuotas = min(recursos, max(Decimal('0'), cuota - separacion))
    por_reunir = max(Decimal('0'), cuota - separacion - recursos_cuotas)
    cuota_mensual = por_reunir / meses if meses else por_reunir
    separacion_aplicada = separacion_desde_recursos if separacion_incluida_en_recursos else separacion
    recursos_totales_aplicables = min(cuota, separacion_aplicada + recursos_cuotas)
    previstos = recursos_totales_aplicables + aporte * meses
    faltante = max(Decimal('0'), cuota - previstos)
    faltante_mensual = max(Decimal('0'), cuota_mensual - aporte) if meses else faltante
    alertas = []
    if faltante_separacion:
        alertas.append({'mes': 0, 'faltante': pesos(faltante_separacion), 'motivo': 'Separación inmediata'})
    if hitos:
        acumulado = Decimal('0')
        for hito in hitos:
            mes = decimal_campo(hito['mes'], 'hito.mes', meses)
            if mes != int(mes):
                raise ValueError('hito.mes: indique un entero.')
            acumulado += decimal_campo(hito['monto'], 'hito.monto')
            disponible = recursos_cuotas + aporte * int(mes)
            if acumulado > disponible:
                alertas.append({'mes': int(mes), 'faltante': pesos(acumulado - disponible), 'motivo': 'Hito de pago'})
    return {'cuota_inicial': pesos(cuota), 'recursos_aplicables': pesos(recursos_cuotas),
            'recursos_declarados': pesos(recursos),
            'recursos_totales_aplicables': pesos(recursos_totales_aplicables),
            'separacion_desde_recursos': pesos(separacion_desde_recursos),
            'faltante_separacion': pesos(faltante_separacion),
            'separacion_incluida_en_recursos': bool(separacion_incluida_en_recursos),
            'saldo_inicial': pesos(max(Decimal('0'), cuota - recursos_totales_aplicables)),
            'cuota_mensual': pesos(cuota_mensual),
            'por_reunir': pesos(por_reunir),
            'recursos_previstos': pesos(previstos), 'faltante': pesos(faltante),
            'faltante_mensual': pesos(faltante_mensual),
            'alertas': alertas, 'separacion_incluida_en_inicial': pesos(separacion),
            'calendario': 'HITOS' if hitos else 'UNIFORME_HIPOTETICO',
            'estado': 'ALCANZABLE_EN_ESCENARIO' if previstos >= cuota and not alertas else 'POR_REVISAR'}


def sumar_meses(fecha, cantidad):
    """Suma meses calendario con tope de fin de mes."""
    total = fecha.year * 12 + (fecha.month - 1) + int(cantidad)
    ano, mes = divmod(total, 12)
    return date(ano, mes + 1, min(fecha.day, calendar.monthrange(ano, mes + 1)[1]))


def meses_restantes(desde, meses_totales, hoy=None):
    """Meses completos que quedan hasta la fecha fija (desde + meses_totales); mínimo 0."""
    if meses_totales is None:
        return None
    hoy = hoy or date.today()
    entrega = sumar_meses(desde, int(meses_totales))
    diferencia = (entrega.year - hoy.year) * 12 + (entrega.month - hoy.month)
    if entrega.day < hoy.day:
        diferencia -= 1
    return max(0, diferencia)


def credito(capital, tasa_ea, anos, administracion=None, seguros=None, cuota_comoda=None):
    capital = decimal_campo(capital, 'capital')
    tasa = decimal_campo(tasa_ea, 'tasa_ea', Decimal('1'))
    plazo = decimal_campo(anos, 'anos', Decimal('50'))
    if plazo == 0 or plazo != int(plazo):
        raise ValueError('anos: indique años enteros mayores que cero.')
    n = int(plazo) * 12
    with localcontext() as contexto:
        contexto.prec = 40
        mensual = (Decimal('1') + tasa) ** (Decimal('1') / Decimal('12')) - 1 if tasa else Decimal('0')
        cuota = capital * mensual / (1 - (1 + mensual) ** (-n)) if mensual and capital else capital / n
        intereses = cuota * n - capital
    administracion = decimal_campo(administracion, 'administracion') if administracion is not None else None
    seguros = decimal_campo(seguros, 'seguros') if seguros is not None else None
    comoda = decimal_campo(cuota_comoda, 'cuota_comoda') if cuota_comoda is not None else None
    return {'capital': pesos(capital), 'tasa_ea': str(tasa), 'anos': int(plazo), 'cuota_capital_intereses': pesos(cuota),
            'intereses_estimados': pesos(intereses), 'administracion': pesos(administracion) if administracion is not None else None,
            'seguros': pesos(seguros) if seguros is not None else None,
            'costo_mensual_conocido': pesos(cuota + (administracion or 0) + (seguros or 0)),
            'total_completo': administracion is not None and seguros is not None,
            'comparacion_cuota_comoda': 'DENTRO' if comoda is not None and cuota <= comoda else 'SUPERA' if comoda is not None else 'PENDIENTE',
            'pendientes': [x for x, falta in [('Seguros', seguros is None), ('Administración', administracion is None), ('Avalúo, gastos notariales y condiciones bancarias', True)] if falta]}
