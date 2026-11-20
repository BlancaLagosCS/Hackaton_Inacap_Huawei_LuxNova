from io import BytesIO, StringIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import ComentarioForo, MensajeInbox, PublicacionForo, Sede, Usuario


# Prueba el foro con datos ficticios; recibe una base aislada y produce comprobaciones de privacidad y flujo.
class ForoV3Tests(TestCase):
    # Crea dos sedes y actores ficticios de varios roles; no recibe argumentos externos ni devuelve valor.
    def setUp(self):
        self.sede = Sede.objects.create(nom_sede='Sede Ficticia A', dir_sede='Dirección demo')
        self.otra = Sede.objects.create(nom_sede='Sede Ficticia B', dir_sede='Dirección demo')
        self.autor = self.crear_usuario('autor', 'ESTUDIANTE', self.sede)
        self.lider = self.crear_usuario('lider', 'LIDER_ESTUDIANTIL', self.sede)
        self.dae = self.crear_usuario('dae', 'DAE', self.sede)
        self.crear_usuario('delegado', 'DELEGADO', self.sede)
        self.crear_usuario('otro_dae', 'DAE', self.otra)
        self.client.force_login(self.autor)

    # Recibe un identificador, rol y sede; devuelve un usuario con datos exclusivamente ficticios.
    def crear_usuario(self, nombre, rol, sede):
        return Usuario.objects.create_user(username=nombre, nom_usu=f'Persona ficticia {nombre}', rut_usu=f'DEMO-{nombre}', corr_usu=f'{nombre}@example.invalid', tel_usu='TELEFONO-DEMO-PRIVADO', carr_usu='Carrera ficticia', rol_usu=rol, sede_usu=sede)

    # Recibe una etiqueta y sede opcionales; devuelve una publicación guardada para pruebas de aislamiento.
    def crear_publicacion(self, etiqueta='AHORA_MISMO', sede=None):
        return PublicacionForo.objects.create(aut_publ=self.autor, sede_publ=sede or self.sede, etiq_publ=etiqueta, tit_publ='Publicación ficticia', cont_publ='Contenido demo')

    # Verifica login obligatorio, redirección antigua, orden y filtros; recibe fixtures y devuelve aserciones.
    def test_acceso_filtros_y_orden(self):
        primera = self.crear_publicacion()
        segunda = self.crear_publicacion('NOTICIA')
        self.crear_publicacion(sede=self.otra)
        respuesta = self.client.get(reverse('core:foro'))
        self.assertQuerySetEqual(respuesta.context['publicaciones'], [segunda, primera], transform=None)
        for etiqueta, esperado in [('AHORA_MISMO', [primera]), ('NOTICIA', [segunda]), ('INICIATIVA', [])]:
            respuesta = self.client.get(reverse('core:foro'), {'etiqueta': etiqueta})
            self.assertQuerySetEqual(respuesta.context['publicaciones'], esperado, transform=None)
        self.assertEqual(len(self.client.get('/foro/?etiqueta=INVALIDA').context['publicaciones']), 2)
        self.assertRedirects(self.client.get('/ahora-mismo/'), '/foro/')
        self.client.logout()
        self.assertEqual(self.client.get('/foro/').status_code, 302)
        self.assertEqual(self.client.post('/foro/').status_code, 302)

    # Comprueba autor/sede impuestos y destinatarios exactos; recibe un POST manipulado y devuelve aserciones.
    def test_iniciativa_privada_y_autoria(self):
        respuesta = self.client.post('/foro/', {'etiq_publ': 'INICIATIVA', 'tit_publ': '', 'cont_publ': 'Propuesta demo', 'aut_publ': self.dae.pk, 'sede_publ': self.otra.pk})
        self.assertRedirects(respuesta, '/foro/')
        publicacion = PublicacionForo.objects.get()
        self.assertEqual(publicacion.aut_publ, self.autor)
        self.assertEqual(publicacion.sede_publ, self.sede)
        mensajes = MensajeInbox.objects.all()
        self.assertEqual(set(mensajes.values_list('dest_inbo_id', flat=True)), {self.lider.pk, self.dae.pk})
        for mensaje in mensajes:
            self.assertEqual(mensaje.publ_inbo, publicacion)
            self.assertIsNone(mensaje.remi_inbo)
            self.assertFalse(mensaje.leid_inbo)
            self.assertEqual(mensaje.tipo_inbo, 'INICIATIVA_BUZON')
            self.assertEqual(mensaje.asun_inbo, 'Nueva Iniciativa: Sin título')
            for dato in [self.autor.nom_usu, self.autor.carr_usu, self.autor.corr_usu, self.autor.tel_usu, publicacion.cont_publ]:
                self.assertIn(dato, mensaje.cuer_inbo)
        respuesta = self.client.get('/foro/')
        self.assertNotContains(respuesta, self.autor.tel_usu)
        self.assertNotContains(respuesta, self.autor.corr_usu)
        self.client.force_login(self.lider)
        self.assertEqual(self.client.get('/foro/').context['inbox_no_leidos'], 1)

    # Verifica publicaciones normales y formularios inválidos; recibe fixtures y devuelve aserciones sin mensajes extra.
    def test_validaciones_publicacion(self):
        for etiqueta in ['AHORA_MISMO', 'NOTICIA']:
            self.assertRedirects(self.client.post('/foro/', {'etiq_publ': etiqueta, 'cont_publ': 'Demo'}), '/foro/')
        for datos in [{'etiq_publ': 'INICIATIVA', 'cont_publ': '   '}, {'etiq_publ': 'INVALIDA', 'cont_publ': 'Demo'}]:
            respuesta = self.client.post('/foro/', datos)
            self.assertTrue(respuesta.context['form'].errors)
        self.assertEqual(PublicacionForo.objects.count(), 2)
        self.assertFalse(MensajeInbox.objects.exists())

    # Comprueba sede, autor, orden y validación de comentarios; recibe fixtures y devuelve aserciones.
    def test_comentarios(self):
        publicacion = self.crear_publicacion()
        otra = self.crear_publicacion(sede=self.otra)
        url = reverse('core:comentar_publicacion', args=[publicacion.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(reverse('core:comentar_publicacion', args=[otra.pk]), {'cont_come': 'Intento'}).status_code, 404)
        self.assertEqual(self.client.post(url, {'cont_come': '  '}).status_code, 400)
        for texto in ['Primero', '<script>alert(1)</script>']:
            self.assertRedirects(self.client.post(url, {'cont_come': texto, 'aut_come': self.dae.pk}), '/foro/')
        comentarios = list(ComentarioForo.objects.order_by('fech_come'))
        self.assertTrue(all(c.aut_come == self.autor for c in comentarios))
        self.assertEqual(comentarios[0].cont_come, 'Primero')
        respuesta = self.client.get('/foro/')
        self.assertContains(respuesta, '&lt;script&gt;')
        self.assertNotContains(respuesta, '<script>alert(1)</script>')

    # Comprueba usuarios sin sede y CSRF; recibe fixtures y devuelve aserciones de rechazo de escrituras.
    def test_sin_sede_y_csrf(self):
        publicacion = self.crear_publicacion()
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.autor)
        self.assertEqual(cliente.post('/foro/', {'etiq_publ': 'NOTICIA', 'cont_publ': 'Demo'}).status_code, 403)
        self.assertEqual(cliente.post(reverse('core:comentar_publicacion', args=[publicacion.pk]), {'cont_come': 'Demo'}).status_code, 403)
        self.autor.sede_usu = None
        self.autor.save()
        self.assertContains(self.client.get('/foro/'), 'Necesitas una sede asignada')
        self.assertEqual(self.client.post('/foro/', {'etiq_publ': 'NOTICIA', 'cont_publ': 'Demo'}).status_code, 403)
        self.assertEqual(self.client.post(reverse('core:comentar_publicacion', args=[publicacion.pk]), {'cont_come': 'Demo'}).status_code, 403)

    # Simula fallo de notificaciones; recibe fixtures y verifica que la transacción no deje publicaciones incompletas.
    def test_transaccion_iniciativa(self):
        with patch('core.views.notificar_iniciativa', side_effect=RuntimeError('Fallo simulado')):
            with self.assertRaises(RuntimeError):
                self.client.post('/foro/', {'etiq_publ': 'INICIATIVA', 'cont_publ': 'Demo'})
        self.assertFalse(PublicacionForo.objects.exists())
        self.assertFalse(MensajeInbox.objects.exists())

    # Recibe imágenes ficticias válidas e inválidas; verifica subida y validación sin dejar archivos en media real.
    def test_imagen_opcional(self):
        with TemporaryDirectory() as carpeta, override_settings(MEDIA_ROOT=carpeta):
            buffer = BytesIO()
            Image.new('RGB', (2, 2), color='red').save(buffer, format='PNG')
            foto = SimpleUploadedFile('demo.png', buffer.getvalue(), content_type='image/png')
            self.assertRedirects(self.client.post('/foro/', {'etiq_publ': 'AHORA_MISMO', 'cont_publ': 'Con foto', 'img_publ': foto}), '/foro/')
            publicacion = PublicacionForo.objects.get()
            self.assertTrue(publicacion.img_publ.name.startswith('foro/'))
            self.assertContains(self.client.get('/foro/'), publicacion.img_publ.url)
            falsa = SimpleUploadedFile('falsa.png', b'no es imagen', content_type='image/png')
            respuesta = self.client.post('/foro/', {'etiq_publ': 'NOTICIA', 'cont_publ': 'Demo', 'img_publ': falsa})
            self.assertIn('img_publ', respuesta.context['form'].errors)
            self.assertEqual(PublicacionForo.objects.count(), 1)

    # Ejecuta dos cargas demo; recibe una BD aislada y verifica foro e iniciativas sin duplicados.
    def test_demo_idempotente(self):
        for _ in range(2):
            call_command('cargar_datos_demo', stdout=StringIO())
        sede = Sede.objects.get(nom_sede='INACAP Rancagua')
        self.assertEqual(PublicacionForo.objects.filter(sede_publ=sede).count(), 2)
        self.assertEqual(MensajeInbox.objects.filter(publ_inbo__sede_publ=sede, tipo_inbo='INICIATIVA_BUZON').count(), 2)
