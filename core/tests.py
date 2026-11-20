from datetime import timedelta
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from django import forms
from django.db import IntegrityError
from unittest.mock import patch
from .forms import validar_rut_chileno
from .models import AvalClub, Club, Evento, MensajeInbox, PublicacionForo, Sede, Usuario


# Verifica dominios, buzón y avales v5; recibe una base de pruebas y devuelve resultados de autorización y transición.
class BuzonV5Tests(TestCase):
    # Prepara dos sedes, creador, cuatro pares y dos DAE ficticios; no recibe entradas externas ni devuelve valor.
    def setUp(self):
        self.sede = Sede.objects.create(nom_sede='Sede demo A', dir_sede='Ficticia')
        self.otra = Sede.objects.create(nom_sede='Sede demo B', dir_sede='Ficticia')
        self.creador = Usuario.objects.create_user(username='creador', rut_usu='11111111-1', corr_usu='creador@inacapmail.cl', sede_usu=self.sede)
        self.dae = Usuario.objects.create_user(username='dae', rut_usu='22222222-2', corr_usu='dae@inacap.cl', sede_usu=self.sede, rol_usu='DAE')
        self.dae_ajeno = Usuario.objects.create_user(username='dae_ajeno', rut_usu='33333333-3', corr_usu='dae_ajeno@inacap.cl', sede_usu=self.otra, rol_usu='DAE')
        self.club = Club.objects.create(nom_club='Club ficticio', cat_club='OTRO', desc_club='Demo', lid_club=self.creador, sede_club=self.sede)
        self.avales = []
        for numero in range(4, 8):
            usuario = Usuario.objects.create_user(username=f'par{numero}', rut_usu=f'{str(numero)*8}-{numero}', corr_usu=f'par{numero}@inacapmail.cl', sede_usu=self.sede)
            aval = AvalClub.objects.create(club_aval=self.club, estu_aval=usuario)
            self.avales.append(aval)
            MensajeInbox.objects.create(dest_inbo=usuario, club_inbo=self.club, tipo_inbo='SOLICITUD_AVAL', asun_inbo='Aval demo', cuer_inbo='Responde tu aval')

    # Recibe un aval y una decisión; autentica al dueño y devuelve la respuesta HTTP de la acción.
    def responder(self, aval, decision='ACEPTADO'):
        self.client.force_login(aval.estu_aval)
        return self.client.post(reverse('core:responder_aval', args=[aval.pk]), {'decision': decision})

    # Recibe cuatro aceptaciones y un reenvío; comprueba transición única y avisos solo al creador/DAE local.
    def test_cuarto_aval_y_reenvio(self):
        for indice, aval in enumerate(self.avales):
            self.assertEqual(self.responder(aval).status_code, 302)
            self.club.refresh_from_db()
            self.assertEqual(self.club.est_club, 'PENDIENTE_DAE' if indice == 3 else 'PENDIENTE_AVALES')
            aval.refresh_from_db()
            self.assertEqual(aval.est_aval, 'ACEPTADO')
            self.assertIsNotNone(aval.fech_aval)
        notificaciones = MensajeInbox.objects.filter(tipo_inbo='SISTEMA', club_inbo=self.club)
        self.assertEqual(set(notificaciones.values_list('dest_inbo_id', flat=True)), {self.creador.pk, self.dae.pk})
        self.responder(self.avales[-1])
        self.responder(self.avales[-1], 'RECHAZADO')
        self.assertEqual(notificaciones.count(), 2)
        self.avales[-1].refresh_from_db()
        self.assertEqual(self.avales[-1].est_aval, 'ACEPTADO')

    # Recibe rechazo y reenvío; verifica aviso único y que el club no escale con un aval rechazado.
    def test_rechazo(self):
        self.responder(self.avales[0], 'RECHAZADO')
        self.responder(self.avales[0], 'RECHAZADO')
        for aval in self.avales[1:]:
            self.responder(aval)
        self.club.refresh_from_db()
        self.assertEqual(self.club.est_club, 'PENDIENTE_AVALES')
        self.assertEqual(MensajeInbox.objects.filter(tipo_inbo='SISTEMA', dest_inbo=self.creador).count(), 1)

    # Recibe accesos inválidos; verifica dueño, POST, sede y CSRF sin mutaciones ajenas.
    def test_permisos(self):
        url = reverse('core:responder_aval', args=[self.avales[0].pk])
        self.assertEqual(self.client.post(url, {'decision': 'ACEPTADO'}).status_code, 302)
        self.client.force_login(self.creador)
        self.assertEqual(self.client.post(url, {'decision': 'ACEPTADO'}).status_code, 404)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.force_login(self.avales[0].estu_aval)
        self.assertEqual(self.client.post(url, {'decision': 'otra'}).status_code, 400)
        cliente_csrf = Client(enforce_csrf_checks=True)
        cliente_csrf.force_login(self.avales[0].estu_aval)
        self.assertEqual(cliente_csrf.post(url, {'decision': 'ACEPTADO'}).status_code, 403)
        Usuario.objects.filter(pk=self.avales[0].estu_aval_id).update(sede_usu=self.otra)
        self.assertEqual(self.client.post(url, {'decision': 'ACEPTADO'}).status_code, 403)

    # Recibe avisos y avales pendientes; verifica lectura propia y preservación del contador hasta responder.
    def test_lectura_y_contador(self):
        usuario = self.avales[0].estu_aval
        sistema = MensajeInbox.objects.create(dest_inbo=usuario, tipo_inbo='SISTEMA', asun_inbo='Solo propio', cuer_inbo='Aviso')
        ajeno = MensajeInbox.objects.create(dest_inbo=self.creador, tipo_inbo='SISTEMA', asun_inbo='Mensaje privado ajeno', cuer_inbo='Oculto')
        self.client.force_login(usuario)
        respuesta = self.client.get('/inbox/')
        self.assertContains(respuesta, 'Aceptar Aval')
        self.assertNotContains(respuesta, ajeno.asun_inbo)
        self.assertEqual(respuesta.context['inbox_no_leidos'], 1)
        sistema.refresh_from_db()
        ajeno.refresh_from_db()
        self.assertTrue(sistema.leid_inbo)
        self.assertFalse(ajeno.leid_inbo)
        self.responder(self.avales[0])
        self.assertEqual(self.client.get('/inbox/').context['inbox_no_leidos'], 0)

    # Recibe iniciativas propias, ajenas y de otra sede; verifica filtro servidor por rol, destinatario y sede.
    def test_privacidad_iniciativas(self):
        publicacion = PublicacionForo.objects.create(aut_publ=self.creador, sede_publ=self.sede, cont_publ='Demo', etiq_publ='INICIATIVA')
        otra = PublicacionForo.objects.create(aut_publ=self.dae_ajeno, sede_publ=self.otra, cont_publ='Demo', etiq_publ='INICIATIVA')
        for usuario in [self.creador, self.dae]:
            MensajeInbox.objects.create(dest_inbo=usuario, tipo_inbo='INICIATIVA_BUZON', publ_inbo=publicacion, asun_inbo='Iniciativa demo', cuer_inbo='CONTACTO-PRIVADO-DEMO')
        MensajeInbox.objects.create(dest_inbo=self.dae, tipo_inbo='INICIATIVA_BUZON', publ_inbo=otra, asun_inbo='Iniciativa ajena', cuer_inbo='CONTACTO-OTRA-SEDE')
        self.client.force_login(self.creador)
        self.assertNotContains(self.client.get('/inbox/'), 'CONTACTO-PRIVADO-DEMO')
        self.client.force_login(self.dae)
        respuesta = self.client.get('/inbox/')
        self.assertContains(respuesta, 'CONTACTO-PRIVADO-DEMO')
        self.assertNotContains(respuesta, 'CONTACTO-OTRA-SEDE')

    # Recibe correos de diversos dominios; verifica dos permitidos y rechazo de dominios similares o externos.
    def test_dominios(self):
        from .forms import RegistroUsuarioForm
        datos = {'username': 'nueva', 'nom_usu': 'Persona ficticia', 'rut_usu': '88888888-8', 'tel_usu': '000000000', 'sede_usu': self.sede.pk, 'carr_usu': 'Ing. Informática (4 años)', 'anio_usu': timezone.localdate().year, 'password1': 'ClaveDemo-573!', 'password2': 'ClaveDemo-573!'}
        for correo in ['nueva@gmail.com', 'nueva@sub.inacap.cl', 'nueva@inacap.cl.ejemplo.com']:
            form = RegistroUsuarioForm({**datos, 'corr_usu': correo})
            self.assertFalse(form.is_valid())
            self.assertIn('El correo debe ser institucional', str(form.errors['corr_usu']))
        for correo in ['NUEVA@INACAPMAIL.CL', 'nueva@inacap.cl']:
            form = RegistroUsuarioForm({**datos, 'corr_usu': correo})
            self.assertTrue(form.is_valid(), form.errors)
            self.assertEqual(form.cleaned_data['corr_usu'], correo.lower())

    # Recibe texto de búsqueda; verifica resultados de Home/Foro manteniendo su alcance por sede.
    def test_busqueda(self):
        self.client.force_login(self.creador)
        local = PublicacionForo.objects.create(aut_publ=self.creador, sede_publ=self.sede, tit_publ='Robótica', cont_publ='Demo')
        PublicacionForo.objects.create(aut_publ=self.dae_ajeno, sede_publ=self.otra, tit_publ='Robótica', cont_publ='Demo')
        self.assertQuerySetEqual(self.client.get('/foro/?q=Robótica').context['publicaciones'], [local], transform=None)
        self.assertFalse(self.client.get('/foro/?q=desconocido').context['publicaciones'].exists())
        evento = Evento.objects.create(tit_even='Robótica', desc_even='Demo', sede_even=self.sede, crea_even=self.creador, cat_even='TODO_PUBLICO', esp_even='Demo', est_even='APROBADO', fech_even=timezone.now() + timedelta(days=1))
        self.assertQuerySetEqual(self.client.get('/?q=Robótica').context['eventos_sede'], [evento], transform=None)
        self.assertFalse(self.client.get('/?q=desconocido').context['eventos_sede'].exists())

    # Ejecuta dos cargas demo; recibe una BD aislada y comprueba dominios, cuatro avales y solicitudes sin duplicados.
    def test_demo_v5_idempotente(self):
        from io import StringIO
        from django.core.management import call_command
        # Separa los identificadores de estas fixtures de los RUT reservados por la demo.
        for usuario in Usuario.objects.all():
            usuario.rut_usu = f'FIXTURE-V5-{usuario.pk}'
            usuario.save(update_fields=['rut_usu'])
        for _ in range(2):
            call_command('cargar_datos_demo', stdout=StringIO())
        club = Club.objects.get(nom_club='Club Demo de Innovación LuxNova')
        self.assertEqual(club.est_club, 'PENDIENTE_AVALES')
        self.assertEqual(club.avales.filter(est_aval='PENDIENTE').count(), 4)
        self.assertEqual(MensajeInbox.objects.filter(club_inbo=club, tipo_inbo='SOLICITUD_AVAL').count(), 4)
        for username in ['est1', 'est2', 'est3', 'est4', 'est5', 'lider_rancagua', 'dae_rancagua']:
            usuario = Usuario.objects.get(username=username)
            dominio = 'inacap.cl' if username == 'dae_rancagua' else 'inacapmail.cl'
            self.assertEqual(usuario.corr_usu, f'{username}@{dominio}')

    # Simula fallo al generar avisos del cuarto aval; verifica rollback de respuesta, estado del club y lectura del mensaje.
    def test_rollback_cuarto_aval(self):
        for aval in self.avales[:3]:
            self.responder(aval)
        with patch('core.views.MensajeInbox.objects.bulk_create', side_effect=RuntimeError('Fallo simulado')):
            with self.assertRaises(RuntimeError):
                self.responder(self.avales[3])
        self.club.refresh_from_db()
        self.avales[3].refresh_from_db()
        self.assertEqual(self.club.est_club, 'PENDIENTE_AVALES')
        self.assertEqual(self.avales[3].est_aval, 'PENDIENTE')
        self.assertFalse(MensajeInbox.objects.get(dest_inbo=self.avales[3].estu_aval, tipo_inbo='SOLICITUD_AVAL').leid_inbo)


# Verifica registro y perfiles v4; recibe una base aislada y devuelve resultados de validación y privacidad.
class PerfilesV4Tests(TestCase):
    # Prepara usuarios sintéticos, evento y asistentes; no recibe datos externos ni devuelve valor.
    def setUp(self):
        self.sede = Sede.objects.create(nom_sede='Sede ficticia', dir_sede='Demo')
        self.estudiante = Usuario.objects.create_user(username='demo', rut_usu='11111111-1', corr_usu='demo@inacapmail.cl', nom_usu='Estudiante ficticio', tel_usu='TELEFONO-PRIVADO-A', sede_usu=self.sede)
        self.lider = Usuario.objects.create_user(username='lider', rut_usu='22222222-2', corr_usu='lider@inacapmail.cl', nom_usu='Líder ficticio', tel_usu='TELEFONO-PRIVADO-B', sede_usu=self.sede, rol_usu='LIDER_ESTUDIANTIL')
        self.otro = Usuario.objects.create_user(username='otro', rut_usu='33333333-3', corr_usu='otro@inacapmail.cl', tel_usu='TELEFONO-PRIVADO-C', sede_usu=self.sede)
        self.evento = Evento.objects.create(tit_even='Evento ficticio', desc_even='Demo', cat_even='TODO_PUBLICO', sede_even=self.sede, esp_even='Patio demo', fech_even=timezone.now() + timedelta(days=2), crea_even=self.lider, est_even='APROBADO')
        self.evento.asis_even.add(self.otro)

    # Recibe cambios opcionales y devuelve datos válidos de registro exclusivamente ficticios.
    def datos_registro(self, **cambios):
        datos = {'username': 'nuevo', 'nom_usu': 'Persona ficticia', 'rut_usu': '44444444-4', 'corr_usu': 'nuevo@inacapmail.cl', 'tel_usu': '000000000', 'sede_usu': self.sede.pk, 'carr_usu': 'Ing. Informática (4 años)', 'anio_usu': timezone.localdate().year, 'password1': 'ClaveFicticia-783!', 'password2': 'ClaveFicticia-783!'}
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
        respuesta = self.client.post('/registro/', self.datos_registro(corr_usu='DEMO@INACAPMAIL.CL'))
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
