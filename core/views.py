from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q
from django.db.models import Prefetch
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .forms import ComentarioForoForm, PublicacionForoForm, RegistroForm
from .models import ComentarioForo, Evento, MensajeInbox, PublicacionForo
from .services import notificar_iniciativa


# Recibe una petición y devuelve bienvenida o eventos futuros aprobados por alcance y sede.
def home(request):
    contexto = {}
    if request.user.is_authenticated:
        inscripciones = Evento.asis_even.through.objects.filter(evento_id=OuterRef('pk'), usuario_id=request.user.pk)
        eventos = Evento.objects.filter(est_even='APROBADO', fech_even__gte=timezone.now()).select_related('sede_even').annotate(total_inscritos=Count('asis_even'), inscrito=Exists(inscripciones)).order_by('fech_even')
        contexto = {'eventos_sede': eventos.filter(alc_even='SEDE', sede_even=request.user.sede_usu) if request.user.sede_usu_id else eventos.none(), 'eventos_intersede': eventos.filter(alc_even='INTERSEDE')}
    return render(request, 'home.html', contexto)


# Recibe datos de alta GET/POST; devuelve el formulario o inicia sesión y redirige al home.
def registro(request):
    if request.user.is_authenticated:
        return redirect('core:home')
    form = RegistroForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        usuario = form.save()
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


# Recibe una petición autenticada; devuelve exclusivamente los mensajes dirigidos al usuario.
@login_required
def inbox(request):
    mensajes = MensajeInbox.objects.filter(dest_inbo=request.user).order_by('-fech_inbo')
    return render(request, 'inbox.html', {'mensajes_inbox': mensajes})


# Recibe una petición autenticada y devuelve el perfil del usuario actual.
@login_required
def perfil(request):
    return render(request, 'perfil.html')
