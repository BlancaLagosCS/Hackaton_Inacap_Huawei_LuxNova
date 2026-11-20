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


# Recibe destinatario, texto y aval opcional; crea un DM oficial con acciones de aval permitidas y devuelve el registro.
def enviar_notificacion_sistema(usuario_destino, texto_mensaje, aval=None):
    sistema = Usuario.objects.filter(username='sistema').first() or asegurar_usuario_sistema()
    return MensajeDirecto.objects.create(emi_mens=sistema, rec_mens=usuario_destino, cont_mens=texto_mensaje, aval_mens=aval)
