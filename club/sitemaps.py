from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Torneo


class Paginas(Sitemap):
    changefreq = "weekly"

    def items(self):
        return ["inicio", "club", "reservas", "escuela", "torneos", "eventos", "galeria", "contacto"]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return 1.0 if item == "inicio" else 0.8


class Torneos(Sitemap):
    changefreq = "daily"
    priority = 0.6

    def items(self):
        return Torneo.objects.filter(publicado=True).exclude(estado="borrador")

    def location(self, t):
        return reverse("torneo", args=[t.slug])


SITEMAPS = {"paginas": Paginas, "torneos": Torneos}
