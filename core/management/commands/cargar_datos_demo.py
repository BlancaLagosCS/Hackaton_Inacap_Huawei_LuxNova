from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import AvalClub, CARRERAS_CHOICES, Club, Evento, MensajeInbox, PublicacionForo, Sede, Usuario
from core.services import notificar_iniciativa


# Define la carga demo; recibe opciones de manage.py y produce sedes, usuarios y eventos reutilizables.
class Command(BaseCommand):
    help = 'Carga 3 sedes, 9 cuentas por rol y datos demo; restablece las credenciales de CREDENCIALES.md.'

    # Recibe argumentos de consola; crea datos sin duplicar ni sobrescribir cuentas existentes y devuelve un resumen.
    @transaction.atomic
    def handle(self, *args, **options):
        sedes = []
        for nombre, direccion in [('INACAP Rancagua', 'Sede Rancagua'), ('INACAP Santiago Centro', 'Sede Santiago Centro'), ('INACAP Maipú', 'Sede Maipú')]:
            sede, _ = Sede.objects.get_or_create(nom_sede=nombre, defaults={'dir_sede': direccion})
            sedes.append(sede)
        cuentas = [
            ('dae_rancagua', 'DAE', 'Equipo DAE Rancagua', 'dae.rancagua@inacap.cl', 'Dae1234!'),
            ('lider_rancagua', 'LIDER_ESTUDIANTIL', 'Lider Rancagua', 'lider.rancagua@inacapmail.cl', 'Lider1234!'),
        ]
        cuentas += [(f'est{i}', 'ESTUDIANTE', f'Estudiante Demo {i}', f'est{i}@inacapmail.cl', 'Est1234!') for i in range(1, 6)]
        cuentas += [('root_admin', 'ADMIN', 'Root Demo', 'root.rancagua@inacap.cl', 'Admin1234!'),
                    ('jefe_informatica', 'JEFATURA', 'Jefatura Demo', 'jefatura.informatica@inacap.cl', 'Jefe1234!')]
        creadas = 0
        for indice, (username, rol, nombre, correo, clave) in enumerate(cuentas, start=1):
            usuario, nuevo = Usuario.objects.update_or_create(username=username, defaults={
                'nom_usu': nombre, 'rut_usu': f'{str(indice) * 8}-{indice}', 'corr_usu': correo,
                'tel_usu': '+56900000000', 'sede_usu': sedes[0], 'carr_usu': CARRERAS_CHOICES[0][0],
                'anio_usu': timezone.localdate().year, 'rol_usu': rol, 'is_active': True,
                'is_staff': username == 'root_admin', 'is_superuser': username == 'root_admin'})
            usuario.set_password(clave)
            usuario.save(update_fields=['password'])
            creadas += int(nuevo)
        lider = Usuario.objects.get(username='lider_rancagua')
        for titulo, alcance, dias, espacio, descripcion in [
            ('Encuentro de clubes · Rancagua', 'SEDE', 7, 'Patio central', 'Conoce a tus compañeros y descubre iniciativas para participar en tu sede.'),
            ('Conecta INACAP · Innovación intersede', 'INTERSEDE', 14, 'Auditorio y encuentro virtual', 'Comparte ideas con estudiantes de todas las sedes en una jornada de innovación.'),
        ]:
            inicio = timezone.now() + timedelta(days=dias)
            evento, _ = Evento.objects.get_or_create(tit_even=titulo, sede_even=sedes[0], crea_even=lider, defaults={'desc_even': descripcion, 'cat_even': 'TODO_PUBLICO', 'alc_even': alcance, 'esp_even': espacio, 'fech_even': inicio, 'ffin_even': inicio + timedelta(hours=2), 'est_even': 'APROBADO'})
            if evento.ffin_even is None or evento.ffin_even <= evento.fech_even:
                evento.ffin_even = evento.fech_even + timedelta(hours=2)
                evento.save(update_fields=['ffin_even'])
        if not PublicacionForo.objects.filter(sede_publ=sedes[0]).exists():
            estudiante = Usuario.objects.get(username='est1')
            PublicacionForo.objects.create(aut_publ=estudiante, sede_publ=sedes[0], etiq_publ='AHORA_MISMO', tit_publ='¡Nos encontramos en el patio!', cont_publ='Compartimos una jornada de juegos y comunidad en Rancagua. Publicación ficticia de demostración.')
            iniciativa = PublicacionForo.objects.create(aut_publ=estudiante, sede_publ=sedes[0], etiq_publ='INICIATIVA', tit_publ='Taller de programación entre pares', cont_publ='Proponemos un taller colaborativo para aprender Python. Iniciativa ficticia de demostración.')
            notificar_iniciativa(iniciativa)
        proponente = Usuario.objects.get(username='est1')
        club, _ = Club.objects.get_or_create(nom_club='Club Demo de Innovación LuxNova', lid_club=proponente, sede_club=sedes[0], defaults={'cat_club': 'DESARROLLO_ACADEMICO', 'desc_club': 'Club ficticio para demostrar cuatro avales de pares.'})
        for numero in range(2, 6):
            estudiante = Usuario.objects.get(username=f'est{numero}')
            AvalClub.objects.get_or_create(club_aval=club, estu_aval=estudiante)
            MensajeInbox.objects.get_or_create(dest_inbo=estudiante, club_inbo=club, tipo_inbo='SOLICITUD_AVAL', defaults={'asun_inbo': 'Solicitud de aval de club', 'cuer_inbo': f'{proponente.nom_usu} solicita tu aval para {club.nom_club}. Acepta o rechaza desde tu buzón.'})
        # Actualiza los contactos de avisos demo existentes después del cambio de dominio, sin duplicar mensajes.
        for publicacion in PublicacionForo.objects.filter(aut_publ=proponente, etiq_publ='INICIATIVA'):
            cuerpo = f'{publicacion.cont_publ}\n\nContacto del proponente:\nNombre: {proponente.nom_usu}\nCarrera: {proponente.carr_usu}\nCorreo: {proponente.corr_usu}\nTeléfono: {proponente.tel_usu}'
            MensajeInbox.objects.filter(publ_inbo=publicacion, tipo_inbo='INICIATIVA_BUZON').update(cuer_inbo=cuerpo)
        self.stdout.write(self.style.SUCCESS(f'Demo disponible: 3 sedes, 9 cuentas, 2 eventos, foro y club con 4 solicitudes de aval. Cuentas nuevas: {creadas}. Credenciales: CREDENCIALES.md.'))
