"""Filtros de plantilla: pesos colombianos, horas y fotos."""
from django import template
from django.templatetags.static import static
from django.utils import timezone
from django.utils.formats import date_format

register = template.Library()


@register.filter
def cop(valor, vacio="Por confirmar"):
    """1234567 -> $ 1.234.567 (formato colombiano)."""
    if valor in (None, ""):
        return vacio
    return "$ " + f"{int(valor):,}".replace(",", ".")


@register.filter
def hora(dt):
    """Hora en formato 12 h colombiano: 7:00 p. m."""
    if not dt:
        return ""
    dt = timezone.localtime(dt)
    h12 = 12 if dt.hour % 12 == 0 else dt.hour % 12
    return f"{h12}:{dt.minute:02d} {'a. m.' if dt.hour < 12 else 'p. m.'}"


@register.filter
def fecha_larga(dt):
    if not dt:
        return ""
    texto = date_format(timezone.localtime(dt) if hasattr(dt, "hour") else dt, "l, j \\d\\e F \\d\\e Y")
    return texto[:1].upper() + texto[1:]


@register.filter
def fecha_corta(dt):
    texto = date_format(timezone.localtime(dt), "D, j M")
    return texto[:1].upper() + texto[1:]


@register.filter
def img(archivo):
    return static(f"club/img/{archivo}")


@register.filter
def dos_digitos(n):
    return f"{int(n):02d}"


@register.filter
def activo(ruta, destino):
    """True si la ruta actual corresponde a la sección del menú."""
    if destino == "/":
        return ruta == "/"
    return ruta.startswith(destino)
