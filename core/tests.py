from datetime import timedelta
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from .models import Evento, MensajeInbox, Sede, Usuario


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
        datos = {'username': 'nueva', 'nom_usu': 'Nueva Alumna', 'rut_usu': 'demo-2', 'corr_usu': 'NUEVA@inacap.cl', 'tel_usu': '912345678', 'sede_usu': self.sede.pk, 'carr_usu': 'Informática', 'anio_usu': timezone.localdate().year, 'password1': 'UnaClaveLarga-549!', 'password2': 'UnaClaveLarga-549!', 'rol_usu': 'ADMIN'}
        self.assertRedirects(self.client.post(reverse('core:registro'), datos), reverse('core:home'))
        usuario = Usuario.objects.get(username='nueva')
        self.assertEqual(usuario.rol_usu, 'ESTUDIANTE')
        self.assertEqual(usuario.corr_usu, 'nueva@inacap.cl')
        self.assertEqual(int(self.client.session['_auth_user_id']), usuario.pk)
        self.client.logout()
        datos.update(username='otra', rut_usu='demo-3')
        self.assertContains(self.client.post(reverse('core:registro'), datos), 'Ya existe una cuenta')

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
