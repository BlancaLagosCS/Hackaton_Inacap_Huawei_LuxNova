from django import template
from core.reservas import texto_reserva

register = template.Library()


# Recibe un evento; devuelve una fecha o rango de días inclusivos sin mostrar los horarios internos.
@register.filter
def periodo_reserva(evento):
    return texto_reserva(evento)
