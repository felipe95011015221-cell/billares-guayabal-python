# Fotos subidas desde el panel (MEDIA)

## El problema
Las fotos que se suben en **Administración > Galería** se guardan en `MEDIA_ROOT` (por defecto la carpeta `media/` del proyecto). En Render (plan gratuito o de pago sin disco) el sistema de archivos es **efímero**: se borra en cada despliegue y cada reinicio. Las fotos subidas desaparecerían.

## Lo que ya hace el código
- Valida que el archivo sea una imagen real (Pillow) con extensión JPG, PNG o WebP y un máximo de **5 MB**.
- `config/urls.py` sirve `/media/` con `django.views.static.serve` cuando `DJANGO_DEBUG=1` o cuando se define `SERVE_MEDIA=1` (no sirve rutas fuera de la carpeta).
- `MEDIA_ROOT` debe poder cambiarse por variable de entorno (ver Peticiones: `settings.py` es de otro responsable): `MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))`.
- Las fotos incluidas con el sitio (`club/static/club/img/`) NO se ven afectadas: viajan con el código.

## Opciones para producción
1. **Disco persistente de Render (de pago)**: crear un disco montado en, por ejemplo, `/var/data`, y definir `MEDIA_ROOT=/var/data/media` y `SERVE_MEDIA=1`. Es lo más simple; no escala a varias instancias.
2. **Cloudinary o S3 (o compatible, como Cloudflare R2) con `django-storages`**: las fotos viven fuera del servidor. Requiere cuenta y credenciales (hay planes gratuitos), instalar `django-storages` (y `boto3` o `cloudinary`) y configurar `STORAGES["default"]` en `settings.py`. Es la opción recomendada si habrá varias instancias.
3. **Sin subidas**: incluir las fotos en `club/static/club/img/` y registrarlas con `ruta_estatica`; se despliegan con el código.

## Recomendación
Mientras no exista almacenamiento persistente, **no subir fotos desde el panel en producción**; usar la opción 3 o configurar la 1 o la 2 antes de entregar el panel al club.
