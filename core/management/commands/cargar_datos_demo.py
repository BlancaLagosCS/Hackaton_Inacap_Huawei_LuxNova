from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import Evento, Sede, Usuario


# Define la carga demo; recibe opciones de manage.py y produce sedes, usuarios y eventos reutilizables.
class Command(BaseCommand):
    help = 'Carga 3 sedes, 7 cuentas y 2 eventos demo. Las cuentas nuevas usan contraseña 1234.'

    # Recibe argumentos de consola; crea datos sin duplicar ni sobrescribir cuentas existentes y devuelve un resumen.
    @transaction.atomic
    def handle(self, *args, **options):
        sedes = []
        for nombre, direccion in [('INACAP Rancagua', 'Sede Rancagua'), ('INACAP Santiago Centro', 'Sede Santiago Centro'), ('INACAP Maipú', 'Sede Maipú')]:
            sede, _ = Sede.objects.get_or_create(nom_sede=nombre, defaults={'dir_sede': direccion})
            sedes.append(sede)
        cuentas = [('dae_rancagua', 'DAE', 'Equipo DAE Rancagua'), ('lider_rancagua', 'LIDER_ESTUDIANTIL', 'Líder Rancagua')]
        cuentas += [(f'est{i}', 'ESTUDIANTE', f'Estudiante Demo {i}') for i in range(1, 6)]
        creadas = 0
        for indice, (username, rol, nombre) in enumerate(cuentas, start=1):
            usuario, nuevo = Usuario.objects.get_or_create(username=username, defaults={'nom_usu': nombre, 'rut_usu': f'DEMO-{indice:03d}', 'corr_usu': f'{username}@demo.inacap.cl', 'tel_usu': '+56900000000', 'sede_usu': sedes[0], 'carr_usu': 'Ingeniería en Informática', 'anio_usu': timezone.localdate().year, 'rol_usu': rol})
            if nuevo:
                usuario.set_password('1234')
                usuario.save()
                creadas += 1
        lider = Usuario.objects.get(username='lider_rancagua')
        for titulo, alcance, dias, espacio, descripcion in [
            ('Encuentro de clubes · Rancagua', 'SEDE', 7, 'Patio central', 'Conoce a tus compañeros y descubre iniciativas para participar en tu sede.'),
            ('Conecta INACAP · Innovación intersede', 'INTERSEDE', 14, 'Auditorio y encuentro virtual', 'Comparte ideas con estudiantes de todas las sedes en una jornada de innovación.'),
        ]:
            Evento.objects.get_or_create(tit_even=titulo, sede_even=sedes[0], crea_even=lider, defaults={'desc_even': descripcion, 'cat_even': 'TODO_PUBLICO', 'alc_even': alcance, 'esp_even': espacio, 'fech_even': timezone.now() + timedelta(days=dias), 'est_even': 'APROBADO'})
        self.stdout.write(self.style.SUCCESS(f'Demo disponible: 3 sedes, 7 cuentas, 2 eventos. Cuentas nuevas: {creadas}. Contraseña inicial demo: 1234.'))
