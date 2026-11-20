from .models import MensajeDirecto, Usuario


# Recibe un alias de BD opcional; garantiza la identidad oficial sin contraseña utilizable ni privilegios Django y devuelve su usuario.
def asegurar_usuario_sistema(using='default'):
    usuario, _ = Usuario.objects.using(using).update_or_create(username='sistema', defaults={
        'nom_usu': 'LuxNova Sistema', 'corr_usu': 'sistema@inacap.cl', 'rut_usu': '00000000-0',
        'rol_usu': 'ADMIN', 'is_active': True, 'is_staff': False, 'is_superuser': False, 'sede_usu': None})
    if usuario.has_usable_password():
        usuario.set_unusable_password()
        usuario.save(using=using, update_fields=['password'])
    return usuario


# Recibe destinatario y texto; crea un DM oficial sin permitir responder al canal y devuelve el registro creado.
def enviar_notificacion_sistema(usuario_destino, texto_mensaje):
    sistema = Usuario.objects.filter(username='sistema').first() or asegurar_usuario_sistema()
    return MensajeDirecto.objects.create(emi_mens=sistema, rec_mens=usuario_destino, cont_mens=texto_mensaje)
