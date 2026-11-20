from .models import MensajeInbox


# Recibe la petición y devuelve el total de mensajes propios no leídos para el navbar.
def inbox_contador(request):
    total = MensajeInbox.objects.filter(dest_inbo=request.user, leid_inbo=False).count() if request.user.is_authenticated else 0
    return {'inbox_no_leidos': total}
