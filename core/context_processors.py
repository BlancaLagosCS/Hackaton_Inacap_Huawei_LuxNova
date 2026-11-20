from .models import MensajeInbox


# Recibe la petición y devuelve el total de mensajes propios no leídos para el navbar.
def inbox_contador(request):
    total = MensajeInbox.objects.filter(dest_inbo=request.user, leid_inbo=False).count() if request.user.is_authenticated else 0
    nombre = request.resolver_match.url_name if request.resolver_match else ''
    titulos = {'home': 'Inicio', 'foro': 'Foro', 'inbox': 'Buzón de sugerencias', 'perfil': 'Mi cuenta',
               'ver_perfil': 'Perfil de la comunidad', 'login': 'Iniciar sesión', 'registro': 'Crear cuenta',
               'configuracion_perfil': 'Configuración de cuenta', 'postular_club': 'Solicitar creación de club estudiantil',
               'crear_cuenta_institucional': 'Crear cuenta institucional', 'gestion_perfil': 'Mi panel de gestión',
               'organizacion_perfil': 'Eventos que estoy organizando', 'mensajes': 'Mensajes', 'solicitar_evento': 'Crear evento'}
    return {'inbox_no_leidos': total, 'titulo_vista_default': titulos.get(nombre, 'INACAP Smart'),
            'busqueda_actual': request.GET.get('q', '')[:200], 'busqueda_en_foro': nombre == 'foro'}
