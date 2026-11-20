from .models import MensajeInbox


# Recibe la petición y devuelve el total de mensajes propios no leídos para el navbar.
def inbox_contador(request):
    puede_buzon = request.user.is_authenticated and request.user.rol_usu in ('LIDER_ESTUDIANTIL', 'DAE', 'ADMIN')
    total = MensajeInbox.objects.filter(dest_inbo=request.user, tipo_inbo='INICIATIVA_BUZON', publ_inbo__sede_publ_id=request.user.sede_usu_id, leid_inbo=False).count() if puede_buzon and request.user.sede_usu_id else 0
    nombre = request.resolver_match.url_name if request.resolver_match else ''
    titulos = {'home': 'Inicio', 'foro': 'Foro', 'inbox': 'Buzón de sugerencias', 'perfil': 'Mi cuenta',
               'ver_perfil': 'Perfil de la comunidad', 'login': 'Iniciar sesión', 'registro': 'Crear cuenta',
               'configuracion_perfil': 'Configuración de cuenta', 'postular_club': 'Solicitar creación de club estudiantil',
               'crear_cuenta_institucional': 'Crear cuenta institucional', 'gestion_perfil': 'Mi panel de gestión',
               'organizacion_perfil': 'Eventos que estoy organizando', 'mensajes': 'Mensajes', 'solicitar_evento': 'Crear evento',
               'crear_publicacion': 'Publicar en el foro', 'clubes': 'Clubes de tu sede', 'detalle_club': 'Club estudiantil', 'mis_clubes': 'Mis clubes', 'espacios': 'Disponibilidad de lugares'}
    if nombre == 'postular_club' and request.user.is_authenticated:
        titulos[nombre] = 'Postular a líder' if request.user.rol_usu == 'ESTUDIANTE' else 'Crear otro club estudiantil'
    return {'inbox_no_leidos': total, 'puede_buzon': puede_buzon, 'titulo_vista_default': titulos.get(nombre, 'INACAP Smart'),
            'busqueda_actual': request.GET.get('q', '')[:200], 'busqueda_en_foro': nombre == 'foro'}
