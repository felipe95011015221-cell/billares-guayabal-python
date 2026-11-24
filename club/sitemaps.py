from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Torneo

# (prioridad, frecuencia de cambio). Las páginas son plantillas sin fecha de edición propia,
# por eso no se declara lastmod: una fecha inexacta es peor para Google que ninguna.
_PAGINAS = {
    "inicio": (1.0, "weekly"),
    "reservas": (0.9, "weekly"),
    "torneos": (0.8, "weekly"),
    "escuela": (0.8, "monthly"),
    "eventos": (0.8, "monthly"),
    "club": (0.7, "monthly"),
    "contacto": (0.7, "yearly"),
    "galeria": (0.5, "monthly"),
}


class Paginas(Sitemap):
    def items(self):
        return list(_PAGINAS)

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return _PAGINAS[item][0]

    def changefreq(self, item):
        return _PAGINAS[item][1]


class Torneos(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Torneo.objects.filter(publicado=True).exclude(estado="borrador")

    def location(self, t):
        return reverse("torneo", args=[t.slug])


SITEMAPS = {"paginas": Paginas, "torneos": Torneos}
