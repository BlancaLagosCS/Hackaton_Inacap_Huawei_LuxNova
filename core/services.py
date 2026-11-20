from .models import MensajeInbox, Usuario


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
    return len(mensajes)
