from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Case, Count, Exists, IntegerField, OuterRef, Q, Subquery, Value, When
from django.db.models import Prefetch
from django.http import HttpResponseForbidden, JsonResponse
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.cache import never_cache

from .forms import ComentarioForoForm, ConfiguracionCuentaForm, CrearCuentaInstitucionalForm, PostularClubForm, PublicacionForoForm, RegistroUsuarioForm, SolicitarEventoForm
from .models import AvalClub, Club, ComentarioForo, Evento, MensajeDirecto, MensajeInbox, PublicacionForo, RegistroAuditoria, Sede, Usuario
from .services import notificar_iniciativa
from .utils import enviar_notificacion_sistema
from .participacion import dashboard_participacion, preparar_estadisticas


# Recibe una petición y devuelve bienvenida o eventos futuros aprobados por alcance y sede.
def home(request):
    contexto = {}
    busqueda = request.GET.get('q', '').strip()[:200]
    if request.user.is_authenticated:
        inscripciones = Evento.asis_even.through.objects.filter(evento_id=OuterRef('pk'), usuario_id=request.user.pk)
        eventos = Evento.objects.filter(est_even='APROBADO', fech_even__gte=timezone.now()).select_related('sede_even', 'crea_even').annotate(total_inscritos=Count('asis_even'), inscrito=Exists(inscripciones)).order_by('fech_even')
        if busqueda:
            eventos = eventos.filter(Q(tit_even__icontains=busqueda) | Q(desc_even__icontains=busqueda))
        clubes = Club.objects.filter(sede_club_id=request.user.sede_usu_id, est_club='APROBADO').select_related('lid_club') if request.user.sede_usu_id else Club.objects.none()
        if busqueda:
            clubes = clubes.filter(Q(nom_club__icontains=busqueda) | Q(desc_club__icontains=busqueda))
        contexto = {'eventos_sede': eventos.filter(alc_even='SEDE', sede_even=request.user.sede_usu) if request.user.sede_usu_id else eventos.none(), 'eventos_intersede': eventos.filter(alc_even='INTERSEDE'), 'clubes_activos': clubes}
        if request.user.rol_usu in ('DAE', 'ADMIN'):
            for clave in ('eventos_sede', 'eventos_intersede'):
                contexto[clave] = preparar_estadisticas(request, contexto[clave].prefetch_related('asis_even'))
    return render(request, 'home.html', contexto)


# Recibe datos de alta GET/POST; devuelve el formulario o inicia sesión y redirige al home.
def registro(request):
    if request.user.is_authenticated:
        return redirect('core:home')
    form = RegistroUsuarioForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        # Repite la comprobación en vista y captura carreras de inserción sin romper la transacción de la petición.
        if Usuario.objects.filter(rut_usu__iexact=form.cleaned_data['rut_usu']).exists():
            form.add_error('rut_usu', 'Este RUT ya se encuentra registrado en el sistema.')
        if Usuario.objects.filter(corr_usu__iexact=form.cleaned_data['corr_usu']).exists():
            form.add_error('corr_usu', 'Este correo institucional ya está registrado.')
        if not form.errors:
            try:
                with transaction.atomic():
                    usuario = form.save()
                    enviar_notificacion_sistema(usuario, '¡Bienvenido a INACAP Smart! Descubre eventos, comparte iniciativas y conecta con tu comunidad.')
            except IntegrityError:
                form.add_error(None, 'El RUT, correo institucional o nombre de usuario ya está registrado. Revisa tus datos.')
            else:
                login(request, usuario)
                messages.success(request, 'Tu cuenta está lista. ¡Bienvenido a LuxNova!')
                return redirect('core:home')
    return render(request, 'registro.html', {'form': form})


# Recibe un POST autenticado; elimina la sesión y devuelve una redirección a la bienvenida.
@require_POST
@login_required
def cerrar_sesion(request):
    logout(request)
    return redirect('core:home')


# Recibe un evento y un POST autenticado; alterna la preinscripción autorizada y vuelve al home.
@require_POST
@login_required
def preinscripcion(request, evento_id):
    if request.user.rol_usu in ('DAE', 'ADMIN'):
        return HttpResponseForbidden('Tu rol consulta la participación y no se preinscribe en eventos.')
    with transaction.atomic():
        evento = get_object_or_404(Evento.objects.select_for_update().filter(Q(alc_even='INTERSEDE') | Q(alc_even='SEDE', sede_even_id=request.user.sede_usu_id)), pk=evento_id, est_even='APROBADO', fech_even__gte=timezone.now())
        if evento.asis_even.filter(pk=request.user.pk).exists():
            evento.asis_even.remove(request.user)
            messages.success(request, 'Preinscripción cancelada.')
        else:
            evento.asis_even.add(request.user)
            messages.success(request, 'Tu preinscripción fue registrada.')
    return redirect('core:perfil' if request.POST.get('volver') == 'perfil' else 'core:home')


# Recibe una petición autenticada de la ruta antigua y devuelve la redirección al foro canónico.
@login_required
def ahora_mismo(request):
    return redirect('core:foro')


# Recibe la petición y formularios opcionales; devuelve el contexto del muro estrictamente limitado a la sede actual.
def contexto_foro(request, formulario=None, comentario=None, publicacion_error=None):
    publicaciones = PublicacionForo.objects.none()
    etiqueta = request.GET.get('etiqueta', '')
    if etiqueta not in ('AHORA_MISMO', 'NOTICIA', 'INICIATIVA'):
        etiqueta = ''
    if request.user.sede_usu_id:
        publicaciones = PublicacionForo.objects.filter(sede_publ_id=request.user.sede_usu_id).select_related('aut_publ').prefetch_related(
            Prefetch('comentarios', queryset=ComentarioForo.objects.select_related('aut_come').order_by('fech_come', 'pk'))
        ).order_by('-fech_publ', '-pk')
        if etiqueta:
            publicaciones = publicaciones.filter(etiq_publ=etiqueta)
        busqueda = request.GET.get('q', '').strip()[:200]
        if busqueda:
            publicaciones = publicaciones.filter(Q(tit_publ__icontains=busqueda) | Q(cont_publ__icontains=busqueda))
    return {'publicaciones': publicaciones, 'form': formulario if formulario is not None else PublicacionForoForm(),
            'comentario_form': comentario, 'publicacion_error': publicacion_error, 'etiqueta': etiqueta}


# Recibe GET o POST autenticado; muestra el muro por sede o guarda publicación y avisos de iniciativa en una transacción.
@login_required
@require_http_methods(['GET', 'POST'])
def foro_ahora_mismo(request):
    form = PublicacionForoForm(request.POST if request.method == 'POST' else None, request.FILES or None)
    if request.method == 'POST':
        if not request.user.sede_usu_id:
            return HttpResponseForbidden('Necesitas una sede asignada para publicar.')
        if form.is_valid():
            with transaction.atomic():
                publicacion = form.save(commit=False)
                publicacion.aut_publ = request.user
                publicacion.sede_publ = request.user.sede_usu
                publicacion.save()
                enviados = notificar_iniciativa(publicacion)
            if publicacion.etiq_publ == 'INICIATIVA':
                messages.success(request, f'Iniciativa publicada y enviada al buzón de Líderes y DAE ({enviados} destinatarios).')
            else:
                messages.success(request, 'Tu publicación ya está en el muro de tu sede.')
            return redirect('core:foro')
    return render(request, 'foro.html', contexto_foro(request, formulario=form))


# Recibe POST y el ID de una publicación; valida su sede y guarda un comentario propio o devuelve errores de formulario.
@require_POST
@login_required
def comentar_publicacion(request, publ_id):
    if not request.user.sede_usu_id:
        return HttpResponseForbidden('Necesitas una sede asignada para comentar.')
    publicacion = get_object_or_404(PublicacionForo, pk=publ_id, sede_publ_id=request.user.sede_usu_id)
    form = ComentarioForoForm(request.POST)
    if form.is_valid():
        comentario = form.save(commit=False)
        comentario.publ_come = publicacion
        comentario.aut_come = request.user
        comentario.save()
        messages.success(request, 'Comentario publicado.')
        return redirect('core:foro')
    return render(request, 'foro.html', contexto_foro(request, comentario=form, publicacion_error=publicacion.pk), status=400)


# Recibe GET autenticado; marca avisos visibles como leídos y devuelve notificaciones propias y el buzón autorizado por sede.
@login_required
@require_http_methods(['GET'])
def buzon_inbox(request):
    recibidos = MensajeInbox.objects.filter(dest_inbo=request.user)
    pendientes = AvalClub.objects.filter(estu_aval=request.user, est_aval='PENDIENTE', club_aval_id=OuterRef('club_inbo_id'))
    solicitudes = recibidos.filter(tipo_inbo='SOLICITUD_AVAL').annotate(pendiente=Exists(pendientes))
    recibidos.filter(tipo_inbo='SISTEMA').update(leid_inbo=True)
    solicitudes.filter(pendiente=False).update(leid_inbo=True)
    solicitudes.filter(pendiente=True).update(leid_inbo=False)
    puede_ver_iniciativas = request.user.rol_usu in ROLES_GESTION
    iniciativas = recibidos.none()
    if puede_ver_iniciativas and request.user.sede_usu_id:
        iniciativas = recibidos.filter(tipo_inbo='INICIATIVA_BUZON', publ_inbo__sede_publ_id=request.user.sede_usu_id)
        iniciativas.update(leid_inbo=True)
    avales = {a.club_aval_id: a for a in AvalClub.objects.filter(estu_aval=request.user).order_by('-pk')}
    notificaciones = list(recibidos.filter(tipo_inbo__in=['SISTEMA', 'SOLICITUD_AVAL']).select_related('club_inbo').order_by('-fech_inbo', '-pk'))
    for mensaje in notificaciones:
        mensaje.aval = avales.get(mensaje.club_inbo_id) if mensaje.tipo_inbo == 'SOLICITUD_AVAL' else None
    return render(request, 'inbox.html', {'notificaciones': notificaciones,
        'iniciativas': iniciativas.select_related('publ_inbo__aut_publ').order_by('-fech_inbo', '-pk'),
        'puede_ver_iniciativas': puede_ver_iniciativas})


# Recibe POST del dueño del aval y su decisión; registra una respuesta única, escala tras cuatro pares y devuelve redirección.
@login_required
@require_POST
def responder_aval(request, aval_id):
    decision = request.POST.get('decision')
    if decision not in ('ACEPTADO', 'RECHAZADO'):
        return JsonResponse({'error': 'Selecciona aceptar o rechazar.'}, status=400)
    with transaction.atomic():
        referencia = get_object_or_404(AvalClub, pk=aval_id, estu_aval=request.user)
        club = get_object_or_404(Club.objects.select_for_update(), pk=referencia.club_aval_id)
        aval = AvalClub.objects.select_for_update().get(pk=referencia.pk)
        if not request.user.sede_usu_id or request.user.sede_usu_id != club.sede_club_id or club.lid_club_id == request.user.pk:
            return HttpResponseForbidden('Solo los compañeros de la sede pueden responder este aval.')
        if aval.est_aval != 'PENDIENTE' or club.est_club != 'PENDIENTE_AVALES':
            messages.info(request, 'Esta solicitud ya fue respondida o cerrada.')
            return redirect('core:inbox')
        aval.est_aval = decision
        aval.fech_aval = timezone.now()
        aval.save(update_fields=['est_aval', 'fech_aval'])
        MensajeInbox.objects.filter(dest_inbo=request.user, club_inbo=club, tipo_inbo='SOLICITUD_AVAL').update(leid_inbo=True)
        if decision == 'RECHAZADO':
            MensajeInbox.objects.create(dest_inbo=club.lid_club, tipo_inbo='SISTEMA', club_inbo=club,
                asun_inbo='Aval de club rechazado', cuer_inbo=f'{request.user.nom_usu or request.user.username} rechazó el aval para {club.nom_club}.')
        else:
            avales = list(club.avales.select_related('estu_aval'))
            if (len(avales) == 4 and len({a.estu_aval_id for a in avales}) == 4
                    and all(a.est_aval == 'ACEPTADO' and a.estu_aval.sede_usu_id == club.sede_club_id and a.estu_aval_id != club.lid_club_id for a in avales)):
                club.est_club = 'PENDIENTE_DAE'
                club.save(update_fields=['est_club'])
                destinatarios = Usuario.objects.filter(Q(rol_usu='DAE', sede_usu_id=club.sede_club_id) | Q(pk=club.lid_club_id)).distinct()
                MensajeInbox.objects.bulk_create([MensajeInbox(dest_inbo=u, tipo_inbo='SISTEMA', club_inbo=club,
                    asun_inbo='Club listo para revisión DAE', cuer_inbo=f'{club.nom_club} completó sus 4 avales y está listo para revisión de la DAE.') for u in destinatarios])
                for destinatario in destinatarios:
                    enviar_notificacion_sistema(destinatario, f'{club.nom_club} completó sus 4 avales y está listo para revisión de la DAE.')
        enviar_notificacion_sistema(request.user, f'Tu aval para {club.nom_club} quedó {decision.lower()}.')
    messages.success(request, 'Tu respuesta al aval fue registrada.')
    return redirect('core:inbox')


ROLES_GESTION = ('LIDER_ESTUDIANTIL', 'DELEGADO', 'JEFATURA', 'DAE', 'ADMIN')
ROLES_EVENTO = ('LIDER_ESTUDIANTIL', 'DELEGADO', 'JEFATURA', 'ADMIN')


# Recibe visitante y dueño de un teléfono; devuelve si el visitante es propietario o tiene un rol autorizado.
def puede_ver_contacto(visitante, propietario):
    return visitante.pk == propietario.pk or visitante.rol_usu in ROLES_GESTION


# Recibe visitante y perfil consultado; devuelve evento próximo o reciente y asistentes con contactos filtrados por permisos.
def resumen_perfil(visitante, perfil_usuario):
    if perfil_usuario.rol_usu not in ROLES_GESTION:
        return None
    eventos = Evento.objects.filter(crea_even=perfil_usuario, est_even='APROBADO')
    evento = eventos.filter(fech_even__gte=timezone.now()).order_by('fech_even', 'pk').first() or eventos.order_by('-fech_even', '-pk').first()
    if not evento:
        return None
    asistentes = [{'nombre': u.nom_usu or u.username, 'carrera': u.carr_usu,
                   'telefono': u.tel_usu if puede_ver_contacto(visitante, u) else None,
                   'url': reverse('core:ver_perfil', args=[u.pk])}
                  for u in evento.asis_even.order_by('nom_usu', 'pk')]
    inicio = timezone.localtime(evento.fech_even).strftime('%d/%m/%Y %H:%M')
    termino = timezone.localtime(evento.ffin_even).strftime('%d/%m/%Y %H:%M') if evento.ffin_even else 'Sin definir'
    return {'titulo': evento.tit_even, 'fecha': f'Inicio: {inicio} — Término: {termino}',
            'total': len(asistentes), 'asistentes': asistentes}


# Recibe petición y perfil; devuelve HTML o métricas JSON sin teléfonos no autorizados.
def mostrar_perfil(request, perfil_usuario):
    resumen = resumen_perfil(request.user, perfil_usuario)
    if request.GET.get('formato') == 'json':
        respuesta = JsonResponse({'resumen': resumen})
        respuesta['Cache-Control'] = 'private, no-store'
        return respuesta
    asistidos = perfil_usuario.eventos_asistidos.filter(est_even='APROBADO').select_related('sede_even').order_by('-fech_even')
    organizados = Evento.objects.filter(crea_even=perfil_usuario, est_even='APROBADO').select_related('sede_even').order_by('-fech_even')
    if request.user.rol_usu in ('DAE', 'ADMIN'):
        asistidos = preparar_estadisticas(request, asistidos.prefetch_related('asis_even'))
        organizados = preparar_estadisticas(request, organizados.prefetch_related('asis_even'))
    return render(request, 'perfil.html', {'perfil_usuario': perfil_usuario, 'es_propio': request.user.pk == perfil_usuario.pk,
        'puede_ver_telefono': puede_ver_contacto(request.user, perfil_usuario), 'es_gestor': perfil_usuario.rol_usu in ROLES_GESTION,
        'eventos_asistidos': asistidos, 'eventos_organizados': organizados,
        'clubes_liderados': Club.objects.filter(lid_club=perfil_usuario, est_club='APROBADO'),
        'publicaciones_perfil': PublicacionForo.objects.filter(aut_publ=perfil_usuario, sede_publ_id=request.user.sede_usu_id).order_by('-fech_publ') if request.user.sede_usu_id else PublicacionForo.objects.none(),
        'publicaciones_count': PublicacionForo.objects.filter(aut_publ=perfil_usuario, sede_publ_id=request.user.sede_usu_id).count() if request.user.sede_usu_id else 0,
        'resumen': resumen,
        'proximos_inscritos': asistidos.filter(fech_even__gte=timezone.now()).order_by('fech_even'),
        'historial_inscritos': asistidos.filter(fech_even__lt=timezone.now()),
        'puede_organizar': request.user.pk == perfil_usuario.pk and perfil_usuario.rol_usu in ROLES_EVENTO,
        'puede_gestionar': request.user.pk == perfil_usuario.pk and (perfil_usuario.rol_usu in ROLES_GESTION or puede_crear_cuentas(request.user)),
        'organizando_total': Evento.objects.filter(crea_even=perfil_usuario).count(),
        'preinscritos_organizados': Evento.asis_even.through.objects.filter(evento__crea_even=perfil_usuario, evento__est_even='APROBADO').count()})


# Recibe GET autenticado del propietario y devuelve su perfil de lectura; toda edición se realiza en configuración.
@login_required
@require_http_methods(['GET'])
def mi_perfil(request):
    return mostrar_perfil(request, request.user)


# Recibe GET autenticado y un ID; devuelve el perfil público existente o 404, sin permitir ediciones por esta ruta.
@login_required
@require_http_methods(['GET'])
def ver_perfil(request, usuario_id):
    perfil_usuario = get_object_or_404(Usuario.objects.select_related('sede_usu'), pk=usuario_id)
    return mostrar_perfil(request, perfil_usuario)


# Recibe petición del propietario; devuelve datos de gestión limitados a su rol y sede.
def contexto_gestion(request):
    usuario = request.user
    contexto = {}
    contexto['dashboard_participacion'] = dashboard_participacion(usuario)
    contexto['puede_crear_cuentas'] = puede_crear_cuentas(usuario)
    contexto['puede_organizar'] = usuario.rol_usu in ROLES_EVENTO
    if usuario.sede_usu_id and usuario.rol_usu == 'JEFATURA':
        contexto['lideres_sede'] = Usuario.objects.filter(sede_usu_id=usuario.sede_usu_id, rol_usu__in=['LIDER_ESTUDIANTIL', 'DELEGADO']).annotate(total_eventos=Count('evento', filter=Q(evento__est_even='APROBADO'))).order_by('nom_usu')
    if usuario.sede_usu_id and usuario.rol_usu in ('DAE', 'ADMIN'):
        sede = usuario.sede_usu_id
        contexto.update({'panel_dae': True,
            'preinscripciones_total': Evento.asis_even.through.objects.filter(evento__sede_even_id=sede, evento__est_even='APROBADO').count(),
            'iniciativas_total': PublicacionForo.objects.filter(sede_publ_id=sede, etiq_publ='INICIATIVA').count(),
            'eventos_aprobados_total': Evento.objects.filter(sede_even_id=sede, est_even='APROBADO').count(),
            'clubes_pendientes': Club.objects.filter(sede_club_id=sede, est_club='PENDIENTE_DAE').select_related('lid_club'),
            'eventos_pendientes': Evento.objects.filter(sede_even_id=sede, est_even='PENDIENTE_DAE').select_related('crea_even').order_by('fech_even'),
            'usuarios_sede': Usuario.objects.filter(sede_usu_id=sede).exclude(username='sistema').order_by('username'),
            'roles_choices': Usuario._meta.get_field('rol_usu').choices,
            'auditoria_sede': RegistroAuditoria.objects.filter(dae_audi__sede_usu_id=sede).select_related('dae_audi').order_by('-fech_audi', '-pk')})
    return contexto


# Recibe un evento con intervalo válido; devuelve si solapa otra reserva aprobada local o una reserva histórica sin término conocido.
def conflicto_espacio(evento):
    return Evento.objects.filter(sede_even_id=evento.sede_even_id, esp_even__iexact=evento.esp_even.strip(), est_even='APROBADO',
        fech_even__lt=evento.ffin_even).filter(Q(ffin_even__gt=evento.fech_even) | Q(ffin_even__isnull=True)).exclude(pk=evento.pk).exists()


# Recibe GET/POST estudiantil; guarda club, cuatro avales y sus avisos atómicamente y devuelve perfil con confirmación o errores.
@login_required
@require_http_methods(['GET', 'POST'])
def postular_club(request):
    if request.user.rol_usu != 'ESTUDIANTE' or not request.user.sede_usu_id:
        return HttpResponseForbidden('Solo estudiantes con sede pueden postular clubes.')
    form = PostularClubForm(request.POST if request.method == 'POST' else None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            club = form.save(commit=False)
            club.sede_club = request.user.sede_usu
            club.lid_club = request.user
            club.est_club = 'PENDIENTE_AVALES'
            club.save()
            for estudiante in form.cleaned_data['avales']:
                AvalClub.objects.create(club_aval=club, estu_aval=estudiante)
                MensajeInbox.objects.create(dest_inbo=estudiante, remi_inbo=None, tipo_inbo='SOLICITUD_AVAL', club_inbo=club,
                    asun_inbo=f'Solicitud de Aval para Club: {club.nom_club}'[:255],
                    cuer_inbo=f"{request.user.nom_usu} te invita a avalar la creación del club '{club.nom_club}' ({club.get_cat_club_display()}). Responde en tu Buzón de sugerencias.")
        messages.success(request, 'Postulación enviada: tus cuatro compañeros recibieron la solicitud de aval.')
        return redirect('core:postular_club')
    postulaciones = Club.objects.filter(lid_club=request.user).annotate(aceptados=Count('avales', filter=Q(avales__est_aval='ACEPTADO'))).order_by('-fech_club')
    return render(request, 'postular_club.html', {'form': form, 'postulaciones': postulaciones})


# Recibe GET/POST de un organizador; muestra un formulario dedicado y guarda solicitud o aprobación directa ADMIN sin conflicto.
@login_required
@require_http_methods(['GET', 'POST'])
def solicitar_evento(request):
    if request.user.rol_usu not in ROLES_EVENTO or not request.user.sede_usu_id:
        return HttpResponseForbidden('Necesitas un rol de gestión y una sede para solicitar eventos.')
    form = SolicitarEventoForm(request.POST if request.method == 'POST' else None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            Sede.objects.select_for_update().get(pk=request.user.sede_usu_id)
            evento = form.save(commit=False)
            evento.sede_even = request.user.sede_usu
            evento.crea_even = request.user
            evento.est_even = 'PENDIENTE_DAE'
            directo = request.user.rol_usu in ('DAE', 'ADMIN')
            if directo and conflicto_espacio(evento):
                form.add_error('fech_even', 'Conflicto de espacio: ya existe un evento aprobado en ese espacio y horario.')
            else:
                if directo:
                    evento.est_even = 'APROBADO'
                evento.save()
                if directo:
                    RegistroAuditoria.objects.create(dae_audi=request.user, acc_audi='Creó y aprobó Evento', det_audi=f'Evento #{evento.pk}: {evento.tit_even}; sede #{evento.sede_even_id}; espacio {evento.esp_even}; inicio {evento.fech_even.isoformat()}; término {evento.ffin_even.isoformat()}')
                    enviar_notificacion_sistema(request.user, f'Tu evento {evento.tit_even} fue aprobado y publicado.')
                messages.success(request, 'Evento publicado.' if directo else 'Solicitud de espacio y evento enviada a la DAE.')
                return redirect('core:organizacion_perfil')
    return render(request, 'solicitar_evento.html', {'form': form})


# Recibe POST de DAE/ADMIN y club local; aplica una resolución terminal con ascenso, aviso y auditoría, o devuelve rechazo seguro.
@login_required
@require_POST
def aprobar_rechazar_club(request, club_id, accion):
    if request.user.rol_usu not in ('DAE', 'ADMIN') or not request.user.sede_usu_id:
        return HttpResponseForbidden('Acceso exclusivo para DAE y ADMIN de la sede.')
    if accion not in ('aprobar', 'rechazar'):
        return JsonResponse({'error': 'Acción inválida.'}, status=400)
    with transaction.atomic():
        club = get_object_or_404(Club.objects.select_for_update(), pk=club_id, sede_club_id=request.user.sede_usu_id)
        if club.est_club != 'PENDIENTE_DAE':
            messages.info(request, 'Este club no está pendiente de revisión DAE.')
            return redirect('core:gestion_perfil')
        avales = list(club.avales.select_related('estu_aval'))
        if accion == 'aprobar' and not (len(avales) == 4 and len({a.estu_aval_id for a in avales}) == 4 and all(a.est_aval == 'ACEPTADO' and a.estu_aval.sede_usu_id == club.sede_club_id and a.estu_aval_id != club.lid_club_id for a in avales)):
            messages.error(request, 'El club debe tener cuatro avales válidos aceptados de su sede.')
            return redirect('core:gestion_perfil')
        club.est_club = 'APROBADO' if accion == 'aprobar' else 'RECHAZADO'
        club.save(update_fields=['est_club'])
        lider = Usuario.objects.select_for_update().get(pk=club.lid_club_id)
        if accion == 'aprobar' and lider.rol_usu == 'ESTUDIANTE':
            lider.rol_usu = 'LIDER_ESTUDIANTIL'
            lider.save(update_fields=['rol_usu'])
        cuerpo = f'Tu club {club.nom_club} fue {club.est_club.lower()}.'
        if accion == 'aprobar':
            cuerpo += ' Ya tienes habilitada la reserva de espacios en tu perfil.'
        MensajeInbox.objects.create(dest_inbo=lider, tipo_inbo='SISTEMA', club_inbo=club, asun_inbo='Resolución de postulación a club', cuer_inbo=cuerpo)
        RegistroAuditoria.objects.create(dae_audi=request.user, acc_audi='Aprobó Club Estudiantil' if accion == 'aprobar' else 'Rechazó Club Estudiantil', det_audi=f'Club #{club.pk}: {club.nom_club}; sede #{club.sede_club_id}; líder #{lider.pk}; estado {club.est_club}')
    messages.success(request, 'Resolución del club registrada y notificada.')
    return redirect('core:gestion_perfil')


# Recibe POST DAE/ADMIN y evento local; bloquea sede, valida solapamiento y registra una única resolución con aviso y auditoría.
@login_required
@require_POST
def aprobar_rechazar_evento(request, evento_id, accion):
    if request.user.rol_usu not in ('DAE', 'ADMIN') or not request.user.sede_usu_id:
        return HttpResponseForbidden('Acceso exclusivo para DAE y ADMIN de la sede.')
    if accion not in ('aprobar', 'rechazar'):
        return JsonResponse({'error': 'Acción inválida.'}, status=400)
    with transaction.atomic():
        Sede.objects.select_for_update().get(pk=request.user.sede_usu_id)
        evento = get_object_or_404(Evento.objects.select_for_update(), pk=evento_id, sede_even_id=request.user.sede_usu_id)
        if evento.est_even != 'PENDIENTE_DAE':
            messages.info(request, 'Este evento ya fue resuelto.')
            return redirect('core:gestion_perfil')
        if accion == 'aprobar' and (evento.ffin_even is None or evento.ffin_even <= evento.fech_even):
            messages.error(request, 'El evento necesita una fecha de término posterior al inicio antes de aprobarse.')
            return redirect('core:gestion_perfil')
        if accion == 'aprobar' and conflicto_espacio(evento):
            messages.error(request, 'Conflicto de espacio: ya existe un evento aprobado en ese espacio y horario.')
            return redirect('core:gestion_perfil')
        evento.est_even = 'APROBADO' if accion == 'aprobar' else 'RECHAZADO'
        evento.save(update_fields=['est_even'])
        MensajeInbox.objects.create(dest_inbo=evento.crea_even, tipo_inbo='SISTEMA', asun_inbo='Resolución de evento', cuer_inbo=f'Tu evento {evento.tit_even} fue {evento.est_even.lower()}.')
        RegistroAuditoria.objects.create(dae_audi=request.user, acc_audi='Aprobó Evento' if accion == 'aprobar' else 'Rechazó Evento', det_audi=f'Evento #{evento.pk}: {evento.tit_even}; sede #{evento.sede_even_id}; espacio {evento.esp_even}; inicio {evento.fech_even.isoformat()}; término {evento.ffin_even.isoformat() if evento.ffin_even else "Sin definir"}; estado {evento.est_even}')
    messages.success(request, 'Resolución del evento registrada y notificada.')
    return redirect('core:gestion_perfil')


# Recibe POST DAE/ADMIN, usuario local y un rol permitido; cambia solo rol_usu y devuelve perfil tras registrar auditoría.
@login_required
@require_POST
def cambiar_rol_usuario(request, usuario_id):
    if request.user.rol_usu not in ('DAE', 'ADMIN') or not request.user.sede_usu_id:
        return HttpResponseForbidden('Acceso exclusivo para DAE y ADMIN de la sede.')
    rol = request.POST.get('rol_usu')
    if rol not in dict(Usuario._meta.get_field('rol_usu').choices):
        return JsonResponse({'error': 'Rol inválido.'}, status=400)
    with transaction.atomic():
        usuario = get_object_or_404(Usuario.objects.select_for_update().exclude(username='sistema'), pk=usuario_id, sede_usu_id=request.user.sede_usu_id)
        anterior = usuario.rol_usu
        if anterior != rol:
            usuario.rol_usu = rol
            usuario.save(update_fields=['rol_usu'])
            RegistroAuditoria.objects.create(dae_audi=request.user, acc_audi='Cambió rol de usuario', det_audi=f'Usuario #{usuario.pk} @{usuario.username}; sede #{usuario.sede_usu_id}; {anterior} -> {rol}')
    messages.success(request, 'Rol actualizado.')
    if usuario.pk == request.user.pk and rol not in ROLES_GESTION and not request.user.is_superuser:
        return redirect('core:perfil')
    return redirect('core:gestion_perfil')


# Recibe un usuario autenticado; devuelve si tiene autorización administrativa para crear cuentas humanas institucionales.
def puede_crear_cuentas(usuario):
    return usuario.username != 'sistema' and (usuario.rol_usu == 'ADMIN' or usuario.is_superuser)


# Recibe GET/POST propio; actualiza solo campos configurables, conserva la sesión tras cambiar clave y devuelve perfil o errores.
@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def configuracion_perfil(request):
    if request.user.username == 'sistema':
        return HttpResponseForbidden('La cuenta oficial no admite configuración de usuario.')
    form = ConfiguracionCuentaForm(request.POST if request.method == 'POST' else None, request.FILES or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                usuario = form.save()
        except IntegrityError:
            form.add_error(None, 'El nickname o correo institucional ya está registrado. Revisa tus datos.')
        else:
            if form.cleaned_data.get('nueva_password'):
                update_session_auth_hash(request, usuario)
            messages.success(request, 'Configuración de cuenta actualizada correctamente.')
            return redirect('core:perfil')
    return render(request, 'configuracion_perfil.html', {'form': form})


# Recibe GET/POST de ADMIN/superusuario; crea cuenta, bienvenida DM y auditoría atómicamente, y devuelve el perfil o formulario con errores.
@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def crear_cuenta_institucional(request):
    if not puede_crear_cuentas(request.user):
        return HttpResponseForbidden('Solo ADMIN o superusuarios pueden crear cuentas institucionales.')
    form = CrearCuentaInstitucionalForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                usuario = form.save()
                enviar_notificacion_sistema(usuario, f'Bienvenido a INACAP Smart, {usuario.nom_usu}. Tu cuenta institucional está lista. Puedes configurar tu nickname y contraseña desde el engranaje de tu perfil.')
                RegistroAuditoria.objects.create(dae_audi=request.user, acc_audi='Creó cuenta institucional', det_audi=f'Usuario #{usuario.pk} @{usuario.username}; rol {usuario.rol_usu}; sede #{usuario.sede_usu_id}')
        except IntegrityError:
            form.add_error(None, 'El nickname, RUT o correo institucional ya está registrado. Revisa tus datos.')
        else:
            messages.success(request, 'Cuenta institucional creada correctamente.')
            return redirect('core:gestion_perfil')
    return render(request, 'crear_cuenta_institucional.html', {'form': form})


# Recibe GET propio de gestión; devuelve paneles del rol separados del perfil personal y rechaza accesos sin permisos.
@login_required
@never_cache
@require_http_methods(['GET'])
def gestion_perfil(request):
    if request.user.rol_usu not in ROLES_GESTION and not puede_crear_cuentas(request.user):
        return HttpResponseForbidden('Tu cuenta no tiene acceso a gestión.')
    return render(request, 'gestion_perfil.html', contexto_gestion(request))


# Recibe GET autenticado; devuelve exclusivamente los eventos que organiza el dueño y los inscritos con contacto según permisos.
@login_required
@never_cache
@require_http_methods(['GET'])
def organizacion_perfil(request):
    eventos = Evento.objects.filter(crea_even=request.user).select_related('sede_even').annotate(total_inscritos=Count('asis_even')).prefetch_related('asis_even').order_by('-fech_even')
    for evento in eventos:
        evento.asistentes_info = [{'nombre': u.nom_usu or u.username, 'carrera': u.carr_usu,
            'telefono': u.tel_usu if puede_ver_contacto(request.user, u) else None,
            'url': reverse('core:ver_perfil', args=[u.pk]), 'id': u.pk} for u in evento.asis_even.all()]
    return render(request, 'organizacion_perfil.html', {'eventos': eventos, 'puede_organizar': request.user.rol_usu in ROLES_EVENTO})


# Recibe GET autenticado y un destinatario opcional; devuelve una entrada visible a mensajes sin enviar nada ni marcar lecturas.
@login_required
@never_cache
@require_http_methods(['GET'])
def mensajes(request):
    destino = request.GET.get('usuario', '')
    if destino and not destino.isdigit():
        return JsonResponse({'error': 'Usuario inválido.'}, status=400)
    if destino:
        get_object_or_404(Usuario.objects.filter(is_active=True).exclude(pk=request.user.pk), pk=int(destino))
    return render(request, 'mensajes.html', {'dm_destino_id': destino})


# Recibe un usuario y devuelve solo datos de perfil públicos para buscadores y conversaciones, sin RUT, correo ni teléfono.
def usuario_json(usuario):
    return {'id': usuario.pk, 'username': usuario.username, 'nom_usu': usuario.nom_usu,
            'carr_usu': usuario.carr_usu, 'sede_nombre': usuario.sede_usu.nom_sede if usuario.sede_usu_id else '',
            'foto_url': usuario.foto_usu.url if usuario.foto_usu else '',
            'perfil_url': reverse('core:ver_perfil', args=[usuario.pk]), 'oficial': usuario.username == 'sistema'}


# Recibe GET autenticado con q/solo_sede; devuelve hasta 20 perfiles activos por nombre o nickname, con filtro estricto para avalistas.
@login_required
@never_cache
@require_http_methods(['GET'])
def buscar_usuarios_api(request):
    consulta = request.GET.get('q', '').strip().lstrip('@')[:100]
    usuarios = Usuario.objects.filter(is_active=True).exclude(username__iexact='sistema').exclude(pk=request.user.pk)
    if request.GET.get('solo_sede') == '1':
        usuarios = usuarios.filter(sede_usu_id=request.user.sede_usu_id, rol_usu='ESTUDIANTE') if request.user.sede_usu_id else usuarios.none()
    if consulta:
        usuarios = usuarios.filter(Q(nom_usu__icontains=consulta) | Q(username__icontains=consulta))
    else:
        usuarios = usuarios.none()
    return JsonResponse({'usuarios': [usuario_json(u) for u in usuarios.select_related('sede_usu').order_by('nom_usu', 'username')[:20]]})


# Recibe GET autenticado; devuelve conversaciones ordenadas por último mensaje, cuenta oficial fija y total propio no leído.
@login_required
@never_cache
@require_http_methods(['GET'])
def dm_conversaciones(request):
    ultimo = MensajeDirecto.objects.filter(Q(emi_mens=request.user, rec_mens_id=OuterRef('pk')) | Q(rec_mens=request.user, emi_mens_id=OuterRef('pk'))).order_by('-fech_mens', '-pk')
    usuarios = Usuario.objects.filter(Q(dms_enviados__rec_mens=request.user) | Q(dms_recibidos__emi_mens=request.user) | Q(username='sistema')).exclude(pk=request.user.pk).distinct()
    usuarios = usuarios.annotate(ultimo_texto=Subquery(ultimo.values('cont_mens')[:1]), ultimo_fecha=Subquery(ultimo.values('fech_mens')[:1]),
        oficial_orden=Case(When(username='sistema', then=Value(0)), default=Value(1), output_field=IntegerField())).select_related('sede_usu').order_by('oficial_orden', '-ultimo_fecha', 'pk')[:100]
    no_leidos = MensajeDirecto.objects.filter(rec_mens=request.user, leid_mens=False)
    conteos = {fila['emi_mens_id']: fila['total'] for fila in no_leidos.values('emi_mens_id').annotate(total=Count('pk'))}
    return JsonResponse({'no_leidos': no_leidos.count(), 'conversaciones': [{**usuario_json(u), 'extracto': (u.ultimo_texto or 'Canal oficial de notificaciones')[:100], 'fecha': u.ultimo_fecha.isoformat() if u.ultimo_fecha else None, 'no_leidos': conteos.get(u.pk, 0)} for u in usuarios]})


# Recibe GET autenticado e ID de interlocutor; devuelve solo los últimos 100 mensajes entre ese usuario y el solicitante.
@login_required
@never_cache
@require_http_methods(['GET'])
def dm_hilo(request, usuario_id):
    interlocutor = get_object_or_404(Usuario.objects.select_related('sede_usu').exclude(pk=request.user.pk), pk=usuario_id)
    mensajes = MensajeDirecto.objects.filter(Q(emi_mens=request.user, rec_mens=interlocutor) | Q(emi_mens=interlocutor, rec_mens=request.user)).order_by('-pk')[:100]
    return JsonResponse({'usuario': usuario_json(interlocutor), 'mensajes': [{'id': m.pk, 'propio': m.emi_mens_id == request.user.pk, 'contenido': m.cont_mens, 'leido': m.leid_mens, 'fecha': m.fech_mens.isoformat()} for m in reversed(list(mensajes))]})


# Recibe usuario actual, interlocutor y corte opcional; marca únicamente mensajes recibidos de ese hilo y devuelve cantidad actualizada.
def leer_recibidos(usuario, interlocutor, hasta_id=None):
    mensajes = MensajeDirecto.objects.filter(emi_mens=interlocutor, rec_mens=usuario, leid_mens=False)
    if hasta_id is not None:
        mensajes = mensajes.filter(pk__lte=hasta_id)
    return mensajes.update(leid_mens=True)


# Recibe POST autenticado con corte opcional; marca lectura del hilo propio, exige CSRF y devuelve el total marcado.
@login_required
@never_cache
@require_POST
def dm_leer(request, usuario_id):
    interlocutor = get_object_or_404(Usuario.objects.exclude(pk=request.user.pk), pk=usuario_id)
    corte = request.POST.get('hasta_id')
    if corte and not corte.isdigit():
        return JsonResponse({'error': 'Corte de lectura inválido.'}, status=400)
    return JsonResponse({'marcados': leer_recibidos(request.user, interlocutor, int(corte) if corte else None)})


# Recibe POST autenticado con texto; envía un DM al destinatario activo, marca recibidos y bloquea respuestas o suplantación de sistema.
@login_required
@never_cache
@require_POST
def dm_enviar(request, usuario_id):
    interlocutor = get_object_or_404(Usuario.objects.filter(is_active=True).exclude(pk=request.user.pk), pk=usuario_id)
    if interlocutor.username == 'sistema' or request.user.username == 'sistema':
        return JsonResponse({'error': 'Canal oficial de notificaciones automáticas del sistema (no admite respuestas)'}, status=403)
    texto = request.POST.get('cont_mens', '').strip()
    if not texto or len(texto) > 5000:
        return JsonResponse({'error': 'Escribe un mensaje de 1 a 5000 caracteres.'}, status=400)
    with transaction.atomic():
        mensaje = MensajeDirecto.objects.create(emi_mens=request.user, rec_mens=interlocutor, cont_mens=texto)
        leer_recibidos(request.user, interlocutor)
    return JsonResponse({'id': mensaje.pk}, status=201)
