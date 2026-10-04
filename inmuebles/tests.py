from django.test import TestCase

from .forms import InmuebleForm


def datos_publicar(**cambios):
    datos = {'titulo': 'Apartamento de prueba', 'descripcion': 'Descripción de ejemplo',
             'tipo': 'APARTAMENTO', 'operacion': 'VENTA', 'estado': 'USADO',
             'modalidad_entrega': 'TERMINADO', 'pais': 'Colombia', 'departamento': 'Quindío',
             'ciudad': 'Armenia', 'barrio': 'Centro', 'area_m2': '80', 'habitaciones': '3',
             'banos': '2', 'parqueaderos': '1', 'precio': '500000000', 'moneda': 'COP',
             'nombre_contacto': 'Ana', 'telefono_contacto': '3001234567'}
    datos.update(cambios)
    return datos


class PublicacionEntregaTests(TestCase):
    def test_usado_no_puede_ser_sobre_planos(self):
        form = InmuebleForm(datos_publicar(estado='USADO', modalidad_entrega='SOBRE_PLANOS', meses_entrega='12'))
        self.assertFalse(form.is_valid())
        self.assertIn('modalidad_entrega', form.errors)

    def test_planos_exige_meses(self):
        form = InmuebleForm(datos_publicar(estado='EN_CONSTRUCCION', modalidad_entrega='SOBRE_PLANOS'))
        self.assertFalse(form.is_valid())
        self.assertIn('meses_entrega', form.errors)

    def test_terminado_rechaza_datos_de_planos(self):
        form = InmuebleForm(datos_publicar(modalidad_entrega='TERMINADO', meses_entrega='6'))
        self.assertFalse(form.is_valid())
        self.assertIn('meses_entrega', form.errors)

    def test_planos_rechaza_fecha_de_terminado(self):
        form = InmuebleForm(datos_publicar(estado='EN_CONSTRUCCION', modalidad_entrega='SOBRE_PLANOS',
                                           meses_entrega='12', fecha_entrega_constructora='2025-01-15'))
        self.assertFalse(form.is_valid())
        self.assertIn('fecha_entrega_constructora', form.errors)

    def test_publicacion_planos_valida_con_empresa_y_condiciones(self):
        form = InmuebleForm(datos_publicar(estado='EN_CONSTRUCCION', modalidad_entrega='SOBRE_PLANOS',
                                           meses_entrega='12', porcentaje_inicial_exigido='30',
                                           valor_separacion='2000000', empresa='Uraki Constructora'))
        self.assertTrue(form.is_valid(), form.errors)
        inmueble = form.save(commit=False)
        inmueble.usuario = None
        inmueble.save()
        self.assertEqual(inmueble.empresa, 'Uraki Constructora')
        self.assertEqual(inmueble.meses_entrega, 12)

    def test_terminado_nuevo_acepta_fecha_y_empresa(self):
        form = InmuebleForm(datos_publicar(estado='NUEVO', modalidad_entrega='TERMINADO',
                                           fecha_entrega_constructora='2026-03-10', empresa='Uraki Constructora'))
        self.assertTrue(form.is_valid(), form.errors)
