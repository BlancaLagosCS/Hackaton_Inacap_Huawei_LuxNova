from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import AvalClub, Club, MensajeDirecto, MensajeInbox, Usuario
from .utils import asegurar_usuario_sistema, enviar_notificacion_sistema


# Recibe una publicación INICIATIVA guardada; crea avisos privados para líderes/DAE de su sede y devuelve el total enviado.
def notificar_iniciativa(publicacion):
    if publicacion.etiq_publ != 'INICIATIVA':
        return 0
    autor = publicacion.aut_publ
    destinatarios = Usuario.objects.filter(sede_usu_id=publicacion.sede_publ_id, rol_usu__in=['LIDER_ESTUDIANTIL', 'DAE'])
    cuerpo = (f'{publicacion.cont_publ}\n\nContacto del proponente:\n'
              f'Nombre: {autor.nom_usu}\nCarrera: {autor.carr_usu}\n'
              f'Correo: {autor.corr_usu}\nTeléfono: {autor.tel_usu}')
    mensajes = [MensajeInbox(dest_inbo=destinatario, remi_inbo=None, tipo_inbo='INICIATIVA_BUZON',
                             asun_inbo=f"Nueva Iniciativa: {publicacion.tit_publ or 'Sin título'}"[:255],
                             cuer_inbo=cuerpo, publ_inbo=publicacion) for destinatario in destinatarios]
    MensajeInbox.objects.bulk_create(mensajes)
    for mensaje in mensajes:
        enviar_notificacion_sistema(mensaje.dest_inbo, 'Recibiste una iniciativa en tu Buzón de sugerencias.')
    return len(mensajes)


# Recibe un aval existente; devuelve un único DM oficial con acciones, sin crear notificaciones en el buzón de sugerencias.
def notificar_solicitud_aval(aval):
    sistema = Usuario.objects.filter(username='sistema').first() or asegurar_usuario_sistema()
    mensaje, _ = MensajeDirecto.objects.get_or_create(aval_mens=aval, defaults={
        'emi_mens': sistema, 'rec_mens': aval.estu_aval,
        'cont_mens': f'{aval.club_aval.lid_club.nom_usu or aval.club_aval.lid_club.username} solicita tu aval para crear «{aval.club_aval.nom_club}». Acepta o rechaza esta solicitud aquí. Avalar no te inscribe automáticamente al club.'})
    return mensaje


# Recibe un club bloqueado por la transacción del llamador; escala una sola vez tras cuatro avales válidos y devuelve si cambió.
def escalar_club_si_completo(club):
    avales = list(club.avales.select_related('estu_aval'))
    if club.est_club != 'PENDIENTE_AVALES' or len(avales) != 4 or len({a.estu_aval_id for a in avales}) != 4:
        return False
    if not all(a.est_aval == 'ACEPTADO' and a.estu_aval.sede_usu_id == club.sede_club_id and a.estu_aval_id != club.lid_club_id for a in avales):
        return False
    club.est_club = 'PENDIENTE_DAE'
    club.save(update_fields=['est_club'])
    for destinatario in Usuario.objects.filter(Q(rol_usu='DAE', sede_usu_id=club.sede_club_id) | Q(pk=club.lid_club_id)).distinct():
        enviar_notificacion_sistema(destinatario, f'{club.nom_club} completó sus 4 avales y está listo para revisión de la DAE.')
    return True


# Recibe ID de aval, destinatario autenticado y decisión; registra una sola respuesta con bloqueos, notifica y devuelve aval/cambio.
@transaction.atomic
def resolver_aval(aval_id, usuario, decision):
    if decision not in ('ACEPTADO', 'RECHAZADO'):
        raise ValidationError('Selecciona aceptar o rechazar.')
    referencia = AvalClub.objects.get(pk=aval_id)
    club = Club.objects.select_for_update().get(pk=referencia.club_aval_id)
    aval = AvalClub.objects.select_for_update().get(pk=aval_id)
    if aval.estu_aval_id != usuario.pk or not usuario.sede_usu_id or usuario.sede_usu_id != club.sede_club_id or club.lid_club_id == usuario.pk:
        raise PermissionDenied('Solo el destinatario de la sede puede responder este aval.')
    if aval.est_aval != 'PENDIENTE' or club.est_club != 'PENDIENTE_AVALES':
        return aval, False
    aval.est_aval, aval.fech_aval = decision, timezone.now()
    aval.save(update_fields=['est_aval', 'fech_aval'])
    MensajeInbox.objects.filter(dest_inbo=usuario, club_inbo=club, tipo_inbo='SOLICITUD_AVAL').update(leid_inbo=True)
    if decision == 'RECHAZADO':
        enviar_notificacion_sistema(club.lid_club, f'{usuario.nom_usu or usuario.username} rechazó el aval para {club.nom_club}.')
    else:
        escalar_club_si_completo(club)
    enviar_notificacion_sistema(usuario, f'Tu aval para {club.nom_club} quedó {decision.lower()}.')
    return aval, True
