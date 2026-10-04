import json
import re
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .models import Perfilacion, EvaluacionPerfil, SimulacionFinanciera, SolicitudAsesoria, ReferenciaFinanciera
from .servicios.catalogo import obtener_catalogo_publico, ficha
from .servicios.evaluacion import evaluar_perfil
from .servicios.financiacion import inicial, credito, decimal_campo
from .servicios.moneda import obtener_cambio_vigente, a_cop
from .servicios.ubicaciones import obtener_ubicaciones
from .servicios.preguntas import PREGUNTAS, VERSION, normalizar_respuestas, cobertura, siguiente, valor, pendientes_obligatorias


@ensure_csrf_cookie
def inicio(request):
    return render(request, 'perfilador/inicio.html')


def error(mensaje, estado=400):
    return JsonResponse({'error': mensaje}, status=estado)


def datos(request):
    if len(request.body) > 65536:
        raise ValueError('La solicitud es demasiado grande.')
    try:
        objeto = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        raise ValueError('Envíe JSON válido.') from None
    if not isinstance(objeto, dict):
        raise ValueError('Envíe un objeto JSON.')
    return objeto


def propio(request, identificador):
    clave = request.session.session_key
    # La sesión original prueba propiedad incluso si luego el visitante inició sesión.
    return get_object_or_404(Perfilacion, id=identificador, clave_sesion=clave) if clave else get_object_or_404(Perfilacion, id=identificador, clave_sesion='')


def limite(request, accion):
    identificador = request.session.session_key or request.META.get('REMOTE_ADDR', 'anonimo')
    clave = f'perfilador:{accion}:{identificador}:{timezone.now():%Y%m%d%H}'
    if cache.add(clave, 1, timeout=3700):
        return False
    try:
        return cache.incr(clave) > settings.PERFILADOR_LIMITES[accion]
    except ValueError:
        return False


def version(datos_enviados, perfilacion):
    if type(datos_enviados.get('revision')) is not int or datos_enviados['revision'] != perfilacion.revision:
        return error('Perfil desactualizado. Recargue las respuestas antes de continuar.', 409)
    return None


def uuid_recibido(valor, campo):
    try:
        return uuid.UUID(str(valor))
    except (ValueError, TypeError, AttributeError):
        raise ValueError(f'{campo}: identificador inválido.') from None


@require_http_methods(['GET'])
def catalogo(request):
    opciones = [ficha(i) for i in obtener_catalogo_publico()]
    return JsonResponse({'total': len(opciones), 'opciones': opciones})


@require_http_methods(['GET'])
def ubicaciones(request):
    return JsonResponse({'departamentos': obtener_ubicaciones()})


@require_http_methods(['GET'])
def preguntas(request):
    return JsonResponse({'version': VERSION, 'preguntas': PREGUNTAS})


@require_http_methods(['GET'])
def cambio(request):
    referencia = obtener_cambio_vigente()
    return JsonResponse({'referencia': {
        'cop_por_usd': str(referencia.cop_por_usd), 'fecha': referencia.fecha.isoformat(), 'fuente': referencia.fuente,
    } if referencia else None})


@require_http_methods(['GET'])
def referencias(request):
    vigentes = ReferenciaFinanciera.objects.filter(activa=True, vence__gte=timezone.localdate())
    return JsonResponse({'referencias': [
        {'id': ref.pk, 'entidad': ref.entidad, 'producto': ref.producto, 'tasa_ea': str(ref.tasa_ea),
         'verificada': ref.verificada.isoformat(), 'vence': ref.vence.isoformat(), 'fuente': ref.fuente}
        for ref in vigentes]})


@csrf_protect
@require_http_methods(['POST'])
def crear(request):
    if limite(request, 'crear'):
        return error('Demasiados intentos. Inténtelo más tarde.', 429)
    if not request.session.session_key:
        request.session.create()
    perfilacion = Perfilacion.objects.create(
        usuario=request.user if request.user.is_authenticated else None,
        clave_sesion=request.session.session_key,
    )
    return JsonResponse({'id': str(perfilacion.id), 'revision': 0, 'respuestas': {}}, status=201)


@require_http_methods(['GET'])
def perfil(request, identificador):
    p = propio(request, identificador)
    ultima = p.evaluaciones.order_by('-fecha').first()
    cambios = []
    if ultima:
        cambio_actual = obtener_cambio_vigente()
        cambio_guardado = ultima.resultados.get('cambio')
        comparacion_cambio = {'cop_por_usd': str(cambio_actual.cop_por_usd), 'fecha': cambio_actual.fecha.isoformat(), 'fuente': cambio_actual.fuente} if cambio_actual else None
        presupuesto_guardado = valor(p.respuestas, 'presupuesto')
        if cambio_guardado != comparacion_cambio and (
            (isinstance(presupuesto_guardado, dict) and presupuesto_guardado.get('moneda') == 'USD')
            or any(opcion.get('moneda') == 'USD' for opcion in ultima.resultados['opciones'])
        ):
            cambios.append({'motivo': 'Cambió la referencia COP/USD: recalcule la orientación'})
        actuales = {x.pk: x for x in obtener_catalogo_publico()}
        for guardada in ultima.resultados['opciones']:
            actual = actuales.get(guardada['id'])
            if actual is None:
                cambios.append({'inmueble': guardada['id'], 'motivo': 'Ya no está disponible'})
            elif str(actual.precio) != guardada['precio'] or actual.fecha_actualizacion.isoformat() != guardada['actualizado']:
                cambios.append({'inmueble': guardada['id'], 'motivo': 'Precio o publicación actualizados'})
    return JsonResponse({'id': str(p.id), 'revision': p.revision, 'respuestas': p.respuestas,
                         'version_preguntas': p.version_preguntas,
                         'cobertura': cobertura(p.respuestas), 'siguiente_pregunta': siguiente(p.respuestas),
                         'evaluacion': str(ultima.id) if ultima else None,
                         'resultado_vigente': bool(ultima and ultima.revision == p.revision and not cambios),
                         'cambios_catalogo': cambios})


@csrf_protect
@require_http_methods(['PATCH'])
def respuestas(request, identificador):
    p = propio(request, identificador)
    try:
        entrada = datos(request)
        conflicto = version(entrada, p)
        if conflicto:
            return conflicto
        nuevas = normalizar_respuestas(entrada.get('respuestas'), p.respuestas)
    except ValueError as exc:
        return error(str(exc))
    if not Perfilacion.objects.filter(pk=p.pk, revision=p.revision).update(respuestas=nuevas, revision=p.revision + 1, actualizado=timezone.now()):
        return error('Perfil desactualizado. Recargue las respuestas.', 409)
    return JsonResponse({'revision': p.revision + 1, 'respuestas': nuevas,
                         'cobertura': cobertura(nuevas), 'siguiente_pregunta': siguiente(nuevas)})


@csrf_protect
@require_http_methods(['POST'])
def evaluar(request, identificador):
    p = propio(request, identificador)
    if limite(request, 'evaluar'):
        return error('Demasiadas evaluaciones. Inténtelo más tarde.', 429)
    try:
        conflicto = version(datos(request), p)
        if conflicto:
            return conflicto
    except ValueError as exc:
        return error(str(exc))
    if p.version_preguntas != VERSION:
        return error('Este perfil usa un cuestionario anterior. Inicie una nueva búsqueda.', 409)
    pendientes = pendientes_obligatorias(p.respuestas)
    if pendientes:
        return error('Responda primero las preguntas necesarias: ' + ', '.join(PREGUNTAS[c]['texto'] for c in pendientes))
    resultado = evaluar_perfil(p.respuestas)
    evaluacion = EvaluacionPerfil.objects.create(perfilacion=p, revision=p.revision,
                                                respuestas=p.respuestas, resultados=resultado)
    Perfilacion.objects.filter(pk=p.pk).update(estado='PRELIMINAR')
    return JsonResponse({'evaluacion': str(evaluacion.id), **resultado})


@csrf_protect
@require_http_methods(['POST'])
def simular(request, identificador):
    p = propio(request, identificador)
    if limite(request, 'simular'):
        return error('Demasiadas simulaciones. Inténtelo más tarde.', 429)
    try:
        entrada = datos(request)
        conflicto = version(entrada, p)
        if conflicto:
            return conflicto
        ev = get_object_or_404(EvaluacionPerfil, id=uuid_recibido(entrada.get('evaluacion'), 'evaluacion'), perfilacion=p)
        if ev.revision != p.revision:
            return error('Recalcule las recomendaciones para esta revisión del perfil.', 409)
        inmueble = get_object_or_404(obtener_catalogo_publico(), pk=entrada.get('inmueble'))
        guardada = next((o for o in ev.resultados['opciones'] if o['id'] == inmueble.pk), None)
        if guardada is None:
            return error('Este inmueble no figura entre las opciones compatibles.', 400)
        if guardada['precio'] != str(inmueble.precio) or guardada['actualizado'] != inmueble.fecha_actualizacion.isoformat():
            return error('La publicación cambió. Recalcule antes de simular.', 409)
        if inmueble.moneda not in ('COP', 'USD') or inmueble.precio <= 0:
            return error('Se requiere precio positivo en COP o USD para simular.')
        porcentaje = entrada.get('porcentaje_inicial')
        if porcentaje is None:
            return error('porcentaje_inicial: indique un porcentaje hipotético; la publicación no registra la condición comercial.')
        moneda_perfil = (valor(p.respuestas, 'presupuesto') or {}).get('moneda', 'COP')
        referencia_cambio = obtener_cambio_vigente() if moneda_perfil == 'USD' or inmueble.moneda == 'USD' else None
        if (moneda_perfil == 'USD' or inmueble.moneda == 'USD') and not referencia_cambio:
            return error('No existe una referencia COP/USD vigente para simular. Solicite actualizarla.')
        if referencia_cambio and ev.resultados.get('cambio') != {'cop_por_usd': str(referencia_cambio.cop_por_usd), 'fecha': referencia_cambio.fecha.isoformat(), 'fuente': referencia_cambio.fuente}:
            return error('La referencia de cambio cambió. Recalcule antes de simular.', 409)
        precio_cop = a_cop(inmueble.precio, inmueble.moneda, referencia_cambio)
        recursos = entrada.get('recursos', valor(p.respuestas, 'recursos'))
        aporte = entrada.get('aporte_mensual', valor(p.respuestas, 'aporte_mensual'))
        uso_guia = False
        if aporte is None and entrada.get('usar_aporte_orientativo') is True:
            ingresos = valor(p.respuestas, 'ingresos')
            if ingresos is None:
                return error('Declare los ingresos del hogar antes de explorar el ejemplo del 30 %.')
            aporte = str(Decimal(ingresos) * Decimal('0.30'))
            uso_guia = True
        if recursos is None or aporte is None:
            return error('Indique recursos y aporte mensual para simular la cuota inicial.')
        recursos_cop = decimal_campo(a_cop(recursos, moneda_perfil, referencia_cambio), 'recursos')
        aporte_cop = a_cop(aporte, moneda_perfil, referencia_cambio)
        meses = entrada.get('meses_inicial', 0)
        separacion_cop = decimal_campo(a_cop(entrada.get('separacion', 0), moneda_perfil, referencia_cambio), 'separacion')
        incluye_separacion = entrada.get('separacion_incluida_en_recursos')
        if separacion_cop > 0 and recursos_cop > 0 and incluye_separacion not in ('SI', 'NO'):
            return error('Indique si los recursos disponibles incluyen el dinero de la separación.')
        if separacion_cop > 0 and recursos_cop == 0:
            incluye_separacion = 'SI'
        cuota_inicial = inicial(precio_cop, porcentaje, recursos_cop, meses, aporte_cop,
                                separacion_cop, separacion_incluida_en_recursos=(incluye_separacion == 'SI'))
        pago = valor(p.respuestas, 'pago')
        if pago == 'CONTADO' and decimal_campo(porcentaje, 'porcentaje_inicial', Decimal('100')) != 100:
            return error('Para compra de contado indique el 100 % del precio como aporte a la compra.')
        prestamo = None
        referencia = None
        if entrada.get('referencia') is not None:
            referencia = get_object_or_404(ReferenciaFinanciera, pk=entrada['referencia'], activa=True)
            if referencia.vence < timezone.localdate():
                return error('La referencia financiera está vencida. Solicite su actualización o use una hipótesis personalizada.')
        if pago not in ('CONTADO', 'UVR', 'LEASING') and (entrada.get('tasa_ea') is not None or referencia):
            tasa = referencia.tasa_ea if referencia else decimal_campo(entrada['tasa_ea'], 'tasa_ea', Decimal('1'))
            anos = entrada.get('anos', valor(p.respuestas, 'plazo_credito') or 20)
            if referencia and not referencia.plazo_minimo <= int(anos) <= referencia.plazo_maximo:
                return error('anos: plazo fuera de la referencia seleccionada.')
            capital = max(Decimal('0'), precio_cop * (100 - decimal_campo(porcentaje, 'porcentaje_inicial', Decimal('100'))) / 100)
            prestamo = credito(capital, tasa, anos, administracion=inmueble.administracion)
            prestamo['origen_tasa'] = 'REFERENCIA_VIGENTE' if referencia else 'HIPOTESIS_PERSONALIZADA'
            if referencia:
                prestamo['referencia'] = {'entidad': referencia.entidad, 'producto': referencia.producto,
                                         'verificada': referencia.verificada.isoformat(), 'vence': referencia.vence.isoformat(),
                                         'fuente': referencia.fuente, 'porcentaje_maximo': str(referencia.porcentaje_maximo) if referencia.porcentaje_maximo else None}
                if referencia.porcentaje_maximo is not None and capital * 100 > precio_cop * referencia.porcentaje_maximo:
                    prestamo['pendientes'].append('Crédito necesario supera el máximo orientativo de la referencia')
            prestamo['capacidad_pago'] = 'PENDIENTE_VERIFICACION'
        resultado = {'inicial': cuota_inicial, 'credito': prestamo,
                     'producto': pago or 'NO_DECLARADO', 'precio_referencia': str(inmueble.precio),
                     'moneda_precio': inmueble.moneda, 'precio_referencia_cop': str(precio_cop),
                     'moneda_perfil': moneda_perfil,
                     'cambio': {'cop_por_usd': str(referencia_cambio.cop_por_usd), 'fecha': referencia_cambio.fecha.isoformat(),
                                'fuente': referencia_cambio.fuente} if referencia_cambio else None,
                     'aporte_orientativo_30': uso_guia,
                     'obligaciones_declaradas': valor(p.respuestas, 'obligaciones'),
                     'porcentaje_inicial': str(porcentaje), 'condicion_inicial': 'HIPOTESIS_NO_CONFIRMADA',
                     'aviso': 'No es una aprobación bancaria. Seguros, gastos y condiciones requieren confirmación.'}
        simulacion = SimulacionFinanciera.objects.create(
            perfilacion=p, evaluacion=ev, inmueble=inmueble, revision=p.revision,
            referencia=referencia, parametros=entrada, resultado=resultado)
        return JsonResponse({'simulacion': str(simulacion.id), 'resultado': resultado}, status=201)
    except (ValueError, TypeError) as exc:
        return error(str(exc))


@require_http_methods(['GET'])
def historial_evaluacion(request, identificador, registro):
    p = propio(request, identificador)
    ev = get_object_or_404(EvaluacionPerfil, pk=registro, perfilacion=p)
    return JsonResponse({'id': str(ev.id), 'revision': ev.revision, 'respuestas': ev.respuestas,
                         'resultado': ev.resultados, 'fecha': ev.fecha.isoformat()})


@require_http_methods(['GET'])
def historial_simulacion(request, identificador, registro):
    p = propio(request, identificador)
    sim = get_object_or_404(SimulacionFinanciera, pk=registro, perfilacion=p)
    return JsonResponse({'id': str(sim.id), 'revision': sim.revision,
                         'parametros': sim.parametros, 'resultado': sim.resultado, 'fecha': sim.fecha.isoformat()})


@csrf_protect
@require_http_methods(['POST'])
def solicitar(request, identificador):
    p = propio(request, identificador)
    if limite(request, 'solicitar'):
        return error('Demasiados intentos. Inténtelo más tarde.', 429)
    try:
        entrada = datos(request)
        clave = uuid.UUID(str(entrada.get('clave_idempotencia')))
        anterior = SolicitudAsesoria.objects.filter(perfilacion=p, clave_idempotencia=clave).first()
        if anterior:
            return JsonResponse({'solicitud': str(anterior.id), 'estado': 'REGISTRADA'})
        conflicto = version(entrada, p)
        if conflicto:
            return conflicto
        ev = get_object_or_404(EvaluacionPerfil, id=uuid_recibido(entrada.get('evaluacion'), 'evaluacion'), perfilacion=p, revision=p.revision)
        nombre = entrada.get('nombre', '')
        telefono = entrada.get('telefono', '')
        correo = entrada.get('correo', '')
        if not isinstance(nombre, str) or not 2 <= len(nombre.strip()) <= 120:
            return error('nombre: indique su nombre.')
        if not isinstance(telefono, str) or not isinstance(correo, str) or len(telefono) > 40 or len(correo) > 254:
            return error('Contacto inválido.')
        if not telefono.strip() and not correo.strip():
            return error('Indique al menos un medio de contacto.')
        if telefono.strip() and (not re.fullmatch(r'[+()\d\s.\-]{7,40}', telefono.strip()) or len(re.sub(r'\D', '', telefono)) < 7):
            return error('telefono: indique un número de contacto válido.')
        if correo:
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError
            try:
                validate_email(correo)
            except ValidationError:
                return error('correo: dirección inválida.')
        preferencia = entrada.get('preferencia_contacto')
        if preferencia not in ('TELEFONO', 'CORREO') or (preferencia == 'TELEFONO' and not telefono.strip()) or (preferencia == 'CORREO' and not correo.strip()):
            return error('Elija un medio de contacto disponible.')
        if entrada.get('accion') not in ('VISITA', 'FINANCIACION', 'CONDICIONES', 'ACOMPANAMIENTO'):
            return error('Seleccione el siguiente paso.')
        if entrada.get('consentimiento') is not True:
            return error('Debe autorizar el tratamiento de sus datos para solicitar asesoría.')
        inmueble = None
        if entrada.get('inmueble'):
            inmueble = get_object_or_404(obtener_catalogo_publico(), pk=entrada['inmueble'])
            if inmueble.pk not in {o['id'] for o in ev.resultados['opciones']}:
                return error('Seleccione una opción compatible de su evaluación.')
        with transaction.atomic():
            solicitud, _ = SolicitudAsesoria.objects.get_or_create(
                perfilacion=p, clave_idempotencia=clave,
                defaults={'evaluacion': ev, 'inmueble': inmueble, 'nombre': nombre.strip(),
                          'telefono': telefono.strip(), 'correo': correo.strip(),
                          'preferencia_contacto': preferencia, 'accion': entrada['accion'], 'consentimiento': True})
            Perfilacion.objects.filter(pk=p.pk).update(estado='SOLICITUD')
        return JsonResponse({'solicitud': str(solicitud.id), 'estado': 'REGISTRADA'}, status=201)
    except (ValueError, TypeError) as exc:
        return error(str(exc))
