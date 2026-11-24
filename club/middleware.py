"""Cabeceras de seguridad adicionales: Content-Security-Policy y Permissions-Policy (sin dependencias).

La política se arma una sola vez al iniciar (settings.CSP_* / GA_ID) y se añade a cada respuesta.
Cómo endurecerla (ver docs/QA.md):
  1. Quitar 'unsafe-inline' de script-src exige nonces o hashes; hoy hay <script> en línea en
     consultar.html, el JSON-LD y Google Analytics. Pasar esos scripts a archivos estáticos
     (o usar nonces desde una plantilla base) permite eliminarlo.
  2. Con las fuentes autoalojadas, poner CSP_PERMITIR_GOOGLE_FONTS=0.
"""
from django.conf import settings

GA_SCRIPT = ["https://www.googletagmanager.com"]
GA_CONNECT = ["https://www.google-analytics.com", "https://*.google-analytics.com", "https://*.analytics.google.com",
              "https://www.googletagmanager.com"]
GA_IMG = ["https://www.google-analytics.com", "https://*.google-analytics.com", "https://www.googletagmanager.com"]


def construir_csp(ga_id: str = "", google_fonts: bool = True, upgrade: bool = True) -> str:
    estilos = ["'self'", "'unsafe-inline'"]  # style="..." en línea (animation-delay, aspect-ratio) y panel de Django
    fuentes = ["'self'", "data:"]
    if google_fonts:
        estilos.append("https://fonts.googleapis.com")
        fuentes.append("https://fonts.gstatic.com")
    scripts = ["'self'", "'unsafe-inline'"]
    conexion = ["'self'"]
    imagenes = ["'self'", "data:", "blob:"]
    if ga_id:
        scripts += GA_SCRIPT
        conexion += GA_CONNECT
        imagenes += GA_IMG
    directivas = [
        ("default-src", ["'self'"]),
        ("script-src", scripts),
        ("style-src", estilos),
        ("font-src", fuentes),
        ("img-src", imagenes),
        ("media-src", ["'self'"]),
        ("connect-src", conexion),
        ("frame-src", ["https://www.google.com", "https://maps.google.com"]),  # mapa embebido
        ("object-src", ["'none'"]),
        ("base-uri", ["'self'"]),
        ("form-action", ["'self'"]),
        ("frame-ancestors", ["'none'"]),
    ]
    texto = "; ".join(f"{n} {' '.join(v)}" for n, v in directivas)
    return texto + ("; upgrade-insecure-requests" if upgrade else "")


PERMISSIONS_POLICY = ("accelerometer=(), autoplay=(self), camera=(), display-capture=(), fullscreen=(self), geolocation=(), "
                      "gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=(), interest-cohort=()")


class CabecerasSeguridadMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.csp = construir_csp(
            ga_id=getattr(settings, "GA_ID", ""),
            google_fonts=getattr(settings, "CSP_PERMITIR_GOOGLE_FONTS", True),
            upgrade=not settings.DEBUG,
        )
        self.cabecera_csp = "Content-Security-Policy-Report-Only" if getattr(settings, "CSP_SOLO_REPORTAR", False) else "Content-Security-Policy"

    def __call__(self, request):
        respuesta = self.get_response(request)
        respuesta.headers.setdefault(self.cabecera_csp, self.csp)
        respuesta.headers.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
        return respuesta


from django.middleware.gzip import GZipMiddleware  # noqa: E402

_COMPRIMIBLES = ("text/html", "application/json", "application/xml", "text/xml", "text/plain")


class CompresionTextoMiddleware(GZipMiddleware):
    """gzip solo para HTML/JSON/XML/texto. Los archivos estáticos (imágenes, video) ya van comprimidos o son
    binarios: WhiteNoise sirve sus .gz precomprimidos y el video necesita peticiones parciales (Range)."""

    def process_response(self, request, response):
        if response.headers.get("Content-Type", "").split(";")[0].strip() not in _COMPRIMIBLES:
            return response
        return super().process_response(request, response)
