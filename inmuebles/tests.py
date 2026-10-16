from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .forms import InmuebleForm


def datos_publicar(**cambios):
    datos = {'titulo': 'Apartamento de prueba', 'descripcion': 'Descripción de ejemplo',
             'tipo': 'APARTAMENTO', 'operacion': 'VENTA', 'estado': 'USADO',
             'pais': 'Colombia', 'departamento': 'Quindío',
             'ciudad': 'Armenia', 'barrio': 'Centro', 'area_m2': '80', 'habitaciones': '3',
             'banos': '2', 'parqueaderos': '1', 'precio': '500000000', 'moneda': 'COP',
             'nombre_contacto': 'Ana', 'telefono_contacto': '3001234567'}
    datos.update(cambios)
    return datos


class PublicacionEntregaTests(TestCase):
    def test_estado_sobre_planos_deriva_modalidad(self):
        form = InmuebleForm(datos_publicar(estado='EN_CONSTRUCCION', meses_entrega='12'))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.instance.modalidad_entrega, 'SOBRE_PLANOS')

    def test_usado_fuerza_terminada_y_limpia_datos_de_planos(self):
        form = InmuebleForm(datos_publicar(estado='USADO', meses_entrega='12',
                                           porcentaje_inicial_exigido='30', valor_separacion='2000000'))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.instance.modalidad_entrega, 'TERMINADO')
        self.assertIsNone(form.instance.meses_entrega)

    def test_planos_exige_meses(self):
        form = InmuebleForm(datos_publicar(estado='EN_CONSTRUCCION'))
        self.assertFalse(form.is_valid())
        self.assertIn('meses_entrega', form.errors)

    def test_planos_rechaza_fecha_de_terminado(self):
        form = InmuebleForm(datos_publicar(estado='EN_CONSTRUCCION',
                                           meses_entrega='12', fecha_entrega_constructora='2025-01-15'))
        self.assertFalse(form.is_valid())
        self.assertIn('fecha_entrega_constructora', form.errors)

    def test_publicacion_planos_valida_con_empresa_y_condiciones(self):
        form = InmuebleForm(datos_publicar(estado='EN_CONSTRUCCION',
                                           meses_entrega='12', porcentaje_inicial_exigido='30',
                                           valor_separacion='2000000', empresa='Uraki Constructora'))
        self.assertTrue(form.is_valid(), form.errors)
        inmueble = form.save(commit=False)
        inmueble.usuario = None
        inmueble.save()
        self.assertEqual(inmueble.modalidad_entrega, 'SOBRE_PLANOS')
        self.assertEqual(inmueble.empresa, 'Uraki Constructora')
        self.assertEqual(inmueble.meses_entrega, 12)

    def test_terminado_nuevo_acepta_fecha_y_empresa(self):
        form = InmuebleForm(datos_publicar(estado='NUEVO',
                                           fecha_entrega_constructora='2026-03-10', empresa='Uraki Constructora'))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.instance.modalidad_entrega, 'TERMINADO')


class FotografiasPublicacionTests(TestCase):
    def setUp(self):
        fotos = TemporaryDirectory()
        self.addCleanup(fotos.cleanup)
        media = override_settings(MEDIA_ROOT=fotos.name)
        media.enable()
        self.addCleanup(media.disable)
        self.usuario = get_user_model().objects.create_user('agente_fotos', password='ClaveTemporal42!')

    @staticmethod
    def imagen(nombre):
        contenido = BytesIO()
        Image.new('RGB', (2, 2), 'red').save(contenido, format='PNG')
        return SimpleUploadedFile(nombre, contenido.getvalue(), content_type='image/png')

    def publicar(self):
        formulario = InmuebleForm(datos_publicar(), files={
            'imagen1': self.imagen('principal.png'), 'imagen2': self.imagen('segunda.png'),
        })
        self.assertTrue(formulario.is_valid(), formulario.errors)
        inmueble = formulario.save(commit=False)
        inmueble.usuario = self.usuario
        inmueble.save()
        return inmueble

    def test_editar_sin_subir_archivos_conserva_fotos_y_muestra_espacios_vacios(self):
        inmueble = self.publicar()
        nombres = (inmueble.imagen1.name, inmueble.imagen2.name)
        formulario = InmuebleForm(datos_publicar(titulo='Título actualizado'), files={}, instance=inmueble)
        self.assertTrue(formulario.is_valid(), formulario.errors)
        formulario.save()
        inmueble.refresh_from_db()
        self.assertEqual((inmueble.imagen1.name, inmueble.imagen2.name), nombres)
        self.assertFalse(inmueble.imagen3)
        self.assertTrue(inmueble.imagen1.storage.exists(nombres[0]))
        self.client.force_login(self.usuario)
        pagina = self.client.get(reverse('inmuebles_editar', args=[inmueble.pk]))
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, inmueble.imagen1.url)
        self.assertContains(pagina, inmueble.imagen2.url)
        self.assertContains(pagina, 'Reemplazar foto', count=2)
        self.assertContains(pagina, 'Agregar imagen', count=2)

    def test_reemplazar_una_foto_y_llenar_espacio_vacio_no_toca_las_otras(self):
        inmueble = self.publicar()
        nombre_principal = inmueble.imagen1.name
        nombre_segunda = inmueble.imagen2.name
        formulario = InmuebleForm(datos_publicar(), files={'imagen2': self.imagen('reemplazo.png')}, instance=inmueble)
        self.assertTrue(formulario.is_valid(), formulario.errors)
        formulario.save()
        inmueble.refresh_from_db()
        self.assertEqual(inmueble.imagen1.name, nombre_principal)
        self.assertNotEqual(inmueble.imagen2.name, nombre_segunda)
        self.assertIn('reemplazo', inmueble.imagen2.name)
        nombre_reemplazo = inmueble.imagen2.name
        formulario = InmuebleForm(datos_publicar(), files={'imagen3': self.imagen('tercera.png')}, instance=inmueble)
        self.assertTrue(formulario.is_valid(), formulario.errors)
        formulario.save()
        inmueble.refresh_from_db()
        self.assertEqual(inmueble.imagen1.name, nombre_principal)
        self.assertEqual(inmueble.imagen2.name, nombre_reemplazo)
        self.assertIn('tercera', inmueble.imagen3.name)

    def test_imagen_invalida_muestra_error_en_su_espacio_y_no_guarda(self):
        inmueble = self.publicar()
        self.client.force_login(self.usuario)
        respuesta = self.client.post(reverse('inmuebles_editar', args=[inmueble.pk]),
                                    {**datos_publicar(), 'imagen2': SimpleUploadedFile(
                                        'invalida.txt', b'no es una foto', content_type='text/plain')})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, '<p class="foto-error" role="alert">', html=False)
        self.assertContains(respuesta, inmueble.imagen2.url)
        inmueble.refresh_from_db()
        self.assertIn('segunda.png', inmueble.imagen2.name)

    def test_post_de_edicion_reemplaza_solo_el_espacio_elegido(self):
        inmueble = self.publicar()
        nombre_principal, nombre_segunda = inmueble.imagen1.name, inmueble.imagen2.name
        self.client.force_login(self.usuario)
        respuesta = self.client.post(reverse('inmuebles_editar', args=[inmueble.pk]),
                                    {**datos_publicar(titulo='Actualizado con fotos'),
                                     'imagen4': self.imagen('cuarta.png')})
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta.url, reverse('inmuebles_detalle', args=[inmueble.pk]))
        inmueble.refresh_from_db()
        self.assertEqual((inmueble.imagen1.name, inmueble.imagen2.name), (nombre_principal, nombre_segunda))
        self.assertFalse(inmueble.imagen3)
        self.assertIn('cuarta', inmueble.imagen4.name)
