from datetime import timedelta
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from django import forms
from django.db import IntegrityError
from unittest.mock import patch
from .forms import validar_rut_chileno
from .models import AvalClub, Club, Evento, MensajeDirecto, MensajeInbox, PublicacionForo, RegistroAuditoria, Sede, Usuario


# Recibe una BD aislada; verifica la portada común, pantallas separadas y accesos a conversaciones y perfiles de v11.
class PerfilesV11Tests(TestCase):
    # Prepara personas, publicaciones y eventos sintéticos propios y ajenos; no recibe argumentos ni devuelve valor.
    def setUp(self):
        self.sede = Sede.objects.create(nom_sede='Sede v11 ficticia', dir_sede='Demo')
        self.persona = Usuario.objects.create_user(username='persona_v11', nom_usu='Persona V11', rut_usu='FICTICIO-V11-1', corr_usu='persona_v11@inacap.cl', sede_usu=self.sede, rol_usu='LIDER_ESTUDIANTIL')
        self.par = Usuario.objects.create_user(username='par_v11', nom_usu='Par V11', rut_usu='FICTICIO-V11-2', corr_usu='par_v11@inacap.cl', sede_usu=self.sede, tel_usu='TELEFONO-PRIVADO-V11')
        inicio = timezone.now() + timedelta(days=4)
        self.evento = Evento.objects.create(tit_even='Actividad propia V11', desc_even='Demo', cat_even='TODO_PUBLICO', sede_even=self.sede, esp_even='Patio Central', fech_even=inicio, ffin_even=inicio + timedelta(hours=1), crea_even=self.persona, est_even='APROBADO')
        self.ajeno = Evento.objects.create(tit_even='Actividad ajena V11', desc_even='Demo', cat_even='TODO_PUBLICO', sede_even=self.sede, esp_even='Sala Multiuso 101', fech_even=inicio, ffin_even=inicio + timedelta(hours=1), crea_even=self.par, est_even='PENDIENTE_DAE')
        self.evento.asis_even.add(self.persona, self.par)
        PublicacionForo.objects.create(aut_publ=self.persona, sede_publ=self.sede, etiq_publ='NOTICIA', tit_publ='Publicación propia V11', cont_publ='Contenido ficticio')
        self.client.force_login(self.persona)

    # Recorre los seis roles; verifica agenda antes de publicaciones y herramientas después, sin formulario de creación incrustado.
    def test_portada_comun_a_todos_los_roles(self):
        for rol, _ in Usuario._meta.get_field('rol_usu').choices:
            with self.subTest(rol=rol):
                Usuario.objects.filter(pk=self.persona.pk).update(rol_usu=rol)
                respuesta = self.client.get('/perfil/')
                contenido = respuesta.content.decode()
                self.assertContains(respuesta, self.evento.tit_even)
                self.assertContains(respuesta, 'Publicación propia V11')
                self.assertLess(contenido.index('id="preinscripciones"'), contenido.index('id="publicaciones"'))
                self.assertLess(contenido.index('id="publicaciones"'), contenido.index('id="organizacion"'))
                self.assertNotContains(respuesta, 'name="tit_even"')
                self.assertNotContains(respuesta, 'Panel de Aprobaciones y Auditoría DAE')
                self.assertEqual(respuesta.context['puede_organizar'], rol in ('LIDER_ESTUDIANTIL', 'DELEGADO', 'JEFATURA', 'ADMIN'))

    # Consulta organización propia y luego con un rol sin contacto; verifica aislamiento, enlaces y privacidad del teléfono.
    def test_organizacion_propia_y_preinscritos(self):
        respuesta = self.client.get('/perfil/organizacion/')
        self.assertContains(respuesta, self.evento.tit_even)
        self.assertNotContains(respuesta, self.ajeno.tit_even)
        self.assertContains(respuesta, 'Ver preinscritos (2)')
        self.assertContains(respuesta, reverse('core:ver_perfil', args=[self.par.pk]))
        self.assertContains(respuesta, f'data-dm-usuario="{self.par.pk}"')
        self.assertContains(respuesta, self.par.tel_usu)
        Usuario.objects.filter(pk=self.persona.pk).update(rol_usu='ESTUDIANTE')
        respuesta = self.client.get('/perfil/organizacion/')
        self.assertContains(respuesta, self.evento.tit_even)
        self.assertNotContains(respuesta, self.par.tel_usu)
        self.assertNotContains(respuesta, 'Crear evento')

    # Solicita las pantallas por rol; comprueba que crear y gestionar conservan autorización fuera del perfil.
    def test_pantallas_separadas_y_permisos(self):
        self.assertTemplateUsed(self.client.get('/evento/solicitar/'), 'solicitar_evento.html')
        Usuario.objects.filter(pk=self.persona.pk).update(rol_usu='DAE')
        self.assertEqual(self.client.get('/evento/solicitar/').status_code, 403)
        respuesta = self.client.get('/perfil/gestion/')
        self.assertContains(respuesta, 'Panel de Aprobaciones y Auditoría DAE')
        self.assertContains(respuesta, self.ajeno.tit_even)
        self.assertNotContains(respuesta, 'name="tit_even"')
        self.assertEqual(self.client.get('/panel-admin/crear-cuenta/').status_code, 403)
        Usuario.objects.filter(pk=self.persona.pk).update(rol_usu='ADMIN')
        self.assertTemplateUsed(self.client.get('/panel-admin/crear-cuenta/'), 'crear_cuenta_institucional.html')
        Usuario.objects.filter(pk=self.persona.pk).update(rol_usu='ESTUDIANTE')
        self.assertEqual(self.client.get('/perfil/gestion/').status_code, 403)

    # Visita un perfil ajeno; verifica envío directo visible, secciones comunes y ausencia de herramientas privadas.
    def test_perfil_publico_con_acceso_directo_a_dm(self):
        self.client.force_login(self.par)
        respuesta = self.client.get(reverse('core:ver_perfil', args=[self.persona.pk]))
        self.assertContains(respuesta, 'Enviar mensaje')
        self.assertContains(respuesta, f'data-dm-usuario="{self.persona.pk}"')
        self.assertContains(respuesta, 'Eventos a los que se preinscribió')
        self.assertNotContains(respuesta, 'id="organizacion"')
        self.assertNotContains(respuesta, 'Mi panel de gestión')

    # Abre la entrada a mensajes y destinos manipulados; verifica fallback autenticado y que GET no envía ni marca lecturas.
    def test_entrada_mensajes_sin_efectos_en_get(self):
        mensaje = MensajeDirecto.objects.create(emi_mens=self.par, rec_mens=self.persona, cont_mens='Aviso ficticio V11')
        respuesta = self.client.get('/mensajes/', {'usuario': self.par.pk})
        self.assertContains(respuesta, f'data-usuario-id="{self.par.pk}"')
        self.assertContains(respuesta, 'Ver perfil')
        self.assertContains(respuesta, 'class="dm-flotante"')
        mensaje.refresh_from_db()
        self.assertFalse(mensaje.leid_mens)
        self.assertEqual(MensajeDirecto.objects.filter(emi_mens=self.persona).count(), 0)
        self.assertEqual(self.client.get('/mensajes/?usuario=abc').status_code, 400)
        self.assertEqual(self.client.get('/mensajes/', {'usuario': self.persona.pk}).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get('/mensajes/').status_code, 302)

    # Envía el cambio propio DAE a estudiante; verifica que el retorno siga accesible después de perder permisos de gestión.
    def test_cambio_de_rol_propio_redirige_a_perfil(self):
        Usuario.objects.filter(pk=self.persona.pk).update(rol_usu='DAE')
        self.assertRedirects(self.client.post(reverse('core:cambiar_rol', args=[self.persona.pk]), {'rol_usu': 'ESTUDIANTE'}), '/perfil/')


# Recibe una BD aislada; verifica configuración propia, altas institucionales, perfil limpio y DM persistente de v10.
class CuentasV10Tests(TestCase):
    # Prepara actores sintéticos con contraseñas de prueba y sede; no recibe datos externos ni devuelve valor.
    def setUp(self):
        self.sede = Sede.objects.create(nom_sede='Sede v10 ficticia', dir_sede='Demo')
        self.estudiante = Usuario.objects.create_user(username='alumno_v10', nom_usu='Alumno Ficticio', rut_usu='11111111-1', corr_usu='alumno_v10@inacapmail.cl', password='Anterior123!', sede_usu=self.sede)
        self.otro = Usuario.objects.create_user(username='otro_v10', rut_usu='22222222-2', corr_usu='otro_v10@inacapmail.cl', sede_usu=self.sede)
        self.admin = Usuario.objects.create_user(username='admin_v10', rut_usu='33333333-3', corr_usu='admin_v10@inacap.cl', sede_usu=self.sede, rol_usu='ADMIN')
        self.client.force_login(self.estudiante)

    # Recibe modificaciones opcionales y devuelve los campos configurables actuales del usuario ficticio.
    def configuracion(self, **cambios):
        datos = {'username': self.estudiante.username, 'corr_usu': self.estudiante.corr_usu, 'bio_usu': 'Bio ficticia'}
        datos.update(cambios)
        return datos

    # Recibe rol, nickname y RUT de prueba; devuelve datos válidos para crear una cuenta institucional.
    def cuenta(self, rol='DAE', username='nueva_dae', rut='44444444-4'):
        return {'nom_usu': 'Cuenta institucional ficticia', 'username': username, 'rut_usu': rut, 'corr_usu': f'{username}@inacap.cl', 'tel_usu': '000000000', 'sede_usu': self.sede.pk, 'carr_usu': 'Ing. Informática', 'rol_usu': rol, 'password': 'ClaveInicial-45!'}

    # Recibe cambio válido de nickname/correo/clave; verifica hash, sesión conservada e imposibilidad de editar rol/RUT.
    def test_configuracion_y_sesion(self):
        datos = self.configuracion(username='nuevo_nickname', corr_usu='NUEVO@INACAP.CL', nueva_password='Clave6', confirmar_password='Clave6', rol_usu='ADMIN', rut_usu='99999999-9')
        self.assertRedirects(self.client.post('/perfil/configuracion/', datos), '/perfil/')
        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.username, 'nuevo_nickname')
        self.assertEqual(self.estudiante.corr_usu, 'nuevo@inacap.cl')
        self.assertTrue(self.estudiante.check_password('Clave6'))
        self.assertEqual(self.estudiante.rol_usu, 'ESTUDIANTE')
        self.assertEqual(self.estudiante.rut_usu, '11111111-1')
        self.assertEqual(int(self.client.session['_auth_user_id']), self.estudiante.pk)
        self.assertEqual(self.client.get('/perfil/').status_code, 200)
        self.assertEqual(self.client.post('/perfil/', datos).status_code, 405)

    # Recibe duplicados, espacios, correo ajeno y contraseñas inválidas; verifica errores y ausencia de cambios persistidos.
    def test_validacion_configuracion(self):
        casos = [({'username': 'OTRO_V10'}, 'username'), ({'username': 'con espacio'}, 'username'),
                 ({'username': ' espacio'}, 'username'), ({'username': 'SISTEMA'}, 'username'),
                 ({'corr_usu': 'OTRO_V10@INACAPMAIL.CL'}, 'corr_usu'), ({'corr_usu': 'demo@gmail.com'}, 'corr_usu'),
                 ({'nueva_password': '12345', 'confirmar_password': '12345'}, 'nueva_password'),
                 ({'nueva_password': 'Clave6', 'confirmar_password': 'Otra66'}, 'confirmar_password')]
        for campos, campo in casos:
            respuesta = self.client.post('/perfil/configuracion/', self.configuracion(**campos))
            self.assertEqual(respuesta.status_code, 200)
            self.assertIn(campo, respuesta.context['form'].errors)
        self.estudiante.refresh_from_db()
        self.assertTrue(self.estudiante.check_password('Anterior123!'))
        self.assertRedirects(self.client.post('/perfil/configuracion/', self.configuracion()), '/perfil/')
        self.estudiante.refresh_from_db()
        self.assertTrue(self.estudiante.check_password('Anterior123!'))

    # Recibe altas DAE/JEFATURA autorizadas; comprueba contraseña cifrada, bienvenida, auditoría y sesión del creador intacta.
    def test_crear_cuentas_institucionales(self):
        self.client.force_login(self.admin)
        for rol, nombre, rut in [('DAE', 'nueva_dae', '44444444-4'), ('JEFATURA', 'nueva_jefatura', '55555555-5')]:
            self.assertRedirects(self.client.post('/panel-admin/crear-cuenta/', self.cuenta(rol, nombre, rut)), '/perfil/gestion/')
            usuario = Usuario.objects.get(username=nombre)
            self.assertEqual(usuario.rol_usu, rol)
            self.assertTrue(usuario.check_password('ClaveInicial-45!'))
            self.assertNotEqual(usuario.password, 'ClaveInicial-45!')
            self.assertFalse(usuario.is_staff or usuario.is_superuser)
            self.assertTrue(MensajeDirecto.objects.filter(emi_mens__username='sistema', rec_mens=usuario, cont_mens__contains='Bienvenido').exists())
            self.assertTrue(RegistroAuditoria.objects.filter(dae_audi=self.admin, acc_audi='Creó cuenta institucional', det_audi__contains=f'@{nombre}').exists())
        self.assertEqual(int(self.client.session['_auth_user_id']), self.admin.pk)

    # Recibe accesos sin rol, superusuario y datos institucionales inválidos; verifica permisos y rechazo de campos no permitidos.
    def test_permisos_y_validacion_alta(self):
        self.assertEqual(self.client.post('/panel-admin/crear-cuenta/', self.cuenta()).status_code, 403)
        self.admin.rol_usu = 'DAE'
        self.admin.save()
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get('/panel-admin/crear-cuenta/').status_code, 403)
        self.admin.is_superuser = True
        self.admin.save()
        self.assertEqual(self.client.get('/panel-admin/crear-cuenta/').status_code, 200)
        for cambios, campo in [({'username': 'OTRO_V10'}, 'username'), ({'rut_usu': '44444444-5'}, 'rut_usu'), ({'rut_usu': '11.111.111-1'}, 'rut_usu'), ({'corr_usu': 'demo@gmail.com'}, 'corr_usu'), ({'rol_usu': 'ESTUDIANTE'}, 'rol_usu')]:
            respuesta = self.client.post('/panel-admin/crear-cuenta/', {**self.cuenta(), **cambios})
            self.assertIn(campo, respuesta.context['form'].errors)
        self.assertFalse(Usuario.objects.filter(username='nueva_dae').exists())

    # Simula fallo de auditoría al crear cuenta; comprueba reversión atómica de usuario y bienvenida oficial.
    def test_rollback_alta(self):
        self.client.force_login(self.admin)
        with patch('core.views.RegistroAuditoria.objects.create', side_effect=RuntimeError('Fallo simulado')):
            with self.assertRaises(RuntimeError):
                self.client.post('/panel-admin/crear-cuenta/', self.cuenta())
        self.assertFalse(Usuario.objects.filter(username='nueva_dae').exists())
        self.assertFalse(MensajeDirecto.objects.filter(cont_mens__contains='Cuenta institucional ficticia').exists())

    # Recibe rutas autenticadas del flujo estudiantil; verifica un solo DM global, Bootstrap Icons y ausencia de formularios antiguos en perfil.
    def test_dm_global_y_perfil_limpio(self):
        for ruta in ['/', '/foro/', '/mensajes/', '/perfil/', '/perfil/configuracion/', '/club/postular/']:
            respuesta = self.client.get(ruta)
            self.assertEqual(respuesta.status_code, 200)
            html = respuesta.content.decode()
            self.assertEqual(html.count('id="dmDrawer"'), 1)
            self.assertIn('class="dm-flotante"', html)
            self.assertIn('js/dm_drawer.js', html)
            self.assertIn('bootstrap-icons@1.11.3', html)
        perfil = self.client.get('/perfil/')
        self.assertContains(perfil, 'bi-gear-fill')
        self.assertNotContains(perfil, 'name="foto_usu"')
        self.assertNotContains(perfil, 'name="avales"')
        self.assertNotContains(perfil, 'Editar Foto y Biografía')
        self.client.force_login(self.otro)
        self.assertNotContains(self.client.get(f'/perfil/{self.estudiante.pk}/'), 'bi-gear-fill')

    # Recibe inscripciones futuras/pasadas y pendientes; verifica prioridad, filtros y cancelación que retorna al perfil.
    def test_proximos_inscritos(self):
        eventos = []
        for titulo, dias, estado in [('Próximo aprobado', 2, 'APROBADO'), ('Pasado', -2, 'APROBADO'), ('Pendiente', 3, 'PENDIENTE_DAE')]:
            inicio = timezone.now() + timedelta(days=dias)
            evento = Evento.objects.create(tit_even=titulo, desc_even='Demo', cat_even='TODO_PUBLICO', sede_even=self.sede, crea_even=self.admin, esp_even='Patio', fech_even=inicio, ffin_even=inicio + timedelta(hours=1), est_even=estado)
            evento.asis_even.add(self.estudiante)
            eventos.append(evento)
        respuesta = self.client.get('/perfil/')
        self.assertQuerySetEqual(respuesta.context['proximos_inscritos'], [eventos[0]], transform=None)
        html = respuesta.content.decode()
        self.assertLess(html.index('Eventos a los que me preinscribí'), html.index('Publicaciones realizadas por mí'))
        self.assertRedirects(self.client.post(reverse('core:preinscripcion', args=[eventos[0].pk]), {'volver': 'perfil'}), '/perfil/')
        self.assertFalse(eventos[0].asis_even.filter(pk=self.estudiante.pk).exists())

    # Recibe postulación dedicada con cuatro compañeros; verifica formulario fuera del perfil y listado de estado tras enviar.
    def test_postulacion_dedicada(self):
        pares = [self.otro]
        for numero in range(3):
            pares.append(Usuario.objects.create_user(username=f'par_v10_{numero}', rut_usu=f'FICTICIO-V10-{numero}', corr_usu=f'par{numero}@inacapmail.cl', sede_usu=self.sede))
        respuesta = self.client.post('/club/postular/', {'nom_club': 'Club dedicado v10', 'cat_club': 'OTRO', 'desc_club': 'Demo', 'avales': [p.pk for p in pares]})
        self.assertRedirects(respuesta, '/club/postular/')
        pagina = self.client.get('/club/postular/')
        self.assertContains(pagina, 'Club dedicado v10')
        self.assertContains(pagina, '0/4 avales aceptados')


# Recibe una BD aislada y prueba búsqueda, DMs privados, canal oficial y dashboards segmentados de v9.
class MensajeriaV9Tests(TestCase):
    # Prepara participantes ficticios de dos carreras y sedes, más gestores; no recibe datos externos ni devuelve valor.
    def setUp(self):
        self.sede = Sede.objects.create(nom_sede='Sede DM A', dir_sede='Demo')
        self.otra = Sede.objects.create(nom_sede='Sede DM B', dir_sede='Demo')
        self.alicia = self.usuario('luz_nova', 'Alicia Ficticia', carrera='Ing. Informática')
        self.beto = self.usuario('betito', 'Roberto Ficticio', carrera='Técnico Mecánica')
        self.tercero = self.usuario('tercero', 'Otra Persona', sede=self.otra)
        self.dae = self.usuario('gestor', 'DAE Ficticio', rol='DAE')
        self.jefe = self.usuario('jefatura', 'Jefatura Ficticia', rol='JEFATURA', carrera=self.alicia.carr_usu)
        self.client.force_login(self.alicia)

    # Recibe datos de prueba y devuelve una cuenta sintética con identificador único y año de ingreso para gráficos temporales.
    def usuario(self, nickname, nombre, rol='ESTUDIANTE', carrera='Ing. Informática', sede=None):
        return Usuario.objects.create_user(username=nickname, nom_usu=nombre, rut_usu=f'DEMO-{nickname}', corr_usu=f'{nickname}@inacapmail.cl', rol_usu=rol, sede_usu=sede or self.sede, carr_usu=carrera)

    # Recibe búsquedas por nombre y nickname; comprueba privacidad, exclusiones y selección de avalistas solo de la sede.
    def test_busqueda_unificada(self):
        for consulta in ['Roberto', '@betito']:
            usuarios = self.client.get('/api/buscar-usuarios/', {'q': consulta}).json()['usuarios']
            self.assertEqual([u['id'] for u in usuarios], [self.beto.pk])
            self.assertNotIn('rut_usu', usuarios[0])
            self.assertNotIn('tel_usu', usuarios[0])
            self.assertTrue(usuarios[0]['perfil_url'].endswith(f'/{self.beto.pk}/'))
        self.assertEqual(self.client.get('/api/buscar-usuarios/?q=@sistema').json()['usuarios'], [])
        self.assertEqual(self.client.get('/api/buscar-usuarios/?q=luz_nova').json()['usuarios'], [])
        self.assertEqual(self.client.get('/api/buscar-usuarios/?q=tercero&solo_sede=1').json()['usuarios'], [])
        self.assertEqual(self.client.get('/api/buscar-usuarios/?q=gestor&solo_sede=1').json()['usuarios'], [])
        self.beto.is_active = False
        self.beto.save()
        self.assertEqual(self.client.get('/api/buscar-usuarios/?q=betito').json()['usuarios'], [])

    # Recibe POST de dos participantes; verifica CSRF, autor impuesto, lectura por POST y ausencia de mensajes ajenos en otro hilo.
    def test_dm_csrf_lectura_y_privacidad(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.alicia)
        enviar = reverse('core:dm_enviar', args=[self.beto.pk])
        self.assertEqual(cliente.post(enviar, {'cont_mens': 'Hola ficticio'}).status_code, 403)
        cliente.get('/')
        token = cliente.cookies['csrftoken'].value
        respuesta = cliente.post(enviar, {'cont_mens': 'Hola ficticio', 'emi_mens': self.tercero.pk}, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(respuesta.status_code, 201)
        mensaje = MensajeDirecto.objects.get(pk=respuesta.json()['id'])
        self.assertEqual(mensaje.emi_mens, self.alicia)
        self.assertFalse(mensaje.leid_mens)
        self.client.force_login(self.beto)
        hilo = reverse('core:dm_hilo', args=[self.alicia.pk])
        self.assertEqual(self.client.get(hilo).json()['mensajes'][0]['contenido'], 'Hola ficticio')
        mensaje.refresh_from_db()
        self.assertFalse(mensaje.leid_mens)
        self.client.post(reverse('core:dm_leer', args=[self.alicia.pk]), {'hasta_id': mensaje.pk})
        mensaje.refresh_from_db()
        self.assertTrue(mensaje.leid_mens)
        self.client.force_login(self.tercero)
        self.assertEqual(self.client.get(hilo).json()['mensajes'], [])
        self.client.post(reverse('core:dm_leer', args=[self.alicia.pk]))
        self.assertEqual(MensajeDirecto.objects.filter(emi_mens=self.alicia, rec_mens=self.beto).count(), 1)

    # Recibe un hilo con recibidos y salientes; comprueba contador, orden oficial fijo y marcado automático al enviar.
    def test_lectura_al_enviar_y_conversaciones(self):
        mensaje = MensajeDirecto.objects.create(emi_mens=self.beto, rec_mens=self.alicia, cont_mens='Recibido')
        datos = self.client.get('/api/dm/conversaciones/').json()
        self.assertEqual(datos['no_leidos'], 1)
        self.assertEqual(datos['conversaciones'][0]['username'], 'sistema')
        self.client.post(reverse('core:dm_enviar', args=[self.beto.pk]), {'cont_mens': 'Respuesta'})
        mensaje.refresh_from_db()
        self.assertTrue(mensaje.leid_mens)
        self.assertEqual(self.client.get('/api/dm/conversaciones/').json()['no_leidos'], 0)
        self.assertEqual(self.client.get(reverse('core:dm_enviar', args=[self.beto.pk])).status_code, 405)
        self.assertEqual(self.client.post(reverse('core:dm_enviar', args=[self.beto.pk]), {'cont_mens': '  '}).status_code, 400)

    # Recibe una notificación oficial y una respuesta humana; verifica identidad, contraseña inutilizable y bloqueo de respuesta.
    def test_sistema_y_notificaciones(self):
        from .utils import asegurar_usuario_sistema, enviar_notificacion_sistema
        sistema = asegurar_usuario_sistema()
        self.assertEqual(sistema.nom_usu, 'LuxNova Sistema')
        self.assertFalse(sistema.has_usable_password())
        self.assertFalse(sistema.is_staff or sistema.is_superuser)
        mensaje = enviar_notificacion_sistema(self.alicia, 'Notificación ficticia')
        self.assertEqual(mensaje.emi_mens, sistema)
        self.assertEqual(self.client.post(reverse('core:dm_enviar', args=[sistema.pk]), {'cont_mens': 'No permitido'}).status_code, 403)
        aviso = MensajeInbox.objects.create(dest_inbo=self.alicia, tipo_inbo='SISTEMA', asun_inbo='Club aprobado', cuer_inbo='Aviso de prueba')
        self.assertTrue(MensajeDirecto.objects.filter(rec_mens=self.alicia, emi_mens=sistema, cont_mens__contains=aviso.asun_inbo).exists())
        total = MensajeDirecto.objects.count()
        aviso.leid_inbo = True
        aviso.save()
        self.assertEqual(MensajeDirecto.objects.count(), total)

    # Recibe un alta válida por la vista; verifica que bienvenida y sesión queden conectadas con el canal oficial.
    def test_bienvenida_registro(self):
        self.client.logout()
        datos = {'username': 'nuevo_v9', 'nom_usu': 'Persona Ficticia', 'rut_usu': '88888888-8', 'corr_usu': 'nuevo_v9@inacapmail.cl', 'tel_usu': '000000000', 'sede_usu': self.sede.pk, 'carr_usu': 'Ing. Informática', 'password1': 'ClaveFicticia-894!', 'password2': 'ClaveFicticia-894!'}
        self.assertRedirects(self.client.post('/registro/', datos), '/')
        usuario = Usuario.objects.get(username='nuevo_v9')
        self.assertTrue(MensajeDirecto.objects.filter(rec_mens=usuario, emi_mens__username='sistema', cont_mens__contains='Bienvenido').exists())

    # Recibe RUTs sintéticos con DV y formato variable; verifica ocultamiento de cuatro dígitos del cuerpo y ausencia de DV.
    def test_rut_enmascarado(self):
        from .templatetags.privacidad import enmascarar_rut
        self.assertEqual(enmascarar_rut('12.345.678-9'), '1234****')
        self.assertEqual(enmascarar_rut('12345678-K'), '1234****')
        self.assertEqual(enmascarar_rut('123-4'), '***')
        self.assertEqual(enmascarar_rut(None), '****')

    # Recibe un evento con dos carreras; verifica gráficos y RUTs enmascarados para DAE, sin botón ni endpoint de preinscripción.
    def test_dae_dashboard_y_evento(self):
        self.alicia.rut_usu = '12345678-5'
        self.alicia.save()
        evento = Evento.objects.create(tit_even='Evento dashboard', desc_even='Demo', cat_even='TODO_PUBLICO', esp_even='Patio', sede_even=self.sede, crea_even=self.dae, est_even='APROBADO', fech_even=timezone.now() + timedelta(days=3), ffin_even=timezone.now() + timedelta(days=3, hours=2))
        evento.asis_even.add(self.alicia, self.beto)
        self.client.force_login(self.dae)
        perfil = self.client.get('/perfil/')
        self.assertNotContains(perfil, 'Solicitar Reserva de Espacio / Crear Evento')
        self.assertEqual(self.client.post('/evento/solicitar/', {}).status_code, 403)
        self.assertEqual(self.client.post(reverse('core:preinscripcion', args=[evento.pk])).status_code, 403)
        home = self.client.get('/')
        self.assertContains(home, 'Consultar RUTs')
        self.assertContains(home, '1234****')
        self.assertNotContains(home, self.alicia.rut_usu)
        self.assertNotContains(home, 'Pre-inscribirme')
        self.assertNotContains(home, 'año de ingreso')
        self.assertContains(home, 'Inscritos por carrera')
        filas = self.client.get('/perfil/gestion/').context['dashboard_participacion']['barras']
        self.assertEqual(sum(f['total'] for f in filas), 2)
        self.client.force_login(self.jefe)
        filas = self.client.get('/perfil/gestion/').context['dashboard_participacion']['barras']
        self.assertEqual(sum(f['total'] for f in filas), 1)
        self.client.force_login(self.alicia)
        self.assertNotContains(self.client.get('/'), 'Consultar RUTs')


# Usa conexiones PostgreSQL independientes; recibe una base transaccional y verifica dos aprobaciones simultáneas en el mismo espacio.
class ConcurrenciaV6Tests(TransactionTestCase):
    # Recibe IDs de DAE y evento; abre conexión propia, ejecuta aprobación y devuelve el estado HTTP cerrando sus conexiones.
    def aprobar_en_hilo(self, usuario_id, evento_id):
        from django.db import close_old_connections, connections
        close_old_connections()
        try:
            cliente = Client()
            cliente.force_login(Usuario.objects.get(pk=usuario_id))
            return cliente.post(reverse('core:resolver_evento', args=[evento_id, 'aprobar'])).status_code
        finally:
            connections.close_all()

    # Crea dos solicitudes idénticas y dos DAE; ejecuta en paralelo y verifica una sola aprobación y auditoría.
    def test_aprobaciones_simultaneas(self):
        from concurrent.futures import ThreadPoolExecutor
        sede = Sede.objects.create(nom_sede='Sede concurrencia ficticia', dir_sede='Demo')
        usuarios = [Usuario.objects.create_user(username=f'dae_concurrente{i}', rut_usu=f'DEMO-CONC-{i}', corr_usu=f'dae{i}@inacap.cl', rol_usu='DAE', sede_usu=sede) for i in range(2)]
        fecha = timezone.now() + timedelta(days=5)
        eventos = [Evento.objects.create(tit_even=f'Solicitud demo {i}', desc_even='Demo', cat_even='TODO_PUBLICO', sede_even=sede, esp_even='Auditorio Principal', fech_even=fecha, ffin_even=fecha + timedelta(hours=2), crea_even=usuarios[i]) for i in range(2)]
        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            tareas = [ejecutor.submit(self.aprobar_en_hilo, u.pk, e.pk) for u, e in zip(usuarios, eventos)]
            self.assertEqual([t.result(timeout=20) for t in tareas], [302, 302])
        self.assertEqual(Evento.objects.filter(est_even='APROBADO').count(), 1)
        self.assertEqual(Evento.objects.filter(est_even='PENDIENTE_DAE').count(), 1)
        self.assertEqual(RegistroAuditoria.objects.count(), 1)


# Verifica inicio/término y límites de reservas v8; recibe una BD aislada y devuelve aserciones de formulario, aprobación y visualización.
class IntervalosV8Tests(TestCase):
    # Crea DAE, dos sedes e intervalo base futuro; no recibe entradas externas ni devuelve valor.
    def setUp(self):
        self.sede = Sede.objects.create(nom_sede='Sede intervalos demo', dir_sede='Ficticia')
        self.otra = Sede.objects.create(nom_sede='Otra sede intervalos', dir_sede='Ficticia')
        self.dae = Usuario.objects.create_user(username='dae_v8', rut_usu='DEMO-V8', corr_usu='dae_v8@inacap.cl', rol_usu='DAE', sede_usu=self.sede)
        self.base = (timezone.now() + timedelta(days=8)).replace(second=0, microsecond=0)
        self.client.force_login(self.dae)

    # Recibe horas relativas de inicio/fin y campos opcionales; devuelve un evento sintético con intervalo explícito.
    def evento(self, inicio, fin, **campos):
        datos = {'orga_even': 'PERSONAL', 'tit_even': 'Reserva ficticia', 'desc_even': 'Demo', 'cat_even': 'TODO_PUBLICO', 'sede_even': self.sede, 'esp_even': 'Auditorio Principal', 'crea_even': self.dae, 'fech_even': self.base + timedelta(hours=inicio), 'ffin_even': self.base + timedelta(hours=fin) if fin is not None else None}
        datos.update(campos)
        return Evento.objects.create(**datos)

    # Recibe inicio y término relativos; devuelve datos HTML5 de solicitud en hora local.
    def datos(self, inicio=0, fin=2):
        return {'orga_even': 'PERSONAL', 'tit_even': 'Solicitud v8', 'desc_even': 'Demo', 'cat_even': 'TODO_PUBLICO', 'alc_even': 'SEDE', 'esp_even': 'Auditorio Principal', 'fech_even': timezone.localtime(self.base + timedelta(hours=inicio)).strftime('%Y-%m-%dT%H:%M'), 'ffin_even': timezone.localtime(self.base + timedelta(hours=fin)).strftime('%Y-%m-%dT%H:%M')}

    # Recibe fin igual/anterior/ausente; verifica rechazo de formularios y aceptación de un intervalo futuro válido.
    def test_orden_y_obligatoriedad(self):
        from .forms import SolicitarEventoForm
        for fin in [0, -1]:
            form = SolicitarEventoForm(self.datos(fin=fin))
            self.assertFalse(form.is_valid())
            self.assertIn('La fecha y hora de término debe ser posterior a la de inicio.', form.non_field_errors())
        datos = self.datos()
        del datos['ffin_even']
        self.assertIn('ffin_even', SolicitarEventoForm(datos).errors)
        form = SolicitarEventoForm(self.datos())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.fields['ffin_even'].widget.input_type, 'datetime-local')

    # Recibe intervalos con cruce, contención y extremos compartidos; verifica el predicado real sin ventana fija de dos horas.
    def test_predicado_intervalos(self):
        from .views import conflicto_espacio
        self.evento(0, 10, est_even='APROBADO')
        for inicio, fin in [(3, 4), (-1, 1), (9, 11), (-2, 12), (0, 10)]:
            self.assertTrue(conflicto_espacio(self.evento(inicio, fin)))
        for inicio, fin in [(-3, 0), (10, 11), (11, 12)]:
            self.assertFalse(conflicto_espacio(self.evento(inicio, fin)))
        self.assertFalse(conflicto_espacio(self.evento(1, 2, sede_even=self.otra)))
        self.assertFalse(conflicto_espacio(self.evento(1, 2, esp_even='Sala Multiuso 101')))

    # Recibe un cruce mayor a dos horas desde el inicio y uno contiguo; verifica bloqueo real y aprobación válida desde DAE.
    def test_aprobar_y_crear_directamente(self):
        self.evento(0, 6, est_even='APROBADO')
        pendiente = self.evento(4, 5)
        self.assertContains(self.client.post(reverse('core:resolver_evento', args=[pendiente.pk, 'aprobar']), follow=True), 'Conflicto de espacio:')
        pendiente.refresh_from_db()
        self.assertEqual(pendiente.est_even, 'PENDIENTE_DAE')
        self.assertFalse(RegistroAuditoria.objects.exists())
        Usuario.objects.filter(pk=self.dae.pk).update(rol_usu='ADMIN')
        self.assertContains(self.client.post('/evento/solicitar/', self.datos(4, 5)), 'Conflicto de espacio:')
        self.assertEqual(Evento.objects.count(), 2)
        self.assertRedirects(self.client.post('/evento/solicitar/', self.datos(6, 7)), '/perfil/organizacion/')
        nuevo = Evento.objects.get(tit_even='Solicitud v8')
        self.assertEqual(nuevo.est_even, 'APROBADO')
        self.assertEqual(nuevo.ffin_even, self.base + timedelta(hours=7))
        self.assertContains(self.client.get('/'), 'Término')
        self.assertContains(self.client.get('/perfil/organizacion/'), 'Inicio:')

    # Recibe filas históricas sin término y un término inválido; impide aprobarlas y mantiene ocupación conservadora de las aprobadas.
    def test_compatibilidad_historica(self):
        from .views import conflicto_espacio
        pendiente = self.evento(0, None)
        url = reverse('core:resolver_evento', args=[pendiente.pk, 'aprobar'])
        self.assertContains(self.client.post(url, follow=True), 'necesita una fecha de término')
        Evento.objects.filter(pk=pendiente.pk).update(ffin_even=pendiente.fech_even)
        self.client.post(url)
        pendiente.refresh_from_db()
        self.assertEqual(pendiente.est_even, 'PENDIENTE_DAE')
        self.evento(0, None, est_even='APROBADO')
        self.assertTrue(conflicto_espacio(self.evento(5, 6)))


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
        notificaciones = MensajeDirecto.objects.filter(cont_mens__contains='completó sus 4 avales')
        self.assertEqual(set(notificaciones.values_list('rec_mens_id', flat=True)), {self.creador.pk, self.dae.pk})
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
        self.assertEqual(MensajeDirecto.objects.filter(rec_mens=self.creador, cont_mens__contains='rechazó el aval').count(), 1)

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

    # Recibe un aval y mensajes propios/ajenos; verifica acciones en DM oficial y lectura separada del buz?n.
    def test_lectura_y_contador(self):
        usuario = self.avales[0].estu_aval
        self.client.force_login(usuario)
        self.assertEqual(self.client.get('/inbox/').status_code, 403)
        sistema = Usuario.objects.get(username='sistema')
        url = reverse('core:dm_hilo', args=[sistema.pk])
        datos = self.client.get(url).json()
        solicitud = next(m for m in datos['mensajes'] if m.get('aval'))
        self.assertTrue(solicitud['aval']['pendiente'])
        self.assertEqual(solicitud['aval']['id'], self.avales[0].pk)
        self.responder(self.avales[0])
        datos = self.client.get(url).json()
        solicitud = next(m for m in datos['mensajes'] if m.get('aval'))
        self.assertFalse(solicitud['aval']['pendiente'])
        self.assertEqual(solicitud['aval']['estado'], 'ACEPTADO')

    # Recibe iniciativas propias, ajenas y de otra sede; verifica filtro servidor por rol, destinatario y sede.
    def test_privacidad_iniciativas(self):
        publicacion = PublicacionForo.objects.create(aut_publ=self.creador, sede_publ=self.sede, cont_publ='Demo', etiq_publ='INICIATIVA')
        otra = PublicacionForo.objects.create(aut_publ=self.dae_ajeno, sede_publ=self.otra, cont_publ='Demo', etiq_publ='INICIATIVA')
        for usuario in [self.creador, self.dae]:
            MensajeInbox.objects.create(dest_inbo=usuario, tipo_inbo='INICIATIVA_BUZON', publ_inbo=publicacion, asun_inbo='Iniciativa demo', cuer_inbo='CONTACTO-PRIVADO-DEMO')
        MensajeInbox.objects.create(dest_inbo=self.dae, tipo_inbo='INICIATIVA_BUZON', publ_inbo=otra, asun_inbo='Iniciativa ajena', cuer_inbo='CONTACTO-OTRA-SEDE')
        self.client.force_login(self.creador)
        self.assertEqual(self.client.get('/inbox/').status_code, 403)
        self.client.force_login(self.dae)
        respuesta = self.client.get('/inbox/')
        self.assertContains(respuesta, 'CONTACTO-PRIVADO-DEMO')
        self.assertNotContains(respuesta, 'CONTACTO-OTRA-SEDE')

    # Recibe correos de diversos dominios; verifica dos permitidos y rechazo de dominios similares o externos.
    def test_dominios(self):
        from .forms import RegistroUsuarioForm
        datos = {'username': 'nueva', 'nom_usu': 'Persona ficticia', 'rut_usu': '88888888-8', 'tel_usu': '000000000', 'sede_usu': self.sede.pk, 'carr_usu': 'Ing. Informática', 'password1': 'ClaveDemo-573!', 'password2': 'ClaveDemo-573!'}
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
        self.assertEqual(MensajeDirecto.objects.filter(aval_mens__club_aval=club).count(), 4)
        for username in ['est1', 'est2', 'est3', 'est4', 'est5', 'lider_rancagua', 'dae_rancagua']:
            usuario = Usuario.objects.get(username=username)
            dominio = 'inacap.cl' if username == 'dae_rancagua' else 'inacapmail.cl'
            correo = {'dae_rancagua': 'dae.rancagua@inacap.cl', 'lider_rancagua': 'lider.rancagua@inacapmail.cl'}.get(username, f'{username}@{dominio}')
            self.assertEqual(usuario.corr_usu, correo)
        for username, clave in [('root_admin', 'Admin1234!'), ('dae_rancagua', 'Dae1234!'), ('jefe_informatica', 'Jefe1234!'), ('lider_rancagua', 'Lider1234!')] + [(f'est{i}', 'Est1234!') for i in range(1, 6)]:
            usuario = Usuario.objects.get(username=username)
            self.assertTrue(usuario.check_password(clave))
            self.assertEqual(validar_rut_chileno(usuario.rut_usu), usuario.rut_usu)
        root = Usuario.objects.get(username='root_admin')
        self.assertTrue(root.is_staff and root.is_superuser)

    # Simula fallo al generar avisos del cuarto aval; verifica rollback de respuesta, estado del club y lectura del mensaje.
    def test_rollback_cuarto_aval(self):
        for aval in self.avales[:3]:
            self.responder(aval)
        with patch('core.services.enviar_notificacion_sistema', side_effect=RuntimeError('Fallo simulado')):
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
        datos = {'username': 'nuevo', 'nom_usu': 'Persona ficticia', 'rut_usu': '44444444-4', 'corr_usu': 'nuevo@inacapmail.cl', 'tel_usu': '000000000', 'sede_usu': self.sede.pk, 'carr_usu': 'Ing. Informática', 'password1': 'ClaveFicticia-783!', 'password2': 'ClaveFicticia-783!'}
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
        self.assertEqual(Usuario.objects.exclude(username='sistema').count(), 3)
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
        self.assertRedirects(self.client.post('/perfil/configuracion/', {'bio_usu': 'Bio ficticia', 'username': self.estudiante.username, 'corr_usu': self.estudiante.corr_usu, 'rol_usu': 'ADMIN'}), '/perfil/')
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
            self.assertRedirects(self.client.post('/perfil/configuracion/', {'bio_usu': 'Demo', 'username': self.estudiante.username, 'corr_usu': self.estudiante.corr_usu, 'foto_usu': foto}), '/perfil/')
            self.estudiante.refresh_from_db()
            self.assertTrue(self.estudiante.foto_usu.name.startswith('perfiles/'))
            falsa = SimpleUploadedFile('falsa.png', b'no es una imagen', content_type='image/png')
            respuesta = self.client.post('/perfil/configuracion/', {'bio_usu': 'Demo', 'username': self.estudiante.username, 'corr_usu': self.estudiante.corr_usu, 'foto_usu': falsa})
            self.assertIn('foto_usu', respuesta.context['form'].errors)
            self.assertRedirects(self.client.post('/perfil/configuracion/', {'bio_usu': 'Demo', 'username': self.estudiante.username, 'corr_usu': self.estudiante.corr_usu, 'foto_usu-clear': 'on'}), '/perfil/')
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
        datos = {'username': 'nueva', 'nom_usu': 'Nueva Alumna', 'rut_usu': '11111111-1', 'corr_usu': 'NUEVA@inacap.cl', 'tel_usu': '912345678', 'sede_usu': self.sede.pk, 'carr_usu': 'Ing. Informática', 'password1': 'UnaClaveLarga-549!', 'password2': 'UnaClaveLarga-549!', 'rol_usu': 'ADMIN'}
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
        self.assertEqual(respuesta.context['inbox_no_leidos'], 0)
        Evento.objects.filter(pk=self.evento.pk).update(fech_even=timezone.now() - timedelta(days=1))
        Evento.objects.filter(pk=self.ajeno.pk).update(est_even='PENDIENTE_DAE')
        respuesta = self.client.get('/')
        self.assertFalse(respuesta.context['eventos_sede'].exists())
        self.assertFalse(respuesta.context['eventos_intersede'].exists())
        for nombre in ['ahora_mismo', 'perfil']:
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



# Comprueba el recorrido final y sus permisos; recibe una base aislada y devuelve aserciones de club, eventos y auditoría.
class CierreV6Tests(TestCase):
    # Crea actores y sedes ficticios; no recibe datos externos ni devuelve valor.
    def setUp(self):
        self.sede = Sede.objects.create(nom_sede='Sede v6', dir_sede='Demo')
        self.otra = Sede.objects.create(nom_sede='Otra v6', dir_sede='Demo')
        self.estudiante = self.usuario('estudiante', 'ESTUDIANTE')
        self.dae = self.usuario('dae', 'DAE')
        self.jefe = self.usuario('jefe', 'JEFATURA')
        self.pares = [self.usuario(f'par{i}', 'ESTUDIANTE') for i in range(4)]

    # Recibe nombre, rol y sede opcional; devuelve una cuenta sintética única para las pruebas.
    def usuario(self, nombre, rol, sede=None):
        return Usuario.objects.create_user(username=f'v6_{nombre}', nom_usu=f'Demo {nombre}', rut_usu=f'FICTICIO-V6-{nombre}', corr_usu=f'{nombre}@inacapmail.cl', rol_usu=rol, sede_usu=sede or self.sede)

    # Recibe campos opcionales; devuelve un POST de evento futuro con hora local y espacio permitido.
    def datos_evento(self, **cambios):
        datos = {'orga_even': 'PERSONAL', 'tit_even': 'Evento v6', 'desc_even': 'Demostración ficticia', 'cat_even': 'TODO_PUBLICO', 'alc_even': 'SEDE', 'esp_even': 'Auditorio Principal', 'fech_even': timezone.localtime(timezone.now() + timedelta(days=7)).strftime('%Y-%m-%dT%H:%M'), 'ffin_even': timezone.localtime(timezone.now() + timedelta(days=7, hours=2)).strftime('%Y-%m-%dT%H:%M')}
        datos.update(cambios)
        return datos

    # Recibe el recorrido completo; verifica cuatro avales, ascenso, auditoría, reserva y publicación del evento aprobado.
    def test_flujo_completo(self):
        self.client.force_login(self.estudiante)
        self.assertRedirects(self.client.post('/club/postular/', {'nom_club': 'Club v6', 'cat_club': 'OTRO', 'desc_club': 'Demo', 'avales': [u.pk for u in self.pares]}), '/club/postular/')
        club = Club.objects.get(nom_club='Club v6')
        self.assertEqual(club.est_club, 'PENDIENTE_AVALES')
        self.assertEqual(club.avales.count(), 4)
        self.assertEqual(MensajeDirecto.objects.filter(aval_mens__club_aval=club).count(), 4)
        for aval in club.avales.select_related('estu_aval'):
            self.client.force_login(aval.estu_aval)
            self.client.post(reverse('core:responder_aval', args=[aval.pk]), {'decision': 'ACEPTADO'})
        club.refresh_from_db()
        self.assertEqual(club.est_club, 'PENDIENTE_DAE')
        self.client.force_login(self.dae)
        url = reverse('core:resolver_club', args=[club.pk, 'aprobar'])
        self.assertRedirects(self.client.post(url), '/perfil/gestion/')
        club.refresh_from_db()
        self.estudiante.refresh_from_db()
        self.assertEqual(club.est_club, 'APROBADO')
        self.assertEqual(self.estudiante.rol_usu, 'LIDER_ESTUDIANTIL')
        self.assertTrue(RegistroAuditoria.objects.filter(acc_audi='Aprobó Club Estudiantil', dae_audi=self.dae).exists())
        self.client.post(url)
        self.assertEqual(RegistroAuditoria.objects.count(), 1)
        self.client.force_login(self.estudiante)
        self.assertRedirects(self.client.post('/evento/solicitar/', self.datos_evento()), '/perfil/organizacion/')
        evento = Evento.objects.get(tit_even='Evento v6')
        self.assertEqual(evento.est_even, 'PENDIENTE_DAE')
        self.client.force_login(self.dae)
        self.assertRedirects(self.client.post(reverse('core:resolver_evento', args=[evento.pk, 'aprobar'])), '/perfil/gestion/')
        self.assertContains(self.client.get('/'), 'Evento v6')
        self.assertEqual(RegistroAuditoria.objects.count(), 2)
        self.client.force_login(self.jefe)
        self.assertContains(self.client.get('/perfil/gestion/'), self.estudiante.nom_usu)

    # Crea intervalos aprobados y pendientes; verifica cruce real, aceptación de eventos contiguos y creación directa sin conflicto.
    def test_solapamiento(self):
        base = timezone.now() + timedelta(days=5)
        aprobado = Evento.objects.create(tit_even='Ocupado', desc_even='Demo', cat_even='TODO_PUBLICO', sede_even=self.sede, esp_even='Auditorio Principal', fech_even=base, ffin_even=base + timedelta(hours=4), crea_even=self.dae, est_even='APROBADO')
        pendiente = Evento.objects.create(tit_even='Pendiente', desc_even='Demo', cat_even='TODO_PUBLICO', sede_even=self.sede, esp_even='auditorio principal', fech_even=base + timedelta(hours=3), ffin_even=base + timedelta(hours=5), crea_even=self.jefe)
        self.client.force_login(self.dae)
        url = reverse('core:resolver_evento', args=[pendiente.pk, 'aprobar'])
        self.assertContains(self.client.post(url, follow=True), 'Conflicto de espacio:')
        pendiente.refresh_from_db()
        self.assertEqual(pendiente.est_even, 'PENDIENTE_DAE')
        self.assertFalse(RegistroAuditoria.objects.exists())
        Evento.objects.filter(pk=pendiente.pk).update(fech_even=aprobado.ffin_even)
        self.client.post(url)
        pendiente.refresh_from_db()
        self.assertEqual(pendiente.est_even, 'APROBADO')
        self.client.post(url)
        self.assertEqual(RegistroAuditoria.objects.count(), 1)
        datos = self.datos_evento(fech_even=timezone.localtime(base).strftime('%Y-%m-%dT%H:%M'), ffin_even=timezone.localtime(base + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'))
        Usuario.objects.filter(pk=self.dae.pk).update(rol_usu='ADMIN')
        self.assertContains(self.client.post('/evento/solicitar/', datos), 'Conflicto de espacio:')
        self.assertEqual(Evento.objects.count(), 2)
        self.assertRedirects(self.client.post('/evento/solicitar/', {**datos, 'esp_even': 'Sala Multiuso 101'}), '/perfil/organizacion/')
        self.assertTrue(Evento.objects.filter(tit_even='Evento v6', est_even='APROBADO').exists())

    # Recibe acciones manipuladas y pares ajenos; verifica controles de rol, sede, cuatro avalistas y flags Django.
    def test_permisos_y_roles(self):
        ajeno = self.usuario('ajeno', 'ESTUDIANTE', self.otra)
        self.client.force_login(self.estudiante)
        datos = {'nom_club': 'No guardar', 'cat_club': 'OTRO', 'desc_club': 'Demo', 'avales': [u.pk for u in self.pares[:3]]}
        self.assertContains(self.client.post('/club/postular/', datos), 'Debes seleccionar exactamente 4')
        self.assertContains(self.client.post('/club/postular/', {**datos, 'avales': []}), 'Debes seleccionar exactamente 4')
        self.client.post('/club/postular/', {**datos, 'avales': [u.pk for u in self.pares[:3]] + [ajeno.pk]})
        self.assertFalse(Club.objects.exists())
        self.assertEqual(self.client.post('/evento/solicitar/', self.datos_evento()).status_code, 403)
        rol_url = reverse('core:cambiar_rol', args=[self.pares[0].pk])
        self.assertEqual(self.client.post(rol_url, {'rol_usu': 'ADMIN'}).status_code, 403)
        self.client.force_login(self.dae)
        self.assertEqual(self.client.get(rol_url).status_code, 405)
        self.assertEqual(self.client.post(reverse('core:cambiar_rol', args=[ajeno.pk]), {'rol_usu': 'ADMIN'}).status_code, 404)
        self.assertEqual(self.client.post(rol_url, {'rol_usu': 'INVALIDO'}).status_code, 400)
        self.client.post(rol_url, {'rol_usu': 'DELEGADO'})
        self.pares[0].refresh_from_db()
        self.assertEqual(self.pares[0].rol_usu, 'DELEGADO')
        self.assertFalse(self.pares[0].is_staff)
        self.assertTrue(RegistroAuditoria.objects.filter(acc_audi='Cambió rol de usuario').exists())

    # Recibe un club listo sin cuatro avales; verifica que la DAE no pueda saltarse la validación comunitaria.
    def test_club_incompleto_y_rechazo(self):
        club = Club.objects.create(nom_club='Incompleto', cat_club='OTRO', desc_club='Demo', sede_club=self.sede, lid_club=self.estudiante, est_club='PENDIENTE_DAE')
        self.client.force_login(self.dae)
        self.client.post(reverse('core:resolver_club', args=[club.pk, 'aprobar']))
        club.refresh_from_db()
        self.assertEqual(club.est_club, 'PENDIENTE_DAE')
        self.client.post(reverse('core:resolver_club', args=[club.pk, 'rechazar']))
        club.refresh_from_db()
        self.estudiante.refresh_from_db()
        self.assertEqual(club.est_club, 'RECHAZADO')
        self.assertEqual(self.estudiante.rol_usu, 'ESTUDIANTE')
        self.assertTrue(RegistroAuditoria.objects.filter(acc_audi='Rechazó Club Estudiantil').exists())
