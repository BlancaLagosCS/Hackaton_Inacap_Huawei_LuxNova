from django.contrib import admin
from .models import Sede, Usuario, Club, AvalClub, Evento, PublicacionForo, ComentarioForo, MensajeInbox, RegistroAuditoria

admin.site.register([Sede, Usuario, Club, AvalClub, Evento, PublicacionForo, ComentarioForo, MensajeInbox, RegistroAuditoria])
