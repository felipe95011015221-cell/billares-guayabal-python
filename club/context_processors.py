import json

from django.conf import settings

from . import negocio


def _json_ld():
    """Datos estructurados (@graph: WebSite + SportsActivityLocation) con SOLO datos «confirmado».

    No incluye calificaciones ni reseñas. `sameAs` solo aparece cuando hay redes confirmadas.
    """
    base = settings.SITE_URL
    lugar = {
        "@type": "SportsActivityLocation",
        "@id": f"{base}/#club",
        "name": negocio.NOMBRE.valor,
        "url": f"{base}/",
        "inLanguage": "es-CO",
        "areaServed": {"@type": "City", "name": "Medellín"},
        "sport": "Billiards",
        "logo": f"{base}/static/club/img/logo.png",
        "image": f"{base}/static/club/img/club/salon-vista-alta-noche.webp",
        "potentialAction": {
            "@type": "ReserveAction",
            "name": "Reservar mesa de billar",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": f"{base}/reservas/",
                "inLanguage": "es-CO",
                "actionPlatform": [
                    "http://schema.org/DesktopWebPlatform",
                    "http://schema.org/MobileWebPlatform",
                ],
            },
        },
    }
    if negocio.DIRECCION.confirmado:
        lugar["address"] = {"@type": "PostalAddress", "streetAddress": negocio.DIRECCION.valor, "addressLocality": negocio.CIUDAD.valor,
                            "addressRegion": negocio.REGION, "addressCountry": negocio.PAIS}
    elif negocio.CIUDAD.confirmado:
        lugar["address"] = {"@type": "PostalAddress", "addressLocality": negocio.CIUDAD.valor, "addressRegion": negocio.REGION, "addressCountry": negocio.PAIS}
    if negocio.TELEFONO.confirmado:
        lugar["telephone"] = negocio.TELEFONO.valor
    if negocio.CORREO.confirmado:
        lugar["email"] = negocio.CORREO.valor
    if negocio.HORARIO.confirmado:
        lugar["openingHoursSpecification"] = [{"@type": "OpeningHoursSpecification", "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], "opens": "09:00", "closes": "02:00"}]
    redes = [d.valor for d in (negocio.INSTAGRAM, negocio.FACEBOOK) if d.confirmado and d.valor]
    if redes:
        lugar["sameAs"] = redes
    sitio_web = {
        "@type": "WebSite",
        "@id": f"{base}/#sitio",
        "url": f"{base}/",
        "name": negocio.NOMBRE.valor,
        "inLanguage": "es-CO",
        "publisher": {"@id": f"{base}/#club"},
    }
    data = {"@context": "https://schema.org", "@graph": [sitio_web, lugar]}
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")  # no puede cerrar el <script>


def sitio(request):
    ruta = request.path
    contexto_wa = next((c for pref, c in [("/reservas", "reservas"), ("/escuela", "clases"), ("/torneos", "torneos"),
                                           ("/eventos", "eventos"), ("/contacto", "ubicacion")] if ruta.startswith(pref)), "general")
    return {
        "negocio": negocio,
        "site_url": settings.SITE_URL,
        "ga_id": settings.GA_ID,
        "nav": negocio.NAV,
        "wa_general": negocio.enlace_whatsapp("general"),
        "wa_contexto": negocio.enlace_whatsapp(contexto_wa),
        "wa_reservas": negocio.enlace_whatsapp("reservas"),
        "wa_reservas_carambola": negocio.enlace_whatsapp("reservas_carambola"),
        "wa_reservas_pool": negocio.enlace_whatsapp("reservas_pool"),
        "wa_clases": negocio.enlace_whatsapp("clases"),
        "wa_torneos": negocio.enlace_whatsapp("torneos"),
        "wa_eventos": negocio.enlace_whatsapp("eventos"),
        "wa_ubicacion": negocio.enlace_whatsapp("ubicacion"),
        "enlace_llamar": negocio.ENLACE_LLAMAR,
        "enlace_mapa": negocio.ENLACE_MAPA,
        "enlace_como_llegar": negocio.ENLACE_COMO_LLEGAR,
        "enlace_mapa_embebido": negocio.ENLACE_MAPA_EMBEBIDO,
        "json_ld": _json_ld(),
        "en_reservas": ruta.startswith("/reservas"),
    }
