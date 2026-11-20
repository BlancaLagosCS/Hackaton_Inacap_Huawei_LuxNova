from datetime import timedelta
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from django import forms
from django.db import IntegrityError
from unittest.mock import patch
from .forms import validar_rut_chileno
from .models import Evento, MensajeInbox, Sede, Usuario


# Verifica registro y perfiles v4; recibe una base aislada y devuelve resultados de validación y privacidad.
class PerfilesV4Tests(TestCase):
    # Prepara usuarios sintéticos, evento y asistentes; no recibe datos externos ni devuelve valor.
    def setUp(self):
        self.sede = Sede.objects.create(nom_sede='Sede ficticia', dir_sede='Demo')
        self.estudiante = Usuario.objects.create_user(username='demo', rut_usu='11111111-1', corr_usu='demo@example.invalid', nom_usu='Estudiante ficticio', tel_usu='TELEFONO-PRIVADO-A', sede_usu=self.sede)
        self.lider = Usuario.objects.create_user(username='lider', rut_usu='22222222-2', corr_usu='lider@example.invalid', nom_usu='Líder ficticio', tel_usu='TELEFONO-PRIVADO-B', sede_usu=self.sede, rol_usu='LIDER_ESTUDIANTIL')
        self.otro = Usuario.objects.create_user(username='otro', rut_usu='33333333-3', corr_usu='otro@example.invalid', tel_usu='TELEFONO-PRIVADO-C', sede_usu=self.sede)
        self.evento = Evento.objects.create(tit_even='Evento ficticio', desc_even='Demo', cat_even='TODO_PUBLICO', sede_even=self.sede, esp_even='Patio demo', fech_even=timezone.now() + timedelta(days=2), crea_even=self.lider, est_even='APROBADO')
        self.evento.asis_even.add(self.otro)

    # Recibe cambios opcionales y devuelve datos válidos de registro exclusivamente ficticios.
    def datos_registro(self, **cambios):
        datos = {'username': 'nuevo', 'nom_usu': 'Persona ficticia', 'rut_usu': '44444444-4', 'corr_usu': 'nuevo@example.invalid', 'tel_usu': '000000000', 'sede_usu': self.sede.pk, 'carr_usu': 'Ing. Informática (4 años)', 'anio_usu': timezone.localdate().year, 'password1': 'ClaveFicticia-783!', 'password2': 'ClaveFicticia-783!'}
        datos.update(cambios)
        return datos

    # Recibe RUTs sintéticos con y sin formato; verifica Módulo 11, K, cero y rechazo de dígitos falsos.
    def test_modulo_once(self):
        self.assertEqual(validar_rut_chileno(' 11.111.111 - 1 '), '11111111-1')
        self.assertEqual(validar_rut_chileno('6-k'), '6-K')
        self.assertEqual(validar_rut_chileno('14-0'), '14-0')
        for rut in ['11111111-2', '0-0', 'abc', '123--4', '1-']:
            with self.assertRaises(forms.ValidationError):
                validar_rut_chileno(rut)
        respuesta = self.client.post('/registro/', self.datos_registro(rut_usu='44444444-5'))
        self.assertContains(respuesta, 'dígito verificador incorrecto')

    # Recibe duplicados y carrera libre; verifica errores legibles y ausencia de altas inválidas.
    def test_duplicados_y_catalogo(self):
        respuesta = self.client.post('/registro/', self.datos_registro(rut_usu='11.111.111-1'))
        self.assertContains(respuesta, 'Este RUT ya se encuentra registrado en el sistema.')
        respuesta = self.client.post('/registro/', self.datos_registro(corr_usu='DEMO@EXAMPLE.INVALID'))
        self.assertContains(respuesta, 'Este correo institucional ya está registrado.')
        respuesta = self.client.post('/registro/', self.datos_registro(carr_usu='Carrera inexistente'))
        self.assertIn('carr_usu', respuesta.context['form'].errors)
        self.assertEqual(Usuario.objects.count(), 3)
        self.assertRedirects(self.client.post('/registro/', self.datos_registro(rut_usu='44.444.444-4')), '/')
        self.assertEqual(Usuario.objects.get(username='nuevo').rut_usu, '44444444-4')

    # Simula una carrera de inserción; recibe datos válidos y comprueba que el error de PostgreSQL se presenta sin caída.
    def test_integridad_concurrente(self):
        with patch('core.forms.RegistroUsuarioForm.save', side_effect=IntegrityError('Duplicado')):
            respuesta = self.client.post('/registro/', self.datos_registro())
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'ya está registrado. Revisa tus datos.')

    # Recibe perfiles y roles distintos; comprueba que HTML y JSON ocultan todos los teléfonos no autorizados.
    def test_privacidad_html_json(self):
        self.client.force_login(self.estudiante)
        self.assertNotContains(self.client.get(f'/perfil/{self.lider.pk}/'), self.lider.tel_usu)
        self.assertNotContains(self.client.get(f'/perfil/{self.lider.pk}/'), self.otro.tel_usu)
        datos = self.client.get(f'/perfil/{self.lider.pk}/?formato=json').json()
        self.assertIsNone(datos['resumen']['asistentes'][0]['telefono'])
        self.assertContains(self.client.get('/perfil/'), self.estudiante.tel_usu)
        for rol in ['LIDER_ESTUDIANTIL', 'DAE', 'DELEGADO', 'JEFATURA', 'ADMIN']:
            self.estudiante.rol_usu = rol
            self.estudiante.save()
            self.assertContains(self.client.get(f'/perfil/{self.lider.pk}/'), self.lider.tel_usu)
            self.assertEqual(self.client.get(f'/perfil/{self.lider.pk}/?formato=json').json()['resumen']['asistentes'][0]['telefono'], self.otro.tel_usu)

    # Recibe ediciones de bio/rol e IDs públicos; verifica propiedad, campos permitidos y rutas protegidas.
    def test_edicion_y_rutas(self):
        self.assertEqual(self.client.get('/perfil/').status_code, 302)
        self.client.force_login(self.estudiante)
        self.assertEqual(self.client.post(f'/perfil/{self.lider.pk}/', {'bio_usu': 'Intento'}).status_code, 405)
        self.assertRedirects(self.client.post('/perfil/', {'bio_usu': 'Bio ficticia', 'rol_usu': 'ADMIN'}), '/perfil/')
        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.bio_usu, 'Bio ficticia')
        self.assertEqual(self.estudiante.rol_usu, 'ESTUDIANTE')
        self.assertEqual(self.client.get('/perfil/999999/').status_code, 404)

    # Recibe una foto sintética temporal; verifica guardado, rechazo de archivo falso y eliminación de la foto propia.
    def test_foto_perfil(self):
        from io import BytesIO
        from tempfile import TemporaryDirectory
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import override_settings
        self.client.force_login(self.estudiante)
        with TemporaryDirectory() as carpeta, override_settings(MEDIA_ROOT=carpeta):
            buffer = BytesIO()
            Image.new('RGB', (2, 2), color='red').save(buffer, format='PNG')
            foto = SimpleUploadedFile('avatar.png', buffer.getvalue(), content_type='image/png')
            self.assertRedirects(self.client.post('/perfil/', {'bio_usu': 'Demo', 'foto_usu': foto}), '/perfil/')
            self.estudiante.refresh_from_db()
            self.assertTrue(self.estudiante.foto_usu.name.startswith('perfiles/'))
            falsa = SimpleUploadedFile('falsa.png', b'no es una imagen', content_type='image/png')
            respuesta = self.client.post('/perfil/', {'bio_usu': 'Demo', 'foto_usu': falsa})
            self.assertIn('foto_usu', respuesta.context['perfil_form'].errors)
            self.assertRedirects(self.client.post('/perfil/', {'bio_usu': 'Demo', 'foto_usu-clear': 'on'}), '/perfil/')
            self.estudiante.refresh_from_db()
            self.assertFalse(self.estudiante.foto_usu)

    # Recibe eventos con distintos estados y fechas; verifica historial aprobado, conteos vivos y elección del resumen.
    def test_metricas_y_eventos(self):
        self.client.force_login(self.lider)
        self.lider.eventos_asistidos.add(self.evento)
        respuesta = self.client.get('/perfil/')
        self.assertEqual(respuesta.context['eventos_asistidos'].count(), 1)
        self.assertEqual(respuesta.context['resumen']['total'], 2)
        self.evento.asis_even.remove(self.otro)
        self.assertEqual(self.client.get('/perfil/?formato=json').json()['resumen']['total'], 1)
        Evento.objects.filter(pk=self.evento.pk).update(fech_even=timezone.now() - timedelta(days=1))
        self.assertIsNotNone(self.client.get('/perfil/?formato=json').json()['resumen'])
        Evento.objects.filter(pk=self.evento.pk).update(est_even='RECHAZADO')
        self.assertIsNone(self.client.get('/perfil/?formato=json').json()['resumen'])
        self.assertFalse(self.client.get('/perfil/').context['eventos_organizados'].exists())


# Verifica autenticación y aislamiento; recibe una BD de pruebas y produce resultados reproducibles.
class FlujosV2Tests(TestCase):
    # Prepara sedes, usuario y eventos antes de cada prueba; no recibe datos externos ni devuelve valor.
    def setUp(self):
        self.sede = Sede.objects.create(nom_sede='Rancagua', dir_sede='Centro')
        self.otra = Sede.objects.create(nom_sede='Maipú', dir_sede='Centro')
        self.usuario = Usuario.objects.create_user(username='alumna', password='ClaveDemo-493!', corr_usu='alumna@inacap.cl', rut_usu='demo-1', sede_usu=self.sede)
        self.evento = Evento.objects.create(tit_even='Local', desc_even='Evento', cat_even='TODO_PUBLICO', alc_even='SEDE', sede_even=self.sede, esp_even='Patio', fech_even=timezone.now() + timedelta(days=2), crea_even=self.usuario, est_even='APROBADO')
        self.ajeno = Evento.objects.create(tit_even='Otra sede', desc_even='Evento', cat_even='TODO_PUBLICO', alc_even='SEDE', sede_even=self.otra, esp_even='Patio', fech_even=timezone.now() + timedelta(days=2), crea_even=self.usuario, est_even='APROBADO')

    # Comprueba registro, rol forzado, correo único y sesión automática; recibe fixtures y devuelve aserciones.
    def test_registro_y_rol(self):
        datos = {'username': 'nueva', 'nom_usu': 'Nueva Alumna', 'rut_usu': '11111111-1', 'corr_usu': 'NUEVA@inacap.cl', 'tel_usu': '912345678', 'sede_usu': self.sede.pk, 'carr_usu': 'Ing. Informática (4 años)', 'anio_usu': timezone.localdate().year, 'password1': 'UnaClaveLarga-549!', 'password2': 'UnaClaveLarga-549!', 'rol_usu': 'ADMIN'}
        self.assertRedirects(self.client.post(reverse('core:registro'), datos), reverse('core:home'))
        usuario = Usuario.objects.get(username='nueva')
        self.assertEqual(usuario.rol_usu, 'ESTUDIANTE')
        self.assertEqual(usuario.corr_usu, 'nueva@inacap.cl')
        self.assertEqual(int(self.client.session['_auth_user_id']), usuario.pk)
        self.client.logout()
        datos.update(username='otra', rut_usu='22222222-2')
        self.assertContains(self.client.post(reverse('core:registro'), datos), 'Este correo institucional ya está registrado.')

    # Comprueba login por usuario/correo y logout POST; recibe fixtures y devuelve aserciones.
    def test_login_y_logout(self):
        for identificador in ['alumna', 'ALUMNA@INACAP.CL']:
            self.assertRedirects(self.client.post(reverse('core:login'), {'username': identificador, 'password': 'ClaveDemo-493!'}), reverse('core:home'))
            self.assertEqual(self.client.get(reverse('core:logout')).status_code, 405)
            self.assertRedirects(self.client.post(reverse('core:logout')), reverse('core:home'))
        self.assertEqual(self.client.post(reverse('core:login'), {'username': 'alumna', 'password': 'incorrecta'}).status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    # Comprueba separación, fecha, estado y contador personal; recibe fixtures y devuelve aserciones.
    def test_home_y_navbar(self):
        self.assertContains(self.client.get('/'), 'Crear mi cuenta')
        self.client.force_login(self.usuario)
        Evento.objects.filter(pk=self.ajeno.pk).update(alc_even='INTERSEDE')
        MensajeInbox.objects.create(dest_inbo=self.usuario, tipo_inbo='SISTEMA', asun_inbo='Aviso', cuer_inbo='Hola')
        respuesta = self.client.get('/')
        self.assertQuerySetEqual(respuesta.context['eventos_sede'], [self.evento], transform=None)
        self.assertQuerySetEqual(respuesta.context['eventos_intersede'], [self.ajeno], transform=None)
        self.assertEqual(respuesta.context['inbox_no_leidos'], 1)
        Evento.objects.filter(pk=self.evento.pk).update(fech_even=timezone.now() - timedelta(days=1))
        Evento.objects.filter(pk=self.ajeno.pk).update(est_even='PENDIENTE_DAE')
        respuesta = self.client.get('/')
        self.assertFalse(respuesta.context['eventos_sede'].exists())
        self.assertFalse(respuesta.context['eventos_intersede'].exists())
        for nombre in ['ahora_mismo', 'inbox', 'perfil']:
            self.assertEqual(self.client.get(reverse('core:' + nombre), follow=True).status_code, 200)

    # Comprueba inscripción, cancelación y permisos; recibe fixtures y devuelve aserciones.
    def test_preinscripcion_y_permisos(self):
        url = reverse('core:preinscripcion', args=[self.evento.pk])
        self.assertEqual(self.client.post(url).status_code, 302)
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url)
        self.assertTrue(self.evento.asis_even.filter(pk=self.usuario.pk).exists())
        self.assertContains(self.client.get('/'), 'Cancelar pre-inscripción')
        self.client.post(url)
        self.assertFalse(self.evento.asis_even.exists())
        ajeno_url = reverse('core:preinscripcion', args=[self.ajeno.pk])
        self.assertEqual(self.client.post(ajeno_url).status_code, 404)
        Evento.objects.filter(pk=self.ajeno.pk).update(alc_even='INTERSEDE')
        self.assertEqual(self.client.post(ajeno_url).status_code, 302)
        Evento.objects.filter(pk=self.evento.pk).update(est_even='RECHAZADO')
        self.assertEqual(self.client.post(url).status_code, 404)
        Evento.objects.filter(pk=self.evento.pk).update(est_even='APROBADO', fech_even=timezone.now() - timedelta(days=1))
        self.assertEqual(self.client.post(url).status_code, 404)

    # Recibe un cliente con CSRF obligatorio; verifica rechazo sin token y alta con token válido.
    def test_csrf_preinscripcion(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.usuario)
        url = reverse('core:preinscripcion', args=[self.evento.pk])
        self.assertEqual(cliente.post(url).status_code, 403)
        cliente.get('/')
        token = cliente.cookies['csrftoken'].value
        self.assertEqual(cliente.post(url, {'csrfmiddlewaretoken': token}).status_code, 302)
        self.assertTrue(self.evento.asis_even.filter(pk=self.usuario.pk).exists())
