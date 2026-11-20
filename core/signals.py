from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from .models import MensajeInbox
from .utils import asegurar_usuario_sistema, enviar_notificacion_sistema


# Recibe la app migrada y argumentos de señal; garantiza la cuenta oficial después de migrar core y no devuelve valor.
@receiver(post_migrate, dispatch_uid='core_sistema_post_migrate')
def crear_cuenta_sistema(sender, using, **kwargs):
    if sender.label == 'core':
        asegurar_usuario_sistema(using)


# Recibe un aviso Inbox recién creado; genera un DM del sistema preservando la privacidad del contacto de iniciativas.
@receiver(post_save, sender=MensajeInbox, dispatch_uid='core_inbox_a_dm')
def notificar_desde_inbox(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        texto = ('Recibiste una iniciativa en tu Buzón de sugerencias.' if instance.tipo_inbo == 'INICIATIVA_BUZON'
                 else f'{instance.asun_inbo}\n{instance.cuer_inbo}')
        enviar_notificacion_sistema(instance.dest_inbo, texto)
