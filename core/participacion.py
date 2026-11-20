from collections import Counter

from django.db.models import Count, Q

from .models import Evento, Usuario


# Recibe pares etiqueta/cantidad y devuelve barras normalizadas respecto al máximo para representarlas con CSS y texto accesible.
def barras(filas):
    filas = list(filas)
    maximo = max((total for _, total in filas), default=0)
    return [{'etiqueta': etiqueta or 'Sin carrera', 'total': total, 'porcentaje': round(total * 100 / maximo) if maximo else 0} for etiqueta, total in filas]


# Recibe una petición y eventos; adjunta estadísticas solo para DAE/ADMIN de la sede del evento y devuelve la colección original.
def preparar_estadisticas(request, eventos):
    if request.user.rol_usu not in ('DAE', 'ADMIN') or not request.user.sede_usu_id:
        return eventos
    for evento in eventos:
        if evento.sede_even_id == request.user.sede_usu_id:
            inscritos = list(evento.asis_even.all())
            carreras = Counter(u.carr_usu or 'Sin carrera' for u in inscritos)
            cohortes = Counter(str(u.anio_usu) if u.anio_usu else 'Sin año' for u in inscritos)
            evento.estadisticas = {'carreras': barras(sorted(carreras.items())), 'temporal': barras(sorted(cohortes.items())), 'inscritos': inscritos}
    return eventos


# Recibe un gestor; devuelve participaciones por carrera (DAE/ADMIN) o por evento de su propia carrera (JEFATURA), siempre de su sede.
def dashboard_participacion(usuario):
    if not usuario.sede_usu_id:
        return None
    if usuario.rol_usu in ('DAE', 'ADMIN'):
        filas = Usuario.objects.filter(eventos_asistidos__sede_even_id=usuario.sede_usu_id, eventos_asistidos__est_even='APROBADO').values('carr_usu').annotate(total=Count('eventos_asistidos')).order_by('carr_usu')
        return {'titulo': 'Participación por carrera en tu sede', 'barras': barras((f['carr_usu'], f['total']) for f in filas)}
    if usuario.rol_usu == 'JEFATURA':
        eventos = Evento.objects.filter(sede_even_id=usuario.sede_usu_id, est_even='APROBADO').annotate(participantes_carrera=Count('asis_even', filter=Q(asis_even__carr_usu=usuario.carr_usu))).order_by('fech_even')
        return {'titulo': f'Participación de {usuario.carr_usu or "tu carrera"} por evento', 'barras': barras((e.tit_even, e.participantes_carrera) for e in eventos)}
    return None
