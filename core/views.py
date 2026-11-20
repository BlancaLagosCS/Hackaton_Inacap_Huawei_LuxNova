from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Count, Exists, OuterRef, Q
from django.db.models import Prefetch
from django.http import HttpResponseForbidden, JsonResponse
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .forms import ComentarioForoForm, EditarPerfilForm, PublicacionForoForm, RegistroUsuarioForm
from .models import AvalClub, Club, ComentarioForo, Evento, MensajeInbox, PublicacionForo, Usuario
from .services import notificar_iniciativa


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
    with transaction.atomic():
        evento = get_object_or_404(Evento.objects.select_for_update().filter(Q(alc_even='INTERSEDE') | Q(alc_even='SEDE', sede_even_id=request.user.sede_usu_id)), pk=evento_id, est_even='APROBADO', fech_even__gte=timezone.now())
        if evento.asis_even.filter(pk=request.user.pk).exists():
            evento.asis_even.remove(request.user)
            messages.success(request, 'Preinscripción cancelada.')
        else:
            evento.asis_even.add(request.user)
            messages.success(request, 'Tu preinscripción fue registrada.')
    return redirect('core:home')


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
    messages.success(request, 'Tu respuesta al aval fue registrada.')
    return redirect('core:inbox')


ROLES_GESTION = ('LIDER_ESTUDIANTIL', 'DELEGADO', 'JEFATURA', 'DAE', 'ADMIN')


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
    return {'titulo': evento.tit_even, 'fecha': timezone.localtime(evento.fech_even).strftime('%d/%m/%Y %H:%M'),
            'total': len(asistentes), 'asistentes': asistentes}


# Recibe petición, perfil y formulario opcional; devuelve HTML o métricas JSON sin teléfonos no autorizados.
def mostrar_perfil(request, perfil_usuario, form=None):
    resumen = resumen_perfil(request.user, perfil_usuario)
    if request.GET.get('formato') == 'json':
        respuesta = JsonResponse({'resumen': resumen})
        respuesta['Cache-Control'] = 'private, no-store'
        return respuesta
    asistidos = perfil_usuario.eventos_asistidos.filter(est_even='APROBADO').select_related('sede_even').order_by('-fech_even')
    organizados = Evento.objects.filter(crea_even=perfil_usuario, est_even='APROBADO').select_related('sede_even').order_by('-fech_even')
    return render(request, 'perfil.html', {'perfil_usuario': perfil_usuario, 'es_propio': request.user.pk == perfil_usuario.pk,
        'puede_ver_telefono': puede_ver_contacto(request.user, perfil_usuario), 'es_gestor': perfil_usuario.rol_usu in ROLES_GESTION,
        'eventos_asistidos': asistidos, 'eventos_organizados': organizados,
        'clubes_liderados': Club.objects.filter(lid_club=perfil_usuario, est_club='APROBADO'),
        'publicaciones_perfil': PublicacionForo.objects.filter(aut_publ=perfil_usuario, sede_publ_id=request.user.sede_usu_id).order_by('-fech_publ') if request.user.sede_usu_id else PublicacionForo.objects.none(),
        'publicaciones_count': PublicacionForo.objects.filter(aut_publ=perfil_usuario).count(),
        'resumen': resumen, 'perfil_form': form})


# Recibe GET/POST del propietario; guarda foto/bio permitidas y devuelve su perfil o errores sin editar identidad ni rol.
@login_required
@require_http_methods(['GET', 'POST'])
def mi_perfil(request):
    form = EditarPerfilForm(request.POST if request.method == 'POST' else None, request.FILES or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Foto y biografía actualizadas.')
        return redirect('core:perfil')
    return mostrar_perfil(request, request.user, form)


# Recibe GET autenticado y un ID; devuelve el perfil público existente o 404, sin permitir ediciones por esta ruta.
@login_required
@require_http_methods(['GET'])
def ver_perfil(request, usuario_id):
    perfil_usuario = get_object_or_404(Usuario.objects.select_related('sede_usu'), pk=usuario_id)
    return mostrar_perfil(request, perfil_usuario)
