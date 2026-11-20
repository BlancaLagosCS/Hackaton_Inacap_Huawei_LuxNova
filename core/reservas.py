from calendar import monthrange
from datetime import date, datetime, time, timedelta
import unicodedata

from django.db.models import Q
from django.utils import timezone

from .models import Evento

ESPACIOS_CHOICES = [(nombre, nombre) for nombre in ('Auditorio Principal', 'Sala Multiuso 101', 'Laboratorio Computación 3', 'Patio Central / Ágora', 'Cancha Deportiva')]
ESTADOS_RESERVA = ('PENDIENTE_DAE', 'APROBADO')


# No recibe argumentos; devuelve el filtro de eventos cuyo día todavía sigue vigente, incluyendo reservas de hoy.
def eventos_vigentes():
    return Q(ffin_even__gt=timezone.now()) | Q(ffin_even__isnull=True, fech_even__date__gte=timezone.localdate())


# Recibe el nombre de un espacio; devuelve su clave uniforme e incluye el alias histórico Patio central.
def clave_espacio(nombre):
    clave = ' '.join(''.join(c for c in unicodedata.normalize('NFD', nombre or '') if not unicodedata.combining(c)).casefold().split())
    return 'patio central / agora' if clave in ('patio central', 'patio central/agora', 'patio central / agora') else clave


# Recibe una fecha local; devuelve los extremos exclusivos del día completo, respetando cambios de horario de Chile.
def intervalo_dia(dia):
    zona = timezone.get_current_timezone()
    return (timezone.make_aware(datetime.combine(dia, time.min), zona),
            timezone.make_aware(datetime.combine(dia + timedelta(days=1), time.min), zona))


# Recibe evento histórico o diario; devuelve las fechas inclusivas que ocupa; fin desconocido se conserva abierto.
def dias_evento(evento):
    inicio = timezone.localtime(evento.fech_even).date()
    fin = timezone.localtime(evento.ffin_even - timedelta(microseconds=1)).date() if evento.ffin_even else None
    return inicio, max(inicio, fin) if fin else None


# Recibe evento a reservar; devuelve si otro aprobado o pendiente ocupa algún día suyo en la misma sede y espacio.
def conflicto_reserva(evento):
    inicio, fin = dias_evento(evento)
    fin = fin or inicio
    desde, _ = intervalo_dia(inicio)
    _, hasta = intervalo_dia(fin)
    candidatos = Evento.objects.filter(sede_even_id=evento.sede_even_id, est_even__in=ESTADOS_RESERVA, fech_even__lt=hasta).filter(Q(ffin_even__gt=desde) | Q(ffin_even__isnull=True)).exclude(pk=evento.pk)
    return any(clave_espacio(otro.esp_even) == clave_espacio(evento.esp_even) for otro in candidatos.only('esp_even'))


# Recibe sede, espacio y mes; devuelve días disponibles y bloqueados sin exponer títulos, organizadores ni datos personales.
def disponibilidad_mes(sede_id, espacio, mes):
    ultimo = date(mes.year, mes.month, monthrange(mes.year, mes.month)[1])
    desde, _ = intervalo_dia(mes)
    _, hasta = intervalo_dia(ultimo)
    candidatos = Evento.objects.filter(sede_even_id=sede_id, est_even__in=ESTADOS_RESERVA, fech_even__lt=hasta).filter(Q(ffin_even__gt=desde) | Q(ffin_even__isnull=True)).only('esp_even', 'fech_even', 'ffin_even', 'est_even')
    ocupados = {}
    for evento in candidatos:
        if clave_espacio(evento.esp_even) != clave_espacio(espacio):
            continue
        inicio, fin = dias_evento(evento)
        actual, final = max(mes, inicio), min(ultimo, fin or ultimo)
        while actual <= final:
            estado = 'RESERVADO' if evento.est_even == 'APROBADO' else 'EN_REVISION'
            if ocupados.get(actual) != 'RESERVADO':
                ocupados[actual] = estado
            actual += timedelta(days=1)
    hoy = timezone.localdate()
    dias = []
    for numero in range(1, ultimo.day + 1):
        dia = date(mes.year, mes.month, numero)
        estado = 'PASADO' if dia < hoy else ocupados.get(dia, 'DISPONIBLE')
        dias.append({'fecha': dia.isoformat(), 'dia': numero, 'estado': estado})
    return {'mes': mes.strftime('%Y-%m'), 'espacio': espacio, 'dias': dias,
            'disponibles': [d['fecha'] for d in dias if d['estado'] == 'DISPONIBLE']}


# Recibe texto YYYY-MM opcional; devuelve el primer día del mes válido o lanza ValueError ante un mes mal formado.
def interpretar_mes(valor):
    if not valor:
        return timezone.localdate().replace(day=1)
    mes = datetime.strptime(valor, '%Y-%m').date()
    if mes.strftime('%Y-%m') != valor or mes.year == 9999:
        raise ValueError('Mes inválido.')
    return mes


# Recibe evento con fechas internas; devuelve un rótulo de días inclusivos sin mostrar horas ni el fin exclusivo del día siguiente.
def texto_reserva(evento):
    inicio, fin = dias_evento(evento)
    if fin is None:
        return f'Desde {inicio:%d/%m/%Y} · Término sin definir'
    return f'{inicio:%d/%m/%Y} · Día completo' if inicio == fin else f'{inicio:%d/%m/%Y} al {fin:%d/%m/%Y}'
