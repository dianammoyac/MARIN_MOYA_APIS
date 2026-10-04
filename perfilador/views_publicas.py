"""Recorrido público sin historial: solo una solicitud consentida crea registros."""

import re
import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from .models import EvaluacionPerfil, Perfilacion, ReferenciaFinanciera, SolicitudAsesoria
from .servicios.catalogo import obtener_catalogo_publico
from .servicios.evaluacion import evaluar_perfil
from .servicios.financiacion import credito, decimal_campo, inicial, meses_restantes, sumar_meses
from .servicios.moneda import a_cop, obtener_cambio_vigente
from .servicios.preguntas import PREGUNTAS, VERSION, normalizar_respuestas, pendientes_obligatorias, valor
from .views import datos, error, limite


def validar_respuestas(entrada, completas=False):
    if entrada.get('version') != VERSION:
        raise ValueError('El cuestionario cambió. Recarga la página para empezar de nuevo.')
    bruto = entrada.get('respuestas', {})
    if not isinstance(bruto, dict):
        raise ValueError('respuestas: envíe un objeto de respuestas.')
    respuestas = normalizar_respuestas(bruto, {}) if bruto else {}
    if completas:
        pendientes = pendientes_obligatorias(respuestas)
        if pendientes:
            raise ValueError('Responda primero las preguntas necesarias: ' + ', '.join(PREGUNTAS[c]['texto'] for c in pendientes))
    return respuestas


@csrf_protect
@require_http_methods(['POST'])
def guardar_respuesta(request):
    try:
        entrada = datos(request)
        anteriores = validar_respuestas(entrada)
        clave = entrada.get('clave')
        if clave not in PREGUNTAS:
            raise ValueError('Pregunta inválida.')
        nuevas = normalizar_respuestas({clave: entrada.get('respuesta')}, anteriores)
    except ValueError as exc:
        return error(str(exc), 409 if 'Recarga la página' in str(exc) else 400)
    return JsonResponse({'respuestas': nuevas})


@csrf_protect
@require_http_methods(['POST'])
def evaluar(request):
    if limite(request, 'evaluar'):
        return error('Demasiadas evaluaciones. Inténtelo más tarde.', 429)
    try:
        respuestas = validar_respuestas(datos(request), completas=True)
    except ValueError as exc:
        return error(str(exc), 409 if 'Recarga la página' in str(exc) else 400)
    return JsonResponse(evaluar_perfil(respuestas))


def calcular_escenario(respuestas, entrada, inmueble):
    if inmueble.moneda not in ('COP', 'USD') or inmueble.precio <= 0:
        raise ValueError('Se requiere un precio positivo en COP o USD para simular.')
    if entrada.get('precio_visto') is not None and str(inmueble.precio) != str(entrada['precio_visto']):
        raise ValueError('El precio del inmueble cambió. Recalcule las recomendaciones.')
    porcentaje = entrada.get('porcentaje_inicial')
    if entrada.get('porcentaje_es_proyecto') == 'SI' and inmueble.porcentaje_inicial_exigido is not None:
        porcentaje = inmueble.porcentaje_inicial_exigido
        origen_porcentaje = 'EXIGIDO_PROYECTO'
    elif porcentaje is None and inmueble.porcentaje_inicial_exigido is not None:
        porcentaje = inmueble.porcentaje_inicial_exigido
        origen_porcentaje = 'EXIGIDO_PROYECTO'
    else:
        origen_porcentaje = 'HIPOTESIS'
    if porcentaje is None:
        raise ValueError('porcentaje_inicial: indique un porcentaje hipotético.')
    moneda_perfil = valor(respuestas, 'presupuesto')['moneda']
    cambio = obtener_cambio_vigente() if moneda_perfil == 'USD' or inmueble.moneda == 'USD' else None
    if (moneda_perfil == 'USD' or inmueble.moneda == 'USD') and not cambio:
        raise ValueError('Falta una referencia COP/USD vigente para esta simulación.')
    precio_cop = a_cop(inmueble.precio, inmueble.moneda, cambio)
    recursos = entrada.get('recursos', valor(respuestas, 'recursos'))
    aporte = entrada.get('aporte_mensual', valor(respuestas, 'aporte_mensual'))
    uso_guia = False
    if aporte is None and entrada.get('usar_aporte_orientativo') is True:
        ingresos = valor(respuestas, 'ingresos')
        if ingresos is None:
            raise ValueError('Declare ingresos del hogar para explorar el ejemplo del 30 %.')
        aporte = str(Decimal(ingresos) * Decimal('0.30'))
        uso_guia = True
    if recursos is None or aporte is None:
        raise ValueError('Indique recursos y aporte mensual para simular la cuota inicial.')
    modalidad = getattr(inmueble, 'modalidad_entrega', 'TERMINADO') or 'TERMINADO'
    meses_inmueble = getattr(inmueble, 'meses_entrega', None)
    entrega_fija = None
    if modalidad == 'SOBRE_PLANOS' and meses_inmueble is not None:
        entrega_fija = sumar_meses(inmueble.fecha_publicacion, int(meses_inmueble))
        meses = meses_restantes(inmueble.fecha_publicacion, int(meses_inmueble))
        origen_meses = 'REMANENTE_EN_VIVO'
    elif modalidad == 'TERMINADO':
        meses = 0
        origen_meses = 'ENTREGA_INMUEBLE'
    else:
        deseo = valor(respuestas, 'entrega')
        if deseo is None:
            raise ValueError('La entrega del inmueble está por confirmar; indique los meses deseados para simular.')
        meses = int(Decimal(str(deseo)))
        origen_meses = 'DESEO_CLIENTE_POR_CONFIRMAR'
    separacion = entrada.get('separacion')
    if entrada.get('separacion_es_proyecto') == 'SI' and inmueble.valor_separacion is not None:
        separacion = inmueble.valor_separacion
        origen_separacion = 'EXIGIDO_PROYECTO'
        separacion_cop = a_cop(separacion, inmueble.moneda, cambio)
    elif separacion is None and inmueble.valor_separacion is not None:
        separacion = inmueble.valor_separacion
        origen_separacion = 'EXIGIDO_PROYECTO'
        separacion_cop = a_cop(separacion, inmueble.moneda, cambio)
    else:
        origen_separacion = 'HIPOTESIS'
        separacion_cop = a_cop(separacion if separacion is not None else 0, moneda_perfil, cambio)
    separacion_cop = decimal_campo(separacion_cop, 'separacion')
    recursos_cop = decimal_campo(a_cop(recursos, moneda_perfil, cambio), 'recursos')
    incluye_separacion = entrada.get('separacion_incluida_en_recursos')
    if separacion_cop > 0 and recursos_cop > 0 and incluye_separacion not in ('SI', 'NO'):
        raise ValueError('Indique si los recursos disponibles incluyen el dinero de la separación.')
    # Sin recursos no se puede dar la separación por cubierta con dinero aparte.
    if separacion_cop > 0 and recursos_cop == 0:
        incluye_separacion = 'SI'
    plan = inicial(precio_cop, porcentaje, recursos_cop,
                   meses, a_cop(aporte, moneda_perfil, cambio),
                   separacion_cop, separacion_incluida_en_recursos=(incluye_separacion == 'SI'))
    pago = valor(respuestas, 'pago')
    if pago == 'CONTADO' and decimal_campo(porcentaje, 'porcentaje_inicial', Decimal('100')) != 100:
        raise ValueError('Para compra de contado indique el 100 % del precio.')
    prestamo = None
    referencia = None
    if entrada.get('referencia') is not None:
        referencia = get_object_or_404(ReferenciaFinanciera, pk=entrada['referencia'], activa=True)
        if referencia.vence < timezone.localdate():
            raise ValueError('La referencia financiera está vencida.')
    if pago != 'CONTADO' and (entrada.get('tasa_ea') is not None or referencia):
        tasa = referencia.tasa_ea if referencia else decimal_campo(entrada['tasa_ea'], 'tasa_ea', Decimal('1'))
        anos = decimal_campo(entrada.get('anos', 20), 'anos', Decimal('50'))
        if referencia and not referencia.plazo_minimo <= anos <= referencia.plazo_maximo:
            raise ValueError('anos: plazo fuera de la referencia seleccionada.')
        capital = max(Decimal('0'), precio_cop * (100 - decimal_campo(porcentaje, 'porcentaje_inicial', Decimal('100'))) / 100)
        prestamo = credito(capital, tasa, anos, administracion=inmueble.administracion)
        prestamo['origen_tasa'] = 'REFERENCIA_VIGENTE' if referencia else 'HIPOTESIS_PERSONALIZADA'
        if referencia:
            prestamo['referencia'] = {'entidad': referencia.entidad, 'producto': referencia.producto,
                                     'verificada': referencia.verificada.isoformat(), 'vence': referencia.vence.isoformat(),
                                     'fuente': referencia.fuente,
                                     'porcentaje_maximo': str(referencia.porcentaje_maximo) if referencia.porcentaje_maximo else None}
            if referencia.porcentaje_maximo is not None and capital * 100 > precio_cop * referencia.porcentaje_maximo:
                prestamo['pendientes'].append('Crédito necesario supera el máximo orientativo de la referencia')
        prestamo['capacidad_pago'] = 'PENDIENTE_VERIFICACION'
    resto_pct = Decimal('100') - decimal_campo(porcentaje, 'porcentaje_inicial', Decimal('100'))
    saldo_financiar = precio_cop * resto_pct / 100
    return {'inicial': plan, 'credito': prestamo, 'producto': pago or 'NO_DECLARADO',
            'saldo_a_financiar': str(saldo_financiar), 'porcentaje_restante': str(resto_pct),
            'meses_inicial': str(meses), 'origen_meses_inicial': origen_meses,
            'fecha_entrega_fija': entrega_fija.isoformat() if entrega_fija else None,
            'origen_porcentaje_inicial': origen_porcentaje, 'origen_separacion': origen_separacion,
            'precio_referencia': str(inmueble.precio), 'moneda_precio': inmueble.moneda,
            'precio_referencia_cop': str(precio_cop), 'moneda_perfil': moneda_perfil,
            'cambio': {'cop_por_usd': str(cambio.cop_por_usd), 'fecha': cambio.fecha.isoformat(), 'fuente': cambio.fuente} if cambio else None,
            'aporte_orientativo_30': uso_guia, 'obligaciones_declaradas': valor(respuestas, 'obligaciones'),
            'porcentaje_inicial': str(porcentaje), 'condicion_inicial': 'HIPOTESIS_NO_CONFIRMADA',
            'aviso': 'No es una aprobación bancaria. Seguros, gastos y condiciones requieren confirmación.'}


@csrf_protect
@require_http_methods(['POST'])
def simular(request):
    if limite(request, 'simular'):
        return error('Demasiadas simulaciones. Inténtelo más tarde.', 429)
    try:
        entrada = datos(request)
        respuestas = validar_respuestas(entrada, completas=True)
        inmueble = get_object_or_404(obtener_catalogo_publico(), pk=entrada.get('inmueble'))
        if inmueble.pk not in {o['id'] for o in evaluar_perfil(respuestas)['opciones']}:
            raise ValueError('Este inmueble no coincide con los requisitos declarados.')
        resultado = calcular_escenario(respuestas, entrada, inmueble)
    except (ValueError, TypeError) as exc:
        return error(str(exc), 409 if 'Recalcule' in str(exc) or 'Recarga la página' in str(exc) else 400)
    return JsonResponse({'resultado': resultado})


@csrf_protect
@require_http_methods(['POST'])
def solicitar(request):
    if limite(request, 'solicitar'):
        return error('Demasiados intentos. Inténtelo más tarde.', 429)
    try:
        entrada = datos(request)
        clave = uuid.UUID(str(entrada.get('clave_idempotencia')))
        anterior = SolicitudAsesoria.objects.filter(clave_idempotencia=clave).first()
        if anterior:
            return JsonResponse({'solicitud': str(anterior.id), 'estado': 'REGISTRADA'})
        respuestas = validar_respuestas(entrada, completas=True)
        nombre, telefono, correo = entrada.get('nombre', ''), entrada.get('telefono', ''), entrada.get('correo', '')
        if not isinstance(nombre, str) or not 2 <= len(nombre.strip()) <= 120:
            raise ValueError('nombre: indique su nombre.')
        if not isinstance(telefono, str) or not isinstance(correo, str) or len(telefono) > 40 or len(correo) > 254:
            raise ValueError('Contacto inválido.')
        if not telefono.strip() and not correo.strip():
            raise ValueError('Indique al menos un medio de contacto.')
        if telefono.strip() and (not re.fullmatch(r'[+()\d\s.\-]{7,40}', telefono.strip()) or len(re.sub(r'\D', '', telefono)) < 7):
            raise ValueError('telefono: indique un número válido.')
        if correo:
            try:
                validate_email(correo)
            except ValidationError:
                raise ValueError('correo: dirección inválida.') from None
        preferencia = entrada.get('preferencia_contacto')
        if preferencia not in ('TELEFONO', 'CORREO') or (preferencia == 'TELEFONO' and not telefono.strip()) or (preferencia == 'CORREO' and not correo.strip()):
            raise ValueError('Elija un medio de contacto disponible.')
        if entrada.get('accion') not in ('VISITA', 'FINANCIACION', 'CONDICIONES', 'ACOMPANAMIENTO'):
            raise ValueError('Seleccione el siguiente paso.')
        if entrada.get('consentimiento') is not True:
            raise ValueError('Debe autorizar el tratamiento de sus datos para solicitar asesoría.')
        evaluacion_actual = evaluar_perfil(respuestas)
        inmueble = None
        if entrada.get('inmueble'):
            inmueble = get_object_or_404(obtener_catalogo_publico(), pk=entrada['inmueble'])
            if inmueble.pk not in {o['id'] for o in evaluacion_actual['opciones']}:
                raise ValueError('Seleccione una vivienda que coincida con su perfil actual.')
        with transaction.atomic():
            perfil = Perfilacion.objects.create(usuario=request.user if request.user.is_authenticated else None,
                                               clave_sesion=request.session.session_key or '', respuestas=respuestas, estado='SOLICITUD')
            evaluacion = EvaluacionPerfil.objects.create(perfilacion=perfil, revision=perfil.revision,
                                                        respuestas=respuestas, resultados=evaluacion_actual)
            solicitud = SolicitudAsesoria.objects.create(perfilacion=perfil, evaluacion=evaluacion, inmueble=inmueble,
                nombre=nombre.strip(), telefono=telefono.strip(), correo=correo.strip(),
                preferencia_contacto=preferencia, accion=entrada['accion'],
                consentimiento=True, clave_idempotencia=clave)
    except IntegrityError:
        anterior = SolicitudAsesoria.objects.filter(clave_idempotencia=clave).first()
        if anterior:
            return JsonResponse({'solicitud': str(anterior.id), 'estado': 'REGISTRADA'})
        return error('No se pudo registrar la solicitud. Inténtelo de nuevo.', 409)
    except (ValueError, TypeError) as exc:
        return error(str(exc), 409 if 'Recarga la página' in str(exc) else 400)
    return JsonResponse({'solicitud': str(solicitud.id), 'estado': 'REGISTRADA'}, status=201)
