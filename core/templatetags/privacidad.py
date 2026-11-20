import re

from django import template

register = template.Library()


# Recibe un RUT con o sin formato; omite el DV y oculta los últimos cuatro dígitos del cuerpo sin revelar cuerpos cortos.
@register.filter
def enmascarar_rut(valor):
    cuerpo = re.sub(r'[^0-9]', '', str(valor or '').split('-')[0])
    return cuerpo[:-4] + '*' * min(4, len(cuerpo)) if cuerpo else '****'
