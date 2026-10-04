import json
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from inmuebles.models import Inmueble
from .models import EvaluacionPerfil, Perfilacion, SolicitudAsesoria, SimulacionFinanciera, ReferenciaFinanciera, ReferenciaCambio
from .servicios.catalogo import obtener_catalogo_publico
from .servicios.evaluacion import evaluar_perfil
from .servicios.financiacion import inicial, credito
from .servicios.preguntas import normalizar_respuestas, cobertura, aplicables, pendientes_obligatorias
from .servicios.ubicaciones import obtener_ubicaciones


def vivienda(numero, **cambios):
    campos = dict(titulo=f'Vivienda {numero}', descripcion='Vivienda de ejemplo', tipo='CASA',
                  operacion='VENTA', estado='USADO', pais='Colombia', departamento='Quindío',
                  ciudad='Armenia', barrio='Centro', area_m2=Decimal('80'), habitaciones=3,
                  banos=2, parqueaderos=1, precio=Decimal('500000000'), moneda='COP', estatus='DISPONIBLE')
    campos.update(cambios)
    return Inmueble.objects.create(**campos)


def respuesta(valor, indispensable=False):
    return {'estado': 'RESPONDIDA', 'valor': valor, 'indispensable': indispensable}


def base_perfil(proposito='VIVIR', moneda='COP'):
    datos = {
        'proposito': respuesta(proposito), 'ciudad': {'estado': 'SIN_PREFERENCIA'},
        'entrega': {'estado': 'NO_SE'}, 'habitaciones': {'estado': 'NO_SE'},
        'area_m2': {'estado': 'NO_SE'}, 'parqueadero': {'estado': 'SIN_PREFERENCIA'},
        'presupuesto': respuesta({'monto': '600000000' if moneda == 'COP' else '150000', 'moneda': moneda}),
        'pago': {'estado': 'NO_SE'}, 'recursos': respuesta('0'),
        'aporte_mensual': {'estado': 'NO_SE'},
    }
    if proposito in ('VIVIR', 'AMBAS'):
        datos['familia'] = respuesta({'adultos': 2, 'menores': 1, 'adultos_mayores': 0})
    if proposito in ('INVERTIR', 'AMBAS'):
        datos.update({'objetivo_inversion': respuesta('INGRESOS_ARRIENDO'),
                      'horizonte_inversion': respuesta('MAS_7'), 'prioridad_inversion': respuesta('UBICACION')})
    return datos


class CatalogoYMotorTests(TestCase):
    def test_ubicaciones_disponibles_aun_sin_inventario(self):
        municipios=obtener_ubicaciones()
        self.assertEqual(len(municipios),33)
        self.assertGreaterEqual(sum(len(ciudades) for ciudades in municipios.values()),1100)
        self.assertIn('Armenia',municipios['Quindío'])
        self.assertIn('Cali',municipios['Valle del Cauca'])
        self.assertIn('Bogotá',municipios['Bogotá D.C.'])
        self.assertEqual(evaluar_perfil({})['estado'],'CATALOGO_VACIO')
        with self.assertRaisesRegex(ValueError,'listado'):
            normalizar_respuestas({'ciudad':respuesta({'departamento':'Quindío','ciudad':'Ciudad inventada'})}, {})

    def test_bogota_distrito_coincide_con_publicacion_registrada_en_cundinamarca(self):
        vivienda(1, ciudad='Bogotá', departamento='Cundinamarca')
        p=normalizar_respuestas({'ciudad':respuesta({'departamento':'Bogotá D.C.','ciudad':'Bogotá'},True)}, {})
        self.assertEqual(evaluar_perfil(p)['total_opciones'],1)

    def test_ramas_vivir_invertir_y_ambas(self):
        for proposito, familia, inversion in [('VIVIR', True, False), ('INVERTIR', False, True), ('AMBAS', True, True)]:
            respuestas=normalizar_respuestas(base_perfil(proposito), {})
            self.assertEqual('familia' in aplicables(respuestas), familia)
            self.assertEqual('objetivo_inversion' in aplicables(respuestas), inversion)
            self.assertFalse(pendientes_obligatorias(respuestas))
        editadas=normalizar_respuestas({'proposito':respuesta('INVERTIR'),
                                       'objetivo_inversion':respuesta('REVENTA'),
                                       'horizonte_inversion':{'estado':'NO_SE'},
                                       'prioridad_inversion':respuesta('ESPACIO')}, normalizar_respuestas(base_perfil('VIVIR'), {}))
        self.assertNotIn('familia',editadas)

    def test_campos_necesarios_y_fuentes_de_recursos(self):
        with self.assertRaises(ValueError):
            normalizar_respuestas({'proposito':{'estado':'NO_SE'}}, {})
        with self.assertRaises(ValueError):
            normalizar_respuestas({'presupuesto':{'estado':'SIN_PREFERENCIA'}}, {})
        with self.assertRaises(ValueError):
            normalizar_respuestas({'recursos':respuesta('1000000'),
                                   'fuentes_recursos':respuesta({'cesantias':'500000','cdt':'400000','cuenta':'0','otros':'0'})}, {})
        respuestas=base_perfil()
        respuestas['recursos']=respuesta('1000000')
        respuestas['fuentes_recursos']=respuesta({'cesantias':'500000','cdt':'300000','cuenta':'200000','otros':'0'})
        guardadas=normalizar_respuestas(respuestas, {})
        self.assertFalse(pendientes_obligatorias(guardadas))
        self.assertEqual(guardadas['fuentes_recursos']['valor']['porcentajes'],
                         {'cesantias':'50.0','cdt':'30.0','cuenta':'20.0','otros':'0.0'})
        del respuestas['fuentes_recursos']
        self.assertIn('fuentes_recursos',pendientes_obligatorias(normalizar_respuestas(respuestas, {})))

    def test_cambiar_recursos_invalida_distribucion_anterior(self):
        respuestas=normalizar_respuestas({**base_perfil(), 'recursos':respuesta('1000000'),
            'fuentes_recursos':respuesta({'cesantias':'1000000','cdt':'0','cuenta':'0','otros':'0'})}, {})
        self.assertIn('fuentes_recursos',respuestas)
        nuevas=normalizar_respuestas({'recursos':respuesta('800000')}, respuestas)
        self.assertNotIn('fuentes_recursos',nuevas)
        self.assertIn('fuentes_recursos',pendientes_obligatorias(nuevas))

    def test_ubicacion_departamento_sin_preferencia_de_ciudad(self):
        vivienda(1, ciudad='Armenia')
        vivienda(2, ciudad='Calarcá')
        vivienda(3, ciudad='Bogotá', departamento='Cundinamarca')
        p=normalizar_respuestas({'ciudad':respuesta({'departamento':'Quindío','ciudad':''},True)}, {})
        self.assertEqual(evaluar_perfil(p)['total_opciones'],2)
        p=normalizar_respuestas({'ciudad':{'estado':'SIN_PREFERENCIA'}},p)
        self.assertEqual(evaluar_perfil(p)['total_opciones'],3)

    def test_inversion_no_promete_renta_ni_valorizacion(self):
        vivienda(1)
        p=normalizar_respuestas(base_perfil('INVERTIR'),{})
        resultado=evaluar_perfil(p)
        self.assertEqual(resultado['total_opciones'],1)
        self.assertTrue(any('Información comercial pendiente' in x for x in resultado['opciones'][0]['pendientes']))

    def test_renta_corta_queda_pendiente_sin_afirmar_autorizacion(self):
        vivienda(1)
        respuestas=normalizar_respuestas(base_perfil('INVERTIR'),{})
        respuestas=normalizar_respuestas({'objetivo_inversion':respuesta('RENTA_CORTA')},respuestas)
        opcion=evaluar_perfil(respuestas)['opciones'][0]
        self.assertTrue(any('Renta corta' in x for x in opcion['pendientes']))
        self.assertFalse(any(x['puntuacion']==1 and 'renta' in x['razon'].lower() for x in opcion['razones']))

    def test_cambiar_moneda_obliga_a_reconfirmar_valores_financieros(self):
        p=normalizar_respuestas(base_perfil(), {})
        nuevo=normalizar_respuestas({'presupuesto':respuesta({'monto':'150000','moneda':'USD'})},p)
        self.assertNotIn('recursos',nuevo)
        self.assertNotIn('aporte_mensual',nuevo)
        self.assertIn('recursos',pendientes_obligatorias(nuevo))

    def test_precio_inmueble_usd_se_convierte_con_tasa_verificada(self):
        casa=vivienda(1, precio=Decimal('100000'), moneda='USD')
        perfil=normalizar_respuestas(base_perfil('AMBAS'),{})
        sin=evaluar_perfil(perfil)
        self.assertIsNone(sin['opciones'][0]['precio_comparacion_cop'])
        ReferenciaCambio.objects.create(cop_por_usd=Decimal('4000'),fecha=date.today(),fuente='https://example.org/trm')
        con=evaluar_perfil(perfil)
        self.assertEqual(Decimal(con['opciones'][0]['precio_comparacion_cop']),Decimal('400000000'))
        self.assertEqual(con['opciones'][0]['id'],casa.pk)
        self.assertEqual(sum(con['pesos'].values()),100)

    def test_hogar_orienta_habitaciones_sin_fingir_respuesta_del_cliente(self):
        vivienda(1, habitaciones=2)
        p=normalizar_respuestas(base_perfil('VIVIR'),{})
        resultado=evaluar_perfil(p)
        razones=resultado['opciones'][0]['razones']
        habitacion=next(x for x in razones if x['criterio']=='habitaciones')
        self.assertTrue(habitacion['orientativo'])
        self.assertEqual(p['habitaciones']['estado'],'NO_SE')
        self.assertTrue(any('2 personas' in x['razon'] for x in razones))

    def test_catalogo_filtra_operacion_tipo_y_estado_sin_depender_de_otros_inmuebles(self):
        casa = vivienda(1)
        vivienda(2, tipo='APARTAMENTO', estatus='INACTIVO')
        vivienda(3, tipo='LOTE')
        vivienda(4, operacion='ARRIENDO')
        vivienda(5, operacion='CESION')
        vivienda(6, tipo='LOCAL')
        self.assertEqual(list(obtener_catalogo_publico()), [casa])

    def test_todas_las_opciones_y_catalogo_vacio(self):
        self.assertEqual(evaluar_perfil({})['estado'], 'CATALOGO_VACIO')
        for n in range(5):
            vivienda(n, ciudad=f'Ciudad {n}')
        resultado = evaluar_perfil({})
        self.assertEqual(resultado['total_opciones'], 5)
        self.assertIsNone(resultado['opciones'][0]['afinidad'])
        self.assertIsNotNone(resultado['alternativa'])

    def test_indispensable_excluye_y_preferencia_flexible_no(self):
        vivienda(1, ciudad='Bogotá', departamento='Cundinamarca')
        vivienda(2, ciudad='Armenia')
        p = normalizar_respuestas({'ciudad': respuesta({'departamento': 'Cundinamarca', 'ciudad': 'Bogotá'}, True)}, {})
        self.assertEqual(evaluar_perfil(p)['total_opciones'], 1)
        p = normalizar_respuestas({'ciudad': {'estado': 'SIN_PREFERENCIA'}}, p)
        self.assertEqual(evaluar_perfil(p)['total_opciones'], 2)
        p = normalizar_respuestas({'ciudad': respuesta({'departamento': 'Risaralda', 'ciudad': 'Pereira'}, True)}, p)
        self.assertEqual(evaluar_perfil(p)['estado'], 'SIN_COINCIDENCIAS')

    def test_omitir_reduce_cobertura_y_permite_orden_diferente(self):
        vivienda(1, ciudad='Bogotá', departamento='Cundinamarca', precio=Decimal('300000000'))
        vivienda(2, ciudad='Armenia', precio=Decimal('500000000'))
        p = normalizar_respuestas({'ciudad': respuesta({'departamento': 'Quindío', 'ciudad': 'Armenia'}), 'presupuesto': respuesta({'monto': '600000000', 'moneda': 'COP'})}, {})
        self.assertEqual(evaluar_perfil(p)['opciones'][0]['ciudad'], 'Armenia')
        anterior = cobertura(p)
        p = normalizar_respuestas({'ciudad': {'estado': 'NO_SE'}, 'presupuesto': respuesta({'monto': '310000000', 'moneda': 'COP'})}, p)
        self.assertLess(cobertura(p), anterior)
        self.assertEqual(evaluar_perfil(p)['opciones'][0]['ciudad'], 'Bogotá')

    def test_desconocimiento_no_es_cero_ni_no_aplica_del_cliente(self):
        for estado in ('NO_SE',):
            self.assertNotIn('valor', normalizar_respuestas({'recursos': {'estado': estado}}, {})['recursos'])
        for estado in ('PREFIERO_DESPUES', 'OMITIDA'):
            with self.assertRaises(ValueError):
                normalizar_respuestas({'recursos': {'estado': estado}}, {})
        with self.assertRaises(ValueError):
            normalizar_respuestas({'recursos': {'estado': 'NO_APLICA'}}, {})
        self.assertEqual(normalizar_respuestas({'recursos': respuesta('0')}, {})['recursos']['valor'], '0')

    def test_datos_no_existentes_del_inmueble_no_generan_entrega_verificada(self):
        vivienda(1, modalidad_entrega='SOBRE_PLANOS')
        p = normalizar_respuestas({'entrega': respuesta('3'), 'proposito': respuesta('INVERTIR'), 'objetivo_inversion': respuesta('REVENTA')}, {})
        opcion = evaluar_perfil(p)['opciones'][0]
        self.assertIsNone(opcion['afinidad'])
        self.assertEqual(len(opcion['pendientes']), 2)
        self.assertTrue(any('constructora' in x for x in opcion['pendientes']))

    def test_entrega_inmediata_excluye_sobre_planos(self):
        vivienda(1)
        vivienda(2, modalidad_entrega='SOBRE_PLANOS', meses_entrega=12)
        p = normalizar_respuestas({'entrega': respuesta('0'), 'proposito': respuesta('VIVIR')}, {})
        resultado = evaluar_perfil(p)
        self.assertEqual(resultado['estado'], 'PRELIMINAR')
        self.assertEqual(resultado['total_opciones'], 1)
        self.assertEqual(resultado['excluidas_requisitos'], 1)
        razones = {r['criterio']: r for r in resultado['opciones'][0]['razones']}
        self.assertIn('inmediata', razones['entrega']['razon'].lower())

    def test_entrega_en_meses_puntua_segun_plazo_declarado(self):
        p = normalizar_respuestas({'entrega': respuesta('12'), 'proposito': respuesta('VIVIR')}, {})
        pronto = vivienda(1, modalidad_entrega='SOBRE_PLANOS', meses_entrega=6)
        tarde = vivienda(2, modalidad_entrega='SOBRE_PLANOS', meses_entrega=24)
        listo = vivienda(3)
        razones = {o['id']: {r['criterio']: r for r in o['razones']} for o in evaluar_perfil(p)['opciones']}
        self.assertEqual(razones[pronto.id]['entrega']['puntuacion'], 1)
        self.assertEqual(razones[listo.id]['entrega']['puntuacion'], 1)
        self.assertAlmostEqual(razones[tarde.id]['entrega']['puntuacion'], 0.5)
        self.assertIn('24 meses', razones[tarde.id]['entrega']['razon'])

    def test_ficha_muestra_modalidad_y_meses_de_entrega(self):
        from .servicios.catalogo import ficha
        inmediato = ficha(vivienda(1))
        planos = ficha(vivienda(2, modalidad_entrega='SOBRE_PLANOS', meses_entrega=9))
        sin_dato = ficha(vivienda(3, modalidad_entrega='SOBRE_PLANOS'))
        self.assertEqual(inmediato['entrega_texto'], 'Entrega inmediata (proyecto terminado)')
        self.assertIn('9 meses', planos['entrega_texto'])
        self.assertIn('confirmar', sin_dato['entrega_texto'])
        self.assertIn('Fecha de entrega', sin_dato['pendientes_catalogo'])
        self.assertNotIn('Fecha de entrega', planos['pendientes_catalogo'])

    def test_modalidad_entrega_exige_coherencia(self):
        from django.core.exceptions import ValidationError
        casa = vivienda(1, estado='EN_CONSTRUCCION', modalidad_entrega='SOBRE_PLANOS')
        with self.assertRaises(ValidationError):
            casa.full_clean()
        casa.meses_entrega = 12
        casa.full_clean()
        casa.modalidad_entrega = 'TERMINADO'
        with self.assertRaises(ValidationError):
            casa.full_clean()

    def test_ficha_muestra_empresa_y_origen_de_entrega(self):
        from .servicios.catalogo import ficha
        obra = ficha(vivienda(1, modalidad_entrega='SOBRE_PLANOS', meses_entrega=9, empresa='Uraki Constructora'))
        nueva = ficha(vivienda(2, empresa='Uraki Constructora'))
        anonimo = ficha(vivienda(3))
        self.assertEqual(obra['origen_texto'], 'Proyecto de Uraki Constructora')
        self.assertEqual(nueva['origen_texto'], 'Comercializado por Uraki Constructora')
        self.assertIsNone(anonimo['origen_texto'])
        self.assertEqual(obra['porcentaje_inicial_exigido'], None)
        self.assertEqual(obra['valor_separacion'], None)
        from datetime import date
        entregada = ficha(vivienda(4, estado='NUEVO', empresa='Uraki Constructora',
                                   fecha_entrega_constructora=date(2026, 3, 10)))
        self.assertEqual(entregada['origen_texto'], 'Construido por Uraki Constructora, entregado en marzo de 2026')

    def test_simulador_usa_condiciones_exigidas_por_el_proyecto(self):
        from decimal import Decimal
        from .views_publicas import calcular_escenario
        base = base_perfil()
        base['entrega'] = respuesta('12')
        respuestas = normalizar_respuestas(base, {})
        planos = vivienda(1, modalidad_entrega='SOBRE_PLANOS', meses_entrega=12,
                          porcentaje_inicial_exigido=Decimal('30'), valor_separacion=Decimal('2000000'))
        entrada = {'recursos': '60000000', 'aporte_mensual': '4000000'}
        resultado = calcular_escenario(respuestas, dict(entrada), planos)
        self.assertEqual(resultado['porcentaje_inicial'], '30')
        self.assertEqual(resultado['origen_porcentaje_inicial'], 'EXIGIDO_PROYECTO')
        self.assertEqual(resultado['inicial']['separacion_incluida_en_inicial'], '2000000')
        self.assertEqual(resultado['origen_separacion'], 'EXIGIDO_PROYECTO')
        personal = calcular_escenario(respuestas, {**entrada, 'porcentaje_inicial': 20, 'separacion': '500000'}, planos)
        self.assertEqual(personal['origen_porcentaje_inicial'], 'HIPOTESIS')
        self.assertEqual(personal['origen_separacion'], 'HIPOTESIS')

    def test_simulador_fija_meses_segun_entrega_del_inmueble(self):
        from .views_publicas import calcular_escenario
        base = base_perfil()
        base['entrega'] = respuesta('6')
        respuestas = normalizar_respuestas(base, {})
        entrada = {'porcentaje_inicial': 30, 'recursos': '60000000', 'aporte_mensual': '4000000'}
        listo = vivienda(1)
        planos = vivienda(2, modalidad_entrega='SOBRE_PLANOS', meses_entrega=12)
        sin_dato = vivienda(3, modalidad_entrega='SOBRE_PLANOS')
        r1 = calcular_escenario(respuestas, dict(entrada), listo)
        self.assertEqual((r1['meses_inicial'], r1['origen_meses_inicial']), ('0', 'ENTREGA_INMUEBLE'))
        r2 = calcular_escenario(respuestas, dict(entrada), planos)
        self.assertEqual((r2['meses_inicial'], r2['origen_meses_inicial']), ('12', 'REMANENTE_EN_VIVO'))
        self.assertTrue(r2['fecha_entrega_fija'])
        self.assertEqual((r2['porcentaje_restante'], r2['saldo_a_financiar']), ('70', '350000000'))
        r3 = calcular_escenario(respuestas, dict(entrada), sin_dato)
        self.assertEqual((r3['meses_inicial'], r3['origen_meses_inicial']), ('6', 'DESEO_CLIENTE_POR_CONFIRMAR'))

    def test_simulador_usa_meses_restantes_en_vivo(self):
        from datetime import timedelta
        from django.utils import timezone
        from inmuebles.models import Inmueble
        from .views_publicas import calcular_escenario
        respuestas = normalizar_respuestas(base_perfil(), {})
        entrada = {'porcentaje_inicial': 30, 'recursos': '60000000', 'aporte_mensual': '4000000'}
        planos = vivienda(1, modalidad_entrega='SOBRE_PLANOS', meses_entrega=12)
        Inmueble.objects.filter(pk=planos.pk).update(
            fecha_publicacion=timezone.localdate() - timedelta(days=210))
        planos.refresh_from_db()
        resultado = calcular_escenario(respuestas, dict(entrada), planos)
        self.assertEqual(resultado['origen_meses_inicial'], 'REMANENTE_EN_VIVO')
        self.assertLess(int(resultado['meses_inicial']), 12)


class FinanzasTests(TestCase):
    def test_caso_referencia(self):
        plan = inicial(500000000, 30, 60000000, 24, 4000000)
        self.assertEqual((plan['cuota_inicial'], plan['saldo_inicial'], plan['cuota_mensual'], plan['por_reunir']),
                         ('150000000', '90000000', '3750000', '90000000'))
        self.assertEqual((plan['faltante'], plan['faltante_mensual'], plan['estado']),
                         ('0', '0', 'ALCANZABLE_EN_ESCENARIO'))
        plan_12 = inicial(500000000, 30, 60000000, 12, 4000000)
        self.assertEqual((plan_12['recursos_previstos'], plan_12['faltante']), ('108000000', '42000000'))
        self.assertEqual((plan_12['cuota_mensual'], plan_12['faltante_mensual']), ('7500000', '3500000'))
        cuota = credito(350000000, Decimal('.10'), 20)
        self.assertLessEqual(abs(Decimal(cuota['cuota_capital_intereses']) - 3278238), 2)
        self.assertFalse(cuota['total_completo'])
        self.assertEqual(cuota['comparacion_cuota_comoda'], 'PENDIENTE')

    def test_hitos_separacion_y_plazo_cero(self):
        x = inicial(500000000, 30, 60000000, 24, 4000000, separacion=70000000,
                    hitos=[{'mes': 1, 'monto': 70000000}])
        self.assertEqual(x['cuota_inicial'], '150000000')
        self.assertEqual(x['faltante'], '0')
        self.assertEqual((x['cuota_mensual'], x['faltante_mensual']), ('833333', '0'))
        self.assertTrue(x['alertas'])
        self.assertEqual(inicial(100, 20, 30, 0, 0)['faltante'], '0')
        self.assertEqual(inicial(100, 20, 0, 0, 0)['cuota_mensual'], '20')

    def test_cuenta_regresiva_desde_fecha_fija(self):
        from datetime import date
        from .servicios.financiacion import meses_restantes, sumar_meses
        base = date(2026, 1, 15)
        self.assertEqual(sumar_meses(base, 12).isoformat(), '2027-01-15')
        self.assertEqual(sumar_meses(date(2026, 1, 31), 1).isoformat(), '2026-02-28')
        self.assertEqual(meses_restantes(base, 12, hoy=date(2026, 6, 15)), 7)
        self.assertEqual(meses_restantes(base, 12, hoy=date(2027, 1, 15)), 0)
        self.assertEqual(meses_restantes(base, 12, hoy=date(2027, 6, 1)), 0)
        self.assertIsNone(meses_restantes(base, None, hoy=base))

    def test_casos_limite_credito(self):
        self.assertEqual(credito(1200, 0, 1)['cuota_capital_intereses'], '100')
        self.assertEqual(credito(0, Decimal('.1'), 20)['cuota_capital_intereses'], '0')
        for capital, tasa, anos in [(-1, .1, 20), (100, -1, 20), (100, .1, 0), (100, 'NaN', 20)]:
            with self.assertRaises(ValueError):
                credito(capital, tasa, anos)


class ApiTests(TestCase):
    def setUp(self):
        self.a = Client(enforce_csrf_checks=True)
        self.b = Client(enforce_csrf_checks=True)
        self.a.get('/perfilador/')
        self.b.get('/perfilador/')
        self.csrf_a = self.a.cookies['csrftoken'].value
        self.csrf_b = self.b.cookies['csrftoken'].value

    def enviar(self, cliente, ruta, cuerpo, csrf, metodo='post'):
        return getattr(cliente, metodo)(ruta, data=json.dumps(cuerpo), content_type='application/json', HTTP_X_CSRFTOKEN=csrf)

    def crear(self):
        r = self.enviar(self.a, '/api/perfilador/perfilaciones/', {}, self.csrf_a)
        self.assertEqual(r.status_code, 201)
        return r.json()['id']

    def guardar_base(self, ident, proposito='VIVIR', moneda='COP'):
        ruta=f'/api/perfilador/perfilaciones/{ident}/respuestas/'
        respuesta_api=self.enviar(self.a,ruta,{'revision':0,'respuestas':base_perfil(proposito, moneda)},self.csrf_a,'patch')
        self.assertEqual(respuesta_api.status_code,200,respuesta_api.content)
        return respuesta_api.json()['revision']

    def test_publico_csrf_y_aislamiento_de_sesiones(self):
        self.assertEqual(self.a.get('/perfilador/').status_code, 200)
        self.assertRedirects(self.a.get('/'), '/index2/')
        self.assertEqual(self.a.get('/login/').status_code, 200)
        ubicaciones=self.a.get('/api/perfilador/ubicaciones/').json()['departamentos']
        self.assertIn('Armenia',ubicaciones['Quindío'])
        self.assertNotIn('respuestas',ubicaciones)
        self.assertEqual(self.a.post('/api/perfilador/perfilaciones/', '{}', content_type='application/json').status_code, 403)
        ident = self.crear()
        self.assertEqual(self.b.get(f'/api/perfilador/perfilaciones/{ident}/').status_code, 404)
        self.assertEqual(self.enviar(self.b, f'/api/perfilador/perfilaciones/{ident}/evaluar/', {'revision': 0}, self.csrf_b).status_code, 404)
        self.assertEqual(self.enviar(self.b, f'/api/perfilador/perfilaciones/{ident}/respuestas/', {'revision': 0, 'respuestas': {}}, self.csrf_b, 'patch').status_code, 404)
        self.assertEqual(self.a.patch(f'/api/perfilador/perfilaciones/{ident}/respuestas/', '{}', content_type='application/json').status_code, 403)

    def test_guardado_evaluacion_historial_y_conflicto(self):
        vivienda(1)
        ident = self.crear()
        url = f'/api/perfilador/perfilaciones/{ident}/'
        p = self.enviar(self.a, url+'respuestas/', {'revision': 0, 'respuestas': base_perfil()}, self.csrf_a, 'patch')
        self.assertEqual(p.status_code, 200)
        self.assertEqual(self.enviar(self.a, url+'respuestas/', {'revision': 0, 'respuestas': {'ciudad': respuesta({'departamento':'Cundinamarca','ciudad':'Bogotá'})}}, self.csrf_a, 'patch').status_code, 409)
        ev = self.enviar(self.a, url+'evaluar/', {'revision': 1}, self.csrf_a)
        self.assertEqual(ev.status_code, 200)
        self.assertEqual(ev.json()['total_opciones'], 1)
        historico=f"{url}evaluaciones/{ev.json()['evaluacion']}/"
        self.assertEqual(self.b.get(historico).status_code,404)
        self.assertEqual(self.a.get(historico).json()['resultado']['total_opciones'],1)
        vivienda(2)
        self.assertEqual(EvaluacionPerfil.objects.get(id=ev.json()['evaluacion']).resultados['total_opciones'], 1)
        self.assertTrue(self.a.get(url).json()['resultado_vigente'])

    def test_evaluacion_rechaza_preguntas_obligatorias_pendientes(self):
        ident=self.crear()
        r=self.enviar(self.a,f'/api/perfilador/perfilaciones/{ident}/evaluar/',{'revision':0},self.csrf_a)
        self.assertEqual(r.status_code,400)
        self.assertIn('preguntas necesarias',r.json()['error'])

    def test_usd_tasa_faltante_o_vencida_y_cambio_verificado(self):
        casa=vivienda(1)
        ident=self.crear()
        self.guardar_base(ident,moneda='USD')
        url=f'/api/perfilador/perfilaciones/{ident}/'
        sin_cambio=self.enviar(self.a,url+'evaluar/',{'revision':1},self.csrf_a).json()
        self.assertIsNone(sin_cambio['cambio'])
        self.assertIn('COP/USD', ' '.join(sin_cambio['opciones'][0]['pendientes']))
        referencia=ReferenciaCambio.objects.create(cop_por_usd=Decimal('4000'),fecha=date.today()-timedelta(days=8),fuente='https://example.org/trm')
        self.assertIsNone(self.a.get('/api/perfilador/cambio/').json()['referencia'])
        referencia.fecha=date.today();referencia.save()
        con_cambio=self.enviar(self.a,url+'evaluar/',{'revision':1},self.csrf_a).json()
        self.assertEqual(con_cambio['cambio']['cop_por_usd'],'4000.0000')
        self.assertTrue(con_cambio['opciones'][0]['afinidad'] is not None)
        sim=self.enviar(self.a,url+'simular/',{'revision':1,'evaluacion':con_cambio['evaluacion'],
            'inmueble':casa.id,'porcentaje_inicial':30,'meses_inicial':24,
            'recursos':'15000','aporte_mensual':'1000','tasa_ea':'.10','anos':20},self.csrf_a)
        self.assertEqual(sim.status_code,201,sim.content)
        self.assertEqual(sim.json()['resultado']['inicial']['recursos_aplicables'],'60000000')
        self.assertEqual(sim.json()['resultado']['moneda_perfil'],'USD')

    def test_ayuda_30_por_ciento_usa_ingresos_solo_por_eleccion_explicita(self):
        casa=vivienda(1)
        ident=self.crear()
        datos=base_perfil()
        datos['ingresos']=respuesta('10000000')
        datos['obligaciones']=respuesta('2000000')
        self.assertEqual(self.enviar(self.a,f'/api/perfilador/perfilaciones/{ident}/respuestas/',
            {'revision':0,'respuestas':datos},self.csrf_a,'patch').status_code,200)
        url=f'/api/perfilador/perfilaciones/{ident}/'
        ev=self.enviar(self.a,url+'evaluar/',{'revision':1},self.csrf_a).json()['evaluacion']
        escenario={'revision':1,'evaluacion':ev,'inmueble':casa.pk,'porcentaje_inicial':30,
                   'meses_inicial':24,'recursos':60000000,'usar_aporte_orientativo':True}
        resultado=self.enviar(self.a,url+'simular/',escenario,self.csrf_a)
        self.assertEqual(resultado.status_code,201,resultado.content)
        self.assertEqual(resultado.json()['resultado']['inicial']['recursos_previstos'],'132000000')
        self.assertTrue(resultado.json()['resultado']['aporte_orientativo_30'])

    def test_solicitud_real_idempotente_y_simulacion_sin_tasa_real(self):
        casa = vivienda(1)
        ident = self.crear()
        self.guardar_base(ident)
        url=f'/api/perfilador/perfilaciones/{ident}/'
        ev=self.enviar(self.a,url+'evaluar/',{'revision':1},self.csrf_a).json()['evaluacion']
        escenario={'revision':1,'evaluacion':ev,'inmueble':casa.id,'porcentaje_inicial':'30','meses_inicial':24,'recursos':60000000,'aporte_mensual':4000000,'tasa_ea':'0.10','anos':20}
        sim=self.enviar(self.a,url+'simular/',escenario,self.csrf_a)
        self.assertEqual(sim.status_code,201)
        self.assertEqual(sim.json()['resultado']['credito']['origen_tasa'],'HIPOTESIS_PERSONALIZADA')
        self.assertEqual(self.b.get(url+'simulaciones/'+sim.json()['simulacion']+'/').status_code,404)
        self.assertEqual(self.enviar(self.b,url+'simular/',escenario,self.csrf_b).status_code,404)
        solicitud={'revision':1,'evaluacion':ev,'inmueble':casa.id,'nombre':'Ana Pérez','correo':'ana@example.com','preferencia_contacto':'CORREO','accion':'VISITA','consentimiento':True,'clave_idempotencia':str(uuid4())}
        self.assertEqual(self.enviar(self.a,url+'solicitudes/',solicitud,self.csrf_a).status_code,201)
        self.assertEqual(self.enviar(self.a,url+'solicitudes/',solicitud,self.csrf_a).status_code,200)
        self.assertEqual(SolicitudAsesoria.objects.count(),1)
        self.assertEqual(self.enviar(self.b,url+'solicitudes/',solicitud,self.csrf_b).status_code,404)
        self.assertEqual(self.a.get('/api/perfilador/catalogo/').json()['opciones'][0]['id'],casa.id)

    def test_contacto_necesita_medio_valido_y_permite_solo_telefono(self):
        vivienda(1)
        ident=self.crear()
        self.guardar_base(ident)
        url=f'/api/perfilador/perfilaciones/{ident}/'
        ev=self.enviar(self.a,url+'evaluar/',{'revision':1},self.csrf_a).json()['evaluacion']
        solicitud={'revision':1,'evaluacion':ev,'nombre':'Cliente Prueba','telefono':'x',
                   'preferencia_contacto':'TELEFONO','accion':'ACOMPANAMIENTO','consentimiento':True,
                   'clave_idempotencia':str(uuid4())}
        self.assertEqual(self.enviar(self.a,url+'solicitudes/',solicitud,self.csrf_a).status_code,400)
        solicitud['telefono']='300 123 4567'
        self.assertEqual(self.enviar(self.a,url+'solicitudes/',solicitud,self.csrf_a).status_code,201)

    def test_login_no_cambia_catalogo_y_administrador_exige_permiso(self):
        vivienda(1)
        invitado=self.a.get('/api/perfilador/catalogo/').json()['total']
        user=User.objects.create_user('persona',password='ClaveTest!!32')
        self.a.force_login(user)
        self.assertEqual(self.a.get('/api/perfilador/catalogo/').json()['total'],invitado)
        self.assertNotEqual(self.a.get('/admin/perfilador/solicitudasesoria/').status_code,200)

    def test_api_publica_de_inmuebles_no_permite_alterar_inventario_ajeno(self):
        casa=vivienda(1)
        self.assertEqual(self.b.get('/api/inmuebles/').status_code,200)
        self.assertIn(self.b.post('/api/inmuebles/',data={},content_type='application/json').status_code,(401,403))
        usuario=User.objects.create_user('agente_prueba', password='ClaveTest!!32')
        self.a.force_login(usuario)
        self.assertEqual(self.enviar(self.a,f'/api/inmuebles/{casa.pk}/',{'titulo':'Inyectado'},self.a.cookies['csrftoken'].value,'patch').status_code,404)
        casa.refresh_from_db()
        self.assertNotEqual(casa.titulo,'Inyectado')

    def test_referencia_vencida_y_cambio_no_modifica_historial(self):
        casa=vivienda(1)
        ident=self.crear()
        self.guardar_base(ident)
        url=f'/api/perfilador/perfilaciones/{ident}/'
        ev=self.enviar(self.a,url+'evaluar/',{'revision':1},self.csrf_a).json()['evaluacion']
        ref=ReferenciaFinanciera.objects.create(entidad='Referencia de prueba',producto='Pesos',
                tasa_ea=Decimal('.10'),fuente='https://example.org/fuente',verificada=date.today()-timedelta(days=2),
                vence=date.today()-timedelta(days=1),activa=True)
        base={'revision':1,'evaluacion':ev,'inmueble':casa.id,'porcentaje_inicial':30,
              'meses_inicial':24,'recursos':60000000,'aporte_mensual':4000000,'referencia':ref.id,'anos':20}
        self.assertEqual(self.enviar(self.a,url+'simular/',base,self.csrf_a).status_code,400)
        ref.vence=date.today()+timedelta(days=2);ref.save()
        sim=self.enviar(self.a,url+'simular/',base,self.csrf_a)
        self.assertEqual(sim.status_code,201)
        ref.tasa_ea=Decimal('.20');ref.save()
        historico=self.a.get(url+'simulaciones/'+sim.json()['simulacion']+'/').json()['resultado']
        self.assertEqual(Decimal(historico['credito']['tasa_ea']),Decimal('0.10'))
        self.assertEqual(historico['credito']['origen_tasa'],'REFERENCIA_VIGENTE')
