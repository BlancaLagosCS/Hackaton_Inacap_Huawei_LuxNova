from datetime import timedelta
from importlib import import_module

from django.apps import apps
from django.core.exceptions import FieldDoesNotExist
from django.db import IntegrityError, connection, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import RegistroForm, SolicitarEventoForm
from .models import AvalClub, CARRERAS_CHOICES, Club, Evento, MembresiaClub, MensajeDirecto, MensajeInbox, PublicacionForo, Sede, Usuario
from .services import notificar_solicitud_aval


# Recibe una BD aislada; verifica el foro compacto, clubes, membresías, representación y avales oficiales de la ampliación v11.
class ComunidadV11Tests(TestCase):
    # Prepara usuarios y clubes sintéticos; no recibe datos externos ni devuelve valor.
    def setUp(self):
        self.sede = Sede.objects.create(nom_sede='Comunidad ficticia', dir_sede='Demo')
        self.otra = Sede.objects.create(nom_sede='Otra comunidad ficticia', dir_sede='Demo')
        self.lider = self.usuario('lider', 'LIDER_ESTUDIANTIL')
        self.estudiantes = [self.usuario(f'par{i}') for i in range(4)]
        self.dae = self.usuario('dae', 'DAE')
        self.ajeno = self.usuario('ajeno', sede=self.otra)
        self.club = Club.objects.create(nom_club='Club comunidad ficticio', cat_club='OTRO', desc_club='Demo', sede_club=self.sede, lid_club=self.lider, est_club='APROBADO')
        self.otro_club = Club.objects.create(nom_club='Club ajeno ficticio', cat_club='OTRO', desc_club='Demo', sede_club=self.otra, lid_club=self.ajeno, est_club='APROBADO')
        MembresiaClub.objects.create(club_memb=self.club, usu_memb=self.lider)
        self.client.force_login(self.estudiantes[0])

    # Recibe nickname, rol y sede opcionales; devuelve un usuario sintético con identificadores únicos.
    def usuario(self, nombre, rol='ESTUDIANTE', sede=None):
        return Usuario.objects.create_user(username=f'com_{nombre}', nom_usu=f'Ficticio {nombre}', rut_usu=f'COM-{nombre}', corr_usu=f'com_{nombre}@inacap.cl', sede_usu=sede or self.sede, carr_usu='Ing. Informática', rol_usu=rol)

    # Recibe campos opcionales; devuelve un formulario de evento futuro a título personal.
    def datos_evento(self, **cambios):
        inicio = timezone.localtime(timezone.now() + timedelta(days=6))
        datos = {'orga_even': 'PERSONAL', 'tit_even': 'Evento comunidad', 'desc_even': 'Demo', 'cat_even': 'TODO_PUBLICO', 'alc_even': 'SEDE', 'esp_even': 'Auditorio Principal', 'dia_even': inicio.date().isoformat(), 'mes_reserva': inicio.strftime('%Y-%m')}
        return {**datos, **cambios}

    # Recibe campos opcionales; devuelve un evento de club aprobado con fechas pasadas o futuras para verificar historial.
    def evento(self, **cambios):
        inicio = timezone.now() + timedelta(days=4)
        datos = {'tit_even': 'Actividad de club', 'desc_even': 'Demo', 'cat_even': 'TODO_PUBLICO', 'sede_even': self.sede, 'crea_even': self.lider, 'esp_even': 'Patio', 'fech_even': inicio, 'ffin_even': inicio + timedelta(hours=1), 'orga_even': 'CLUB', 'club_even': self.club, 'est_even': 'APROBADO'}
        return Evento.objects.create(**{**datos, **cambios})

    # Consulta el foro y publica desde la pantalla dedicada; verifica filtros primero, ausencia del compositor y aislamiento de sede.
    def test_foro_compacto_y_formulario_dedicado(self):
        publicacion = PublicacionForo.objects.create(aut_publ=self.lider, sede_publ=self.sede, cont_publ='Contenido visible', etiq_publ='NOTICIA')
        PublicacionForo.objects.create(aut_publ=self.ajeno, sede_publ=self.otra, cont_publ='Contenido otra sede')
        respuesta = self.client.get('/foro/')
        self.assertNotContains(respuesta, 'name="cont_publ"')
        self.assertContains(respuesta, 'Crear publicación')
        html = respuesta.content.decode()
        self.assertLess(html.index('aria-label="Filtrar publicaciones"'), html.index('LA VIDA DE TU SEDE'))
        self.assertNotContains(respuesta, 'Contenido otra sede')
        self.assertQuerySetEqual(self.client.get('/foro/?etiqueta=NOTICIA').context['publicaciones'], [publicacion], transform=None)
        self.assertTemplateUsed(self.client.get('/foro/publicar/'), 'crear_publicacion.html')
        respuesta = self.client.post('/foro/publicar/', {'etiq_publ': 'NOTICIA', 'cont_publ': ''})
        self.assertTemplateUsed(respuesta, 'crear_publicacion.html')
        self.assertRedirects(self.client.post('/foro/publicar/', {'etiq_publ': 'AHORA_MISMO', 'cont_publ': 'Publicación ficticia', 'sede_publ': self.otra.pk, 'aut_publ': self.ajeno.pk}), '/foro/')
        creada = PublicacionForo.objects.get(cont_publ='Publicación ficticia')
        self.assertEqual(creada.aut_publ_id, self.estudiantes[0].pk)
        self.assertEqual(creada.sede_publ_id, self.sede.pk)

    # Envía dos propuestas como líder; verifica cuatro DM por club, sin mensajes de aval en buzón ni membresías implícitas de avalistas.
    def test_lider_puede_solicitar_varios_clubes(self):
        self.client.force_login(self.lider)
        for nombre in ['Club adicional uno', 'Club adicional dos']:
            self.assertRedirects(self.client.post('/club/postular/', {'nom_club': nombre, 'cat_club': 'OTRO', 'desc_club': 'Demo', 'avales': [u.pk for u in self.estudiantes]}), '/club/postular/')
            club = Club.objects.get(nom_club=nombre)
            self.assertEqual(club.avales.count(), 4)
            self.assertEqual(MensajeDirecto.objects.filter(aval_mens__club_aval=club).count(), 4)
            self.assertFalse(MensajeInbox.objects.filter(club_inbo=club, tipo_inbo='SOLICITUD_AVAL').exists())
            self.assertFalse(club.membresias.exists())
            for aval in club.avales.all():
                notificar_solicitud_aval(aval)
            self.assertEqual(MensajeDirecto.objects.filter(aval_mens__club_aval=club).count(), 4)

    # Envía representación personal, club propio, pendiente y ajeno; verifica selección explícita, autorización y vínculo guardado.
    def test_representacion_evento_y_club_autorizado(self):
        self.client.force_login(self.lider)
        self.assertFalse(SolicitarEventoForm(self.datos_evento(orga_even=''), user=self.lider).is_valid())
        for datos in [self.datos_evento(orga_even='CLUB'), self.datos_evento(orga_even='CLUB', club_even=self.otro_club.pk), self.datos_evento(club_even=self.club.pk)]:
            self.assertFalse(SolicitarEventoForm(datos, user=self.lider).is_valid())
        otro_lider = Club.objects.create(nom_club='Otro responsable local', cat_club='OTRO', desc_club='Demo', sede_club=self.sede, lid_club=self.estudiantes[1], est_club='APROBADO')
        self.assertFalse(SolicitarEventoForm(self.datos_evento(orga_even='CLUB', club_even=otro_lider.pk), user=self.lider).is_valid())
        Club.objects.filter(pk=self.club.pk).update(est_club='PENDIENTE_DAE')
        self.assertFalse(SolicitarEventoForm(self.datos_evento(orga_even='CLUB', club_even=self.club.pk), user=self.lider).is_valid())
        Club.objects.filter(pk=self.club.pk).update(est_club='APROBADO')
        respuesta = self.client.get('/evento/solicitar/', {'club': self.club.pk})
        self.assertEqual(respuesta.context['form'].initial['club_even'], self.club.pk)
        self.assertEqual(self.client.get('/evento/solicitar/', {'club': self.otro_club.pk}).status_code, 404)
        self.assertRedirects(self.client.post('/evento/solicitar/', self.datos_evento(orga_even='CLUB', club_even=self.club.pk)), '/perfil/organizacion/')
        evento = Evento.objects.get(tit_even='Evento comunidad')
        self.assertEqual(evento.club_even_id, self.club.pk)
        self.assertEqual(evento.crea_even_id, self.lider.pk)
        self.assertEqual(evento.est_even, 'PENDIENTE_DAE')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Evento.objects.filter(pk=evento.pk).update(orga_even='PERSONAL')

    # Solicita membresías propias y manipuladas; verifica idempotencia, POST/CSRF, sede y visibilidad de miembros reservada al líder.
    def test_membresias_y_privacidad_de_miembros(self):
        url = reverse('core:membresia_club', args=[self.club.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.estudiantes[0])
        self.assertEqual(cliente.post(url, {'accion': 'unirse'}).status_code, 403)
        for _ in range(2):
            self.assertRedirects(self.client.post(url, {'accion': 'unirse', 'usu_memb': self.ajeno.pk}), reverse('core:detalle_club', args=[self.club.pk]))
        self.assertEqual(MembresiaClub.objects.filter(usu_memb=self.estudiantes[0], club_memb=self.club).count(), 1)
        self.assertFalse(MembresiaClub.objects.filter(usu_memb=self.ajeno).exists())
        self.assertEqual(self.client.post(reverse('core:membresia_club', args=[self.otro_club.pk]), {'accion': 'unirse'}).status_code, 404)
        respuesta = self.client.get(reverse('core:detalle_club', args=[self.club.pk]))
        self.assertNotContains(respuesta, 'Miembros del club (')
        self.client.force_login(self.lider)
        respuesta = self.client.get(reverse('core:detalle_club', args=[self.club.pk]))
        self.assertContains(respuesta, self.estudiantes[0].nom_usu)
        self.assertContains(respuesta, 'Miembros del club (2)')
        self.assertEqual(self.client.post(url, {'accion': 'salir'}).status_code, 403)
        self.client.force_login(self.dae)
        self.assertEqual(self.client.post(url, {'accion': 'unirse'}).status_code, 403)

    # Compara eventos pasados, futuros, pendientes y personales antes/después de salir; verifica historial sin preinscripción automática.
    def test_eventos_de_mis_clubes_con_historial(self):
        futuro = self.evento(tit_even='Futuro del club')
        pasado = self.evento(tit_even='Pasado del club', fech_even=timezone.now() - timedelta(days=2), ffin_even=timezone.now() - timedelta(days=1))
        self.evento(tit_even='Solicitud privada pendiente', est_even='PENDIENTE_DAE')
        self.evento(tit_even='Personal fuera del club', orga_even='PERSONAL', club_even=None)
        url = reverse('core:membresia_club', args=[self.club.pk])
        self.client.post(url, {'accion': 'unirse'})
        self.assertQuerySetEqual(self.client.get('/perfil/mis-clubes/').context['eventos'], [futuro, pasado], transform=None)
        self.assertFalse(futuro.asis_even.exists())
        self.client.post(url, {'accion': 'salir'})
        self.assertQuerySetEqual(self.client.get('/perfil/mis-clubes/').context['eventos'], [pasado], transform=None)
        self.client.post(url, {'accion': 'unirse'})
        self.assertEqual(self.client.get('/perfil/mis-clubes/').context['eventos'].count(), 2)

    # Responde por API desde DM; verifica destinatario, CSRF, rechazo definitivo y conservación del canal oficial sin escritura humana.
    def test_avales_en_dm_con_acciones_protegidas(self):
        club = Club.objects.create(nom_club='Solicitud ficticia', cat_club='OTRO', desc_club='Demo', sede_club=self.sede, lid_club=self.lider)
        aval = AvalClub.objects.create(club_aval=club, estu_aval=self.estudiantes[0])
        mensaje = notificar_solicitud_aval(aval)
        url = reverse('core:dm_hilo', args=[mensaje.emi_mens_id])
        recibido = self.client.get(url).json()['mensajes'][0]
        self.assertTrue(recibido['aval']['pendiente'])
        self.client.force_login(self.estudiantes[1])
        self.assertEqual(self.client.post(recibido['aval']['url'], {'decision': 'ACEPTADO'}, HTTP_ACCEPT='application/json').status_code, 404)
        self.client.force_login(self.estudiantes[0])
        respuesta = self.client.post(recibido['aval']['url'], {'decision': 'RECHAZADO'}, HTTP_ACCEPT='application/json')
        self.assertEqual(respuesta.json()['estado'], 'RECHAZADO')
        total = MensajeDirecto.objects.count()
        self.client.post(recibido['aval']['url'], {'decision': 'ACEPTADO'}, HTTP_ACCEPT='application/json')
        self.assertEqual(MensajeDirecto.objects.count(), total)
        aval.refresh_from_db()
        self.assertEqual(aval.est_aval, 'RECHAZADO')
        self.assertEqual(self.client.post(reverse('core:dm_enviar', args=[mensaje.emi_mens_id]), {'cont_mens': 'Intento'}).status_code, 403)

    # Recorre roles del buzón; verifica su ausencia para estudiantes, delegado y jefatura, manteniendo acceso a líderes/DAE/ADMIN.
    def test_buzon_restringido_y_registro_sin_anio(self):
        for rol in ('ESTUDIANTE', 'DELEGADO', 'JEFATURA', 'LIDER_ESTUDIANTIL', 'DAE', 'ADMIN'):
            Usuario.objects.filter(pk=self.estudiantes[0].pk).update(rol_usu=rol)
            permitido = rol in ('LIDER_ESTUDIANTIL', 'DAE', 'ADMIN')
            self.assertEqual(self.client.get('/inbox/').status_code, 200 if permitido else 403)
            self.assertEqual(self.client.get('/perfil/').context['puede_buzon'], permitido)
        self.assertNotIn('anio_usu', RegistroForm().fields)
        with self.assertRaises(FieldDoesNotExist):
            Usuario._meta.get_field('anio_usu')
        self.assertTrue(all('(4 años)' not in nombre for nombre, _ in CARRERAS_CHOICES))

    # Ejecuta dos veces la preparación histórica; verifica carreras normalizadas y reutilización del mensaje de aval previo sin duplicados.
    def test_migracion_datos_idempotente(self):
        Usuario.objects.filter(pk=self.lider.pk).update(carr_usu='Ing. Informática (4 años)')
        club = Club.objects.create(nom_club='Club histórico ficticio', cat_club='OTRO', desc_club='Demo', sede_club=self.sede, lid_club=self.lider)
        aval = AvalClub.objects.create(club_aval=club, estu_aval=self.estudiantes[0])
        MensajeInbox.objects.create(dest_inbo=self.estudiantes[0], club_inbo=club, tipo_inbo='SOLICITUD_AVAL', asun_inbo='Solicitud antigua', cuer_inbo='Texto histórico')
        dm = MensajeDirecto.objects.get(aval_mens=aval)
        MensajeDirecto.objects.filter(pk=dm.pk).update(aval_mens=None, cont_mens='Solicitud antigua\nTexto histórico')
        migracion = import_module('core.migrations.0005_remove_usuario_anio_usu_evento_club_even_and_more')
        with connection.schema_editor() as editor:
            for _ in range(2):
                migracion.preparar_datos(apps, editor)
        self.lider.refresh_from_db()
        dm.refresh_from_db()
        self.assertEqual(self.lider.carr_usu, 'Ing. Informática')
        self.assertEqual(dm.aval_mens_id, aval.pk)
        self.assertEqual(MensajeDirecto.objects.filter(rec_mens=self.estudiantes[0], aval_mens=aval).count(), 1)
