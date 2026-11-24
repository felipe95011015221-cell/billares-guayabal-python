import json

from django.conf import settings

from . import negocio


def _json_ld():
    """Datos estructurados LocalBusiness: SOLO datos con estado «confirmado»."""
    data = {
        "@context": "https://schema.org",
        "@type": "SportsActivityLocation",
        "name": negocio.NOMBRE.valor,
        "url": settings.SITE_URL,
        "areaServed": {"@type": "City", "name": "Medellín"},
        "sport": "Billiards",
        "logo": f"{settings.SITE_URL}/static/club/img/logo.png",
    }
    if negocio.DIRECCION.confirmado:
        data["address"] = {"@type": "PostalAddress", "streetAddress": negocio.DIRECCION.valor, "addressLocality": negocio.CIUDAD.valor,
                           "addressRegion": negocio.REGION, "addressCountry": negocio.PAIS}
    elif negocio.CIUDAD.confirmado:
        data["address"] = {"@type": "PostalAddress", "addressLocality": negocio.CIUDAD.valor, "addressRegion": negocio.REGION, "addressCountry": negocio.PAIS}
    if negocio.TELEFONO.confirmado:
        data["telephone"] = negocio.TELEFONO.valor
    if negocio.HORARIO.confirmado:
        data["openingHoursSpecification"] = [{"@type": "OpeningHoursSpecification", "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], "opens": "09:00", "closes": "02:00"}]
    return json.dumps(data, ensure_ascii=False)


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
