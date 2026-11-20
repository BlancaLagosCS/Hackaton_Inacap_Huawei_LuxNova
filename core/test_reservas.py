from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

from django.db import close_old_connections, connections
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from .forms import SolicitarEventoForm
from .models import AvalClub, Club, Evento, MensajeDirecto, Sede, Usuario
from .reservas import intervalo_dia, texto_reserva
from .services import notificar_solicitud_aval


# Recibe una BD aislada; verifica disponibilidad diaria, bloqueos pendientes, aprobación y acciones de aval siempre visibles.
class ReservasDiariasTests(TestCase):
    # Crea actores sintéticos y una fecha futura; no recibe datos externos ni devuelve valor.
    def setUp(self):
        self.sede = Sede.objects.create(nom_sede='Sede reservas ficticia', dir_sede='Demo')
        self.otra = Sede.objects.create(nom_sede='Otra sede reservas', dir_sede='Demo')
        self.lider = Usuario.objects.create_user(username='res_lider', rut_usu='RES-LIDER', corr_usu='res_lider@inacap.cl', sede_usu=self.sede, rol_usu='LIDER_ESTUDIANTIL')
        self.dae = Usuario.objects.create_user(username='res_dae', rut_usu='RES-DAE', corr_usu='res_dae@inacap.cl', sede_usu=self.sede, rol_usu='DAE')
        self.estudiante = Usuario.objects.create_user(username='res_est', rut_usu='RES-EST', corr_usu='res_est@inacap.cl', sede_usu=self.sede)
        self.dia = timezone.localdate() + timedelta(days=7)
        self.client.force_login(self.lider)

    # Recibe campos opcionales; devuelve datos del formulario diario, sin horarios enviados por cliente.
    def datos(self, **cambios):
        return {'esp_even': 'Auditorio Principal', 'mes_reserva': self.dia.strftime('%Y-%m'), 'dia_even': self.dia.isoformat(), 'orga_even': 'PERSONAL', 'tit_even': 'Solicitud diaria ficticia', 'desc_even': 'Demo', 'cat_even': 'TODO_PUBLICO', 'alc_even': 'SEDE', **cambios}

    # Recibe día/estado opcionales y campos de modelo; devuelve un evento de día completo.
    def evento(self, dia=None, estado='APROBADO', **campos):
        inicio, fin = intervalo_dia(dia or self.dia)
        return Evento.objects.create(**{'tit_even': 'Reserva confidencial de prueba', 'desc_even': 'Demo', 'cat_even': 'TODO_PUBLICO', 'sede_even': self.sede, 'esp_even': 'Auditorio Principal', 'fech_even': inicio, 'ffin_even': fin, 'crea_even': self.lider, 'est_even': estado, **campos})

    # Consulta calendario con aprobados, pendientes, rechazados y otra sede; solo bloquea días activos locales sin exponer datos de actividad.
    def test_calendario_por_estado_y_sede(self):
        self.evento()
        pendiente = self.dia + timedelta(days=1)
        rechazado = self.dia + timedelta(days=2)
        ajeno = self.dia + timedelta(days=3)
        self.evento(pendiente, 'PENDIENTE_DAE')
        self.evento(rechazado, 'RECHAZADO')
        self.evento(ajeno, sede_even=self.otra)
        for dia, estado in [(self.dia, 'RESERVADO'), (pendiente, 'EN_REVISION'), (rechazado, 'DISPONIBLE'), (ajeno, 'DISPONIBLE')]:
            respuesta = self.client.get(reverse('core:disponibilidad_espacio'), {'espacio': 'Auditorio Principal', 'mes': dia.strftime('%Y-%m'), 'sede': self.otra.pk})
            datos = respuesta.json()
            self.assertEqual(next(d['estado'] for d in datos['dias'] if d['fecha'] == dia.isoformat()), estado)
            self.assertEqual(dia.isoformat() in datos['disponibles'], estado == 'DISPONIBLE')
            self.assertNotIn('Reserva confidencial', respuesta.content.decode())

    # Envía campos horarios manipulados y luego repite el día; verifica normalización completa y rechazo de la segunda solicitud pendiente.
    def test_dia_completo_y_bloqueo_de_pendientes(self):
        self.assertRedirects(self.client.post('/evento/solicitar/', self.datos(fech_even='2099-01-01T01:00', ffin_even='2099-01-01T02:00')), '/perfil/organizacion/')
        evento = Evento.objects.get(tit_even='Solicitud diaria ficticia')
        self.assertEqual((evento.fech_even, evento.ffin_even), intervalo_dia(self.dia))
        self.assertEqual(evento.est_even, 'PENDIENTE_DAE')
        respuesta = self.client.post('/evento/solicitar/', self.datos(tit_even='Duplicado'))
        self.assertIn('dia_even', respuesta.context['form'].errors)
        self.assertEqual(Evento.objects.count(), 1)
        self.assertNotIn(self.dia.isoformat(), [v for v, _ in respuesta.context['form'].fields['dia_even'].widget.choices])

    # Simula un calendario desactualizado durante la validación; el control bajo bloqueo de sede vuelve a rechazar el día ocupado.
    def test_revalidacion_bajo_bloqueo(self):
        self.evento(estado='PENDIENTE_DAE')
        with patch('core.forms.conflicto_reserva', return_value=False):
            respuesta = self.client.post('/evento/solicitar/', self.datos())
        self.assertIn('dia_even', respuesta.context['form'].errors)
        self.assertEqual(Evento.objects.count(), 1)

    # Resuelve la solicitud que ocupaba un día; rechazar libera la fecha y permite una nueva propuesta.
    def test_rechazar_libera_dia(self):
        evento = self.evento(estado='PENDIENTE_DAE')
        self.client.force_login(self.dae)
        self.client.post(reverse('core:resolver_evento', args=[evento.pk, 'rechazar']))
        self.client.force_login(self.lider)
        self.assertRedirects(self.client.post('/evento/solicitar/', self.datos()), '/perfil/organizacion/')

    # Comprueba que las horas disjuntas y el alias histórico de Patio central bloquean igualmente el día entero.
    def test_alias_historico_y_horas_distintas(self):
        inicio, fin = intervalo_dia(self.dia)
        self.evento(esp_even=' Patio central ', fech_even=inicio + timedelta(hours=8), ffin_even=inicio + timedelta(hours=10))
        form = SolicitarEventoForm(self.datos(esp_even='Patio Central / Ágora'), user=self.lider)
        self.assertFalse(form.is_valid())
        self.assertIn('dia_even', form.errors)
        self.assertTrue(SolicitarEventoForm(self.datos(dia_even=(self.dia + timedelta(days=1)).isoformat(), mes_reserva=(self.dia + timedelta(days=1)).strftime('%Y-%m'), esp_even='Patio Central / Ágora'), user=self.lider).is_valid())
        self.assertEqual(texto_reserva(self.evento(dia=self.dia + timedelta(days=2))), f'{self.dia + timedelta(days=2):%d/%m/%Y} · Día completo')

    # Conserva una reserva antigua de varios días; bloquea cada día ocupado pero libera el día del término exclusivo a medianoche.
    def test_reserva_historica_varios_dias(self):
        inicio, _ = intervalo_dia(self.dia)
        fin, _ = intervalo_dia(self.dia + timedelta(days=3))
        self.evento(fech_even=inicio + timedelta(hours=10), ffin_even=fin)
        for numero in range(4):
            dia = self.dia + timedelta(days=numero)
            datos = self.client.get(reverse('core:disponibilidad_espacio'), {'espacio': 'Auditorio Principal', 'mes': dia.strftime('%Y-%m')}).json()
            self.assertEqual(dia.isoformat() in datos['disponibles'], numero == 3)

    # Recorre acceso DAE/estudiante y parámetros inválidos; la consulta es de lectura y el formulario coloca lugar primero, sin horas.
    def test_accesos_y_formulario(self):
        for usuario in (self.dae, self.estudiante):
            self.client.force_login(usuario)
            self.assertContains(self.client.get('/espacios/'), 'Lugar que quieres reservar')
            self.assertEqual(self.client.get(reverse('core:disponibilidad_espacio'), {'espacio': 'Auditorio Principal', 'mes': self.dia.strftime('%Y-%m')}).status_code, 200)
        self.assertFalse(Evento.objects.exists())
        self.assertEqual(self.client.get(reverse('core:disponibilidad_espacio'), {'espacio': 'Ajeno', 'mes': '2026-99'}).status_code, 400)
        self.assertEqual(list(SolicitarEventoForm(user=self.lider).fields)[:3], ['esp_even', 'mes_reserva', 'dia_even'])
        self.assertNotIn('ffin_even', SolicitarEventoForm().fields)

    # Reserva hoy y consulta Home/preinscripción; un día completo iniciado a medianoche sigue visible y permite participar durante ese día.
    def test_evento_de_hoy_sigue_visible(self):
        evento = self.evento(timezone.localdate())
        self.client.force_login(self.estudiante)
        self.assertContains(self.client.get('/'), evento.tit_even)
        self.client.post(reverse('core:preinscripcion', args=[evento.pk]))
        self.assertTrue(evento.asis_even.filter(pk=self.estudiante.pk).exists())

    # Inserta más de cien avisos después de una solicitud; el aval sigue fijado y el formulario HTML permite aceptar con CSRF.
    def test_aval_antiguo_fijado_y_respuesta_sin_buzon(self):
        club = Club.objects.create(nom_club='Club con aval antiguo', cat_club='OTRO', desc_club='Demo', sede_club=self.sede, lid_club=self.lider)
        aval = AvalClub.objects.create(club_aval=club, estu_aval=self.estudiante)
        mensaje = notificar_solicitud_aval(aval)
        MensajeDirecto.objects.bulk_create([MensajeDirecto(emi_mens=mensaje.emi_mens, rec_mens=self.estudiante, cont_mens=f'Aviso de prueba {i}') for i in range(110)])
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.estudiante)
        datos = cliente.get(reverse('core:dm_hilo', args=[mensaje.emi_mens_id])).json()
        self.assertFalse(any(m.get('aval') for m in datos['mensajes']))
        self.assertEqual(datos['avales_pendientes'][0]['id'], aval.pk)
        self.assertContains(cliente.get('/mensajes/'), 'Aceptar aval')
        token = cliente.cookies['csrftoken'].value
        respuesta = cliente.post(datos['avales_pendientes'][0]['url'], {'decision': 'ACEPTADO'}, HTTP_X_CSRFTOKEN=token, HTTP_ACCEPT='application/json')
        self.assertEqual(respuesta.json()['estado'], 'ACEPTADO')
        self.assertFalse(cliente.get(reverse('core:dm_hilo', args=[mensaje.emi_mens_id])).json()['avales_pendientes'])
        self.assertEqual(cliente.get('/inbox/').status_code, 403)


# Recibe conexiones PostgreSQL independientes; verifica que dos organizadores simultáneos no reserven el mismo lugar y día.
class ConcurrenciaReservasDiariasTests(TransactionTestCase):
    # Recibe ID de usuario y campos; envía la solicitud con conexión propia y devuelve su estado HTTP, cerrando conexiones al terminar.
    def solicitar(self, usuario_id, datos):
        close_old_connections()
        try:
            cliente = Client()
            cliente.force_login(Usuario.objects.get(pk=usuario_id))
            return cliente.post('/evento/solicitar/', datos).status_code
        finally:
            connections.close_all()

    # Lanza dos solicitudes iguales; una sola queda pendiente y la otra recibe errores de disponibilidad.
    def test_dos_solicitudes_simultaneas(self):
        sede = Sede.objects.create(nom_sede='Sede carrera diaria', dir_sede='Demo')
        usuarios = [Usuario.objects.create_user(username=f'diario_{i}', rut_usu=f'DIARIO-{i}', corr_usu=f'diario_{i}@inacap.cl', rol_usu='LIDER_ESTUDIANTIL', sede_usu=sede) for i in range(2)]
        dia = timezone.localdate() + timedelta(days=10)
        datos = {'esp_even': 'Auditorio Principal', 'mes_reserva': dia.strftime('%Y-%m'), 'dia_even': dia.isoformat(), 'orga_even': 'PERSONAL', 'tit_even': 'Solicitud concurrente', 'desc_even': 'Demo', 'cat_even': 'TODO_PUBLICO', 'alc_even': 'SEDE'}
        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            tareas = [ejecutor.submit(self.solicitar, usuario.pk, datos) for usuario in usuarios]
            self.assertEqual(sorted(t.result(timeout=30) for t in tareas), [200, 302])
        self.assertEqual(Evento.objects.filter(est_even='PENDIENTE_DAE').count(), 1)
