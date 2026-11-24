"""
Configuración Django — Club de Billares Guayabal.

Variables de entorno (ver .env.example):
  DJANGO_SECRET_KEY   obligatoria en producción
  DJANGO_DEBUG        "1" solo en desarrollo
  DJANGO_ALLOWED_HOSTS  dominios separados por coma
  DATABASE_URL        postgres://... en producción (sin ella se usa SQLite local)
  SITE_URL            URL pública (canonical, sitemap, Open Graph)
  GA_ID               Google Analytics 4 (opcional)

En Vercel la variable VERCEL=1 existe automáticamente y activa los ajustes para funciones sin servidor.
"""
import os
import sys
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")  # solo si existe (desarrollo); en producción use variables del hosting


def _env_bool(nombre: str, defecto: bool = False) -> bool:
    return os.environ.get(nombre, "1" if defecto else "0").lower() in {"1", "true", "yes", "si", "sí"}


DEBUG = _env_bool("DJANGO_DEBUG", False)
EN_VERCEL = bool(os.environ.get("VERCEL"))

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY and EN_VERCEL and (os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")):
    # Respaldo en Vercel: clave estable derivada de la conexión secreta de Neon (nunca está en el código).
    # Si defines DJANGO_SECRET_KEY en Vercel, esa tiene prioridad.
    import hashlib
    SECRET_KEY = hashlib.sha256(
        ("billares-guayabal:" + (os.environ.get("DATABASE_URL") or os.environ["POSTGRES_URL"])).encode()
    ).hexdigest() * 2
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "solo-desarrollo-no-usar-en-produccion"
    else:
        raise RuntimeError("Defina DJANGO_SECRET_KEY en producción.")

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
if os.environ.get("RENDER_EXTERNAL_HOSTNAME"):  # Render lo define automáticamente (su-app.onrender.com)
    ALLOWED_HOSTS.append(os.environ["RENDER_EXTERNAL_HOSTNAME"])
for _var in ("VERCEL_PROJECT_PRODUCTION_URL", "VERCEL_URL", "VERCEL_BRANCH_URL"):  # Vercel las define solo
    if os.environ.get(_var):
        ALLOWED_HOSTS.append(os.environ[_var])
CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS if h not in {"localhost", "127.0.0.1"} and not h.startswith((".", "*"))]

SITE_URL = os.environ.get("SITE_URL", "http://localhost:8000").rstrip("/")
GA_ID = os.environ.get("GA_ID", "")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.humanize",
    "club",
]

MIDDLEWARE = [
    "club.middleware.CompresionTextoMiddleware",  # gzip de HTML/JSON (los estáticos los comprime WhiteNoise)
    "django.middleware.security.SecurityMiddleware",
    "club.middleware.CabecerasSeguridadMiddleware",  # CSP y Permissions-Policy (también en archivos estáticos)
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "club.context_processors.sitio",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Base de datos: PostgreSQL en producción (DATABASE_URL), SQLite en desarrollo.
# En PostgreSQL una restricción de exclusión impide reservas solapadas a nivel de base de datos.
URL_BD = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
if URL_BD:
    # En Vercel cada petición puede ser una instancia nueva: sin conexiones persistentes
    # y sin cursores del lado del servidor (Neon usa un pool de conexiones).
    DATABASES = {"default": dj_database_url.parse(URL_BD, conn_max_age=0 if EN_VERCEL else 600, ssl_require=not DEBUG)}
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = EN_VERCEL
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
            # IMMEDIATE: cada transacción toma el bloqueo de escritura al empezar,
            # así dos reservas simultáneas no pueden pasar la verificación a la vez.
            "OPTIONS": {"transaction_mode": "IMMEDIATE", "timeout": 20},
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # En Vercel los estáticos los sirve su CDN (collectstatic corre solo al construir).
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage" if not (DEBUG or EN_VERCEL)
                    else "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
if "test" in sys.argv[1:2]:  # las pruebas no necesitan collectstatic ni el manifiesto con hash
    STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
# Cuerpos de petición (JSON/formularios; no cuenta archivos del panel): las APIs reciben unos pocos KB.
DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024  # por encima, el archivo se escribe a disco temporal

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "admin:login"

# Seguridad en producción
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SECURE_REDIRECT_EXEMPT = [r"^robots\.txt$"]  # el health check de Render puede llegar por HTTP interno
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # HSTS: 1 año. includeSubDomains y preload SOLO con dominio propio (en *.onrender.com no se pueden
    # precargar y afectarían a subdominios ajenos). Actívelos con DJANGO_HSTS_SUBDOMINIOS=1 / DJANGO_HSTS_PRELOAD=1.
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", 60 * 60 * 24 * 365))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool("DJANGO_HSTS_SUBDOMINIOS", False)
    SECURE_HSTS_PRELOAD = _env_bool("DJANGO_HSTS_PRELOAD", False)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
# CSRF_COOKIE_HTTPONLY debe seguir en False: sitio.js lee la cookie «csrftoken» para el encabezado X-CSRFToken.
SESSION_COOKIE_AGE = 8 * 60 * 60

# Content-Security-Policy (club/middleware.py). Poner en 0 cuando head.html ya no cargue Google Fonts.
CSP_PERMITIR_GOOGLE_FONTS = _env_bool("CSP_PERMITIR_GOOGLE_FONTS", True)
CSP_SOLO_REPORTAR = _env_bool("CSP_SOLO_REPORTAR", False)  # "1": solo reporta en consola, no bloquea

# Con PostgreSQL la caché (límite de envíos por IP) vive en la base, compartida entre instancias.
# La tabla se crea con «manage.py createcachetable» al desplegar.
if URL_BD:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.db.DatabaseCache", "LOCATION": "club_cache"}}
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
