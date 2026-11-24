from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path

from club import api, views
from club.sitemaps import SITEMAPS

admin.site.site_header = "Club de Billares Guayabal · Administración"
admin.site.site_title = "Administración"
admin.site.index_title = "Panel"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("club/", views.club, name="club"),
    path("reservas/", views.reservas, name="reservas"),
    path("reservas/consultar/", views.consultar_reserva, name="consultar"),
    path("escuela/", views.escuela, name="escuela"),
    path("torneos/", views.torneos, name="torneos"),
    path("torneos/<slug:slug>/", views.torneo_detalle, name="torneo"),
    path("eventos/", views.eventos, name="eventos"),
    path("galeria/", views.galeria, name="galeria"),
    path("contacto/", views.contacto, name="contacto"),
    path("privacidad/", views.privacidad, name="privacidad"),
    path("creditos/", views.creditos, name="creditos"),
    # APIs
    path("api/disponibilidad/", api.disponibilidad, name="api_disponibilidad"),
    path("api/reservas/", api.crear_reserva, name="api_reservas"),
    path("api/reservas/consultar/", api.consultar_reserva, name="api_consultar"),
    path("api/clases/inscripcion/", api.inscripcion_clase, name="api_clase"),
    path("api/torneos/inscripcion/", api.inscripcion_torneo, name="api_torneo"),
    path("api/eventos/", api.solicitud_evento, name="api_evento"),
    path("api/contacto/", api.contacto, name="api_contacto"),
    # SEO
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
    path("robots.txt", views.robots, name="robots"),
    path("admin/", admin.site.urls),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "club.views.error_404"
