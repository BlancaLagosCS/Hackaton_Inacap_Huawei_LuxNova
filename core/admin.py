from django.contrib import admin
from .models import Sede, Usuario, Club, AvalClub, Evento, PublicacionForo, ComentarioForo, MensajeInbox, RegistroAuditoria
from .models import MensajeDirecto

admin.site.register([Sede, Usuario, Club, AvalClub, Evento, PublicacionForo, ComentarioForo, MensajeInbox, RegistroAuditoria])
admin.site.register(MensajeDirecto)
