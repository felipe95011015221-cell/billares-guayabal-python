# QA, seguridad y rendimiento (2026-11-23)

## Qué se probó
- 71 pruebas automáticas (`python manage.py test`): todas pasan. Nuevas en `club/tests.py`: cabeceras, CSP, límites, honeypot, validaciones, enlaces/anclas/imágenes, sitemap/robots, reservas concurrentes lógicas, compresión, configuración de producción.
- `check --deploy` con variables de producción simuladas (DEBUG=0, clave aleatoria, HTTPS, PostgreSQL): solo quedan W005 y W021 (HSTS `includeSubDomains`/`preload`), a propósito (ver abajo).
- Chrome headless (consola) en `/`, `/reservas/`, `/contacto/`, `/reservas/consultar/`, `/galeria/` con la CSP activa: sin violaciones. Control positivo: con `CSP_PERMITIR_GOOGLE_FONTS=0` Chrome sí bloquea y reporta Google Fonts. El mapa embebido carga.
- `scripts/verificar_enlaces.py` contra local y producción (con enlaces externos): 0 rotos. Unsplash devuelve 401 a clientes automáticos (aviso, no error).
- Búsqueda de secretos (claves, tokens, llaves privadas): ninguno en el repositorio. `.env` existe en disco pero está en `.gitignore`.

## Cambios
| Área | Cambio |
|---|---|
| CSP | `club/middleware.py`: `default-src 'self'`; scripts `'self' 'unsafe-inline'` (+GA solo si `GA_ID`); estilos `'unsafe-inline'`; `frame-src` solo Google Maps; `object-src 'none'`, `base-uri`, `form-action`, `frame-ancestors 'none'`, `upgrade-insecure-requests` (sin DEBUG). Variables: `CSP_PERMITIR_GOOGLE_FONTS` (1 por defecto), `CSP_SOLO_REPORTAR=1` (modo prueba). |
| Otras cabeceras | Permissions-Policy, COOP `same-origin`, nosniff, Referrer-Policy, X-Frame-Options DENY, cookies Secure/HttpOnly/SameSite=Lax. |
| HSTS | 1 año (antes 30 días). Sin `includeSubDomains`/`preload`: el dominio es `*.onrender.com` (no precargable, y afectaría a subdominios ajenos). Con dominio propio: `DJANGO_HSTS_SUBDOMINIOS=1`, `DJANGO_HSTS_PRELOAD=1`. |
| Límite de envíos | Caché en base de datos (`club_cache`) si hay `DATABASE_URL`; `createcachetable` en `build.sh`. Memoria en desarrollo. |
| Cuerpos | `DATA_UPLOAD_MAX_MEMORY_SIZE` 10 MB a 2 MB. |
| Despliegue | `build.sh`: `pipefail`, `createcachetable`, `check --deploy --fail-level ERROR`. `render.yaml`: 2 workers x 2 hilos, log de acceso. `/robots.txt` exento de la redirección HTTPS (health check). |
| CSRF origins | Ignora hosts con comodín o punto inicial. |
| Rendimiento | gzip solo para HTML/JSON/XML (`CompresionTextoMiddleware`; no toca imágenes ni video). Fuentes autoalojadas. Imágenes recomprimidas. |
| Pruebas | El almacenamiento de estáticos con hash no se usa al ejecutar `test` (no exige `collectstatic`). |

## Mediciones (gzip, recursos propios sin video; Google Fonts aparte)
| Página | Producción anterior | Local nuevo (sin gzip de estáticos en runserver) |
|---|---|---|
| HTML inicio | 8,9 KB | 44,5 KB sin comprimir, 10,0 KB con gzip |
| Total inicio | 1120 KB | 1221 KB (incluye CSS 77 KB; en producción WhiteNoise lo sirve a 12,7 KB) |
| Tiempo HTML | 280-430 ms (Render, red) | 1-35 ms local |
Las cifras locales no son comparables 1 a 1: runserver no comprime estáticos y el rediseño es más grande. Con `collectstatic`: CSS 77 a 12,7 KB, JS 11,5 a 3,6 KB y 14,5 a 5 KB (gzip).
Imágenes (antes a después): `mano-taco.webp` 675 a 299 KB, `tres-bolas.webp` 559 a 180 KB, `jugador-pool.webp` 286 a 245 KB, `logo.png` 391 a 65 KB (solo lo usa el JSON-LD). Mismas rutas; las dos portadas altas pasaron de 1600 a 1200 px de ancho (misma proporción). Originales en el scratchpad de la sesión.
Fuentes: dos .woff2 latinos (77 KB + 35 KB) en `club/static/club/fonts/`, `fuentes.css` con `font-display: swap`. Quitan 2 conexiones a Google y 1 CSS que bloquea el render.
Caché de estáticos: `CompressedManifestStaticFilesStorage` en producción (nombre con hash, `max-age` de 1 año, gz precomprimido).

## Hallazgos
| Sev. | Hallazgo | Estado |
|---|---|---|
| Media | Límite de envíos por proceso (LocMem) | Corregido (caché en BD). |
| Media | `_limitar` hace get+set no atómico: bajo carrera concurrente cuenta de menos | Pendiente (api.py, Dev). |
| Media | Sin CSP | Corregido; `'unsafe-inline'` en scripts sigue por scripts en línea (consultar.html, JSON-LD, GA). Para endurecer: moverlos a `.js` estáticos o usar nonce; luego quitar `'unsafe-inline'` de `script-src` en `middleware.py`. |
| Baja | Enlaces internos con `target="_blank"` sin `noopener` (navegadores modernos lo aplican solos) | Aceptado. |
| Baja | `jugador-pool.webp` (245 KB) no la usa ninguna plantilla ni `negocio.py` | Pendiente: borrar o usar. |
| Baja | Video de 8,7 MB sin recomprimir (no hay ffmpeg aquí); ya usa `preload="none"` y póster | Pendiente: recodificar a H.264 ~2-3 MB. |
| Baja | Fuentes de Google aún en `head.html` | Pendiente (UX/SEO), ver PETICIONES. |
| Info | Fotos subidas al panel se pierden en Render (disco efímero); plan gratuito se duerme | Ya en AUDITORIA.md. |
| Info | `tests_dev.py` (Dev) falló a media sesión por trabajo en curso; al final pasa | Resuelto. |

## Compatibilidad
CSS Tailwind 4 requiere Safari 16.4+, Chrome 111+, Firefox 128+ (todos de los últimos 3 años). JS usa `??`, `?.`, `inert`, `IntersectionObserver`, `Intl.DateTimeFormat`: soportado en Safari iOS 15.5+. Sin errores de consola en Chrome.
