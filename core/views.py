from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import RegistroForm
from .models import Evento, MensajeInbox, PublicacionForo


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


# Recibe una petición autenticada; devuelve publicaciones de la sede en una vista básica de lectura.
@login_required
def ahora_mismo(request):
    publicaciones = PublicacionForo.objects.filter(sede_publ_id=request.user.sede_usu_id).select_related('aut_publ').order_by('-fech_publ') if request.user.sede_usu_id else PublicacionForo.objects.none()
    return render(request, 'ahora_mismo.html', {'publicaciones': publicaciones})


# Recibe una petición autenticada; devuelve exclusivamente los mensajes dirigidos al usuario.
@login_required
def inbox(request):
    mensajes = MensajeInbox.objects.filter(dest_inbo=request.user).order_by('-fech_inbo')
    return render(request, 'inbox.html', {'mensajes_inbox': mensajes})


# Recibe una petición autenticada y devuelve el perfil del usuario actual.
@login_required
def perfil(request):
    return render(request, 'perfil.html')
