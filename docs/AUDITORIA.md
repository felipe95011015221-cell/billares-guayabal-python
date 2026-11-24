# Auditoría del repositorio (2026-11-23)

Alcance: Django (`club/`, `config/`), plantillas, JS, CSS, despliegue (`render.yaml`, `build.sh`) y dependencias.
Archivos revisados: `api.py`, `servicios.py`, `views.py`, `forms.py`, `models.py`, `admin.py`, `negocio.py`, `disponibilidad.py`, `context_processors.py`, `sitemaps.py`, `settings.py`, `urls.py`, comando de datos iniciales, las 14 plantillas y 2 archivos JS, `render.yaml`, `build.sh`, dependencias.
Verificado: 25 pruebas automáticas pasan (3 nuevas por fallo corregido); `check --deploy` sin errores.

## Corregido en esta revisión
| # | Hallazgo | Evidencia | Arreglo |
|---|---|---|---|
| 1 | **Error 500** si el cuerpo JSON de la API no es un objeto (`[1]`, `"x"`, `123`) | `POST /api/reservas/consultar/` → 500 (`'int' object has no attribute 'get'`) | `_cuerpo` solo acepta `dict`; ahora 422. Prueba nueva. |
| 2 | **Límite de envíos evadible**: `_ip` usaba la primera IP de `X-Forwarded-For`, que escribe el cliente | 20 consultas con IP distinta cada una, ningún 429 (el límite es 15) | Se usa la última entrada (la del proxy). Prueba nueva. Permite probar códigos de reserva a fuerza bruta menos fácilmente. |
| 3 | `transition: all` (guía Vercel) en botón, menú y 2 tarjetas | `grep transition-all` | Propiedades explícitas. |
| 4 | Restos de MAYÚSCULAS/espaciado en `reservas.js` tras el rediseño | `grep uppercase` | Corregido. |
| 5 | **Bucle infinito**: si en el panel se guarda `intervalo_min = 0`, `franjas_disponibles` nunca termina y `/api/disponibilidad/` cuelga un worker | `while t + duracion <= cierre: t += 0` | `Ajustes.clean()` valida intervalo ≥ 5, cierre > apertura y duraciones (lista de enteros 15–600); además `reglas_actuales` usa `max(5, …)`. Prueba nueva. |
| 6 | **HTML sin escapar en el panel**: `historial_legible` armaba el HTML con f-string y `format_html(filas)` sin argumentos (obsoleto en Django 5, eliminado en 6) | detalle con `<script>` se renderizaba tal cual | `format_html_join` escapa cada campo. Prueba nueva. |
| 7 | JSON-LD dentro de `<script>` sin escapar `<` | `json.dumps(...)|safe` | Se sustituye `<` por `\u003c`. Prueba nueva. |
| 8 | Titulares de página con una sola palabra resaltada (`<em class="text-oro">`) en 8 páginas | `grep "<em"` | Eliminado, coherente con el sistema de diseño. |

## Pendiente (recomendado)
0. **Las fotos subidas desde el panel no se verán en producción.** `FotoGaleria.imagen` se guarda en `media/` (disco local de Render, que se borra en cada despliegue) y `urls.py` solo sirve `/media/` con `DEBUG=1`. Usar almacenamiento externo (Cloudinary, S3 o un disco persistente de Render) antes de que el club suba fotos.
0b. **Política de datos** (`privacidad.html`): sigue marcada «Borrador base» y afirma que los datos «no se comparten con terceros», pero el sitio usa Google Maps, Google Fonts y, si se configura, Google Analytics. Revisarla con el responsable del tratamiento (razón social, NIT y canal de atención).
0c. **Acciones masivas de inscripciones** (`_acciones_inscripcion`) usan `update()`: reactivar una inscripción cancelada puede superar el cupo o chocar con la restricción de celular único (error 500 en el panel). Validar cupo y duplicado como hace `_cambiar_estado` en reservas.
0d. **Accesibilidad**: el video del evento no tiene subtítulos ni transcripción; los filtros de la galería usan `role="tab"` sin `tabpanel` (mejor botones con `aria-pressed`); el visor de la galería cierra con Escape pero conviene confirmar que devuelve el foco al abrirlo.
1. **Límite de envíos por proceso**: usa `LocMemCache`; con 2 workers de gunicorn el límite efectivo se duplica y se reinicia al desplegar. Usar caché en base de datos o Redis si hay abuso.
2. **Sin Content-Security-Policy.** Añadir `django-csp` (el sitio carga Google Fonts y, opcionalmente, GA).
3. **Fuentes de Google** desde CDN: autoalojarlas mejora privacidad (Ley 1581) y velocidad.
4. **HSTS**: solo 30 días, sin `includeSubDomains`/`preload`; subir cuando el dominio definitivo esté estable.
5. **Código de reserva de 6 caracteres** + celular: razonable con el límite de intentos, pero depende del arreglo #2.
6. **Nombres de mesa en `innerHTML`** (`reservas.js`): vienen del panel de administración (confiables); aun así, escapar o usar `textContent`.
7. **Imágenes sin `width`/`height`** en inicio (se posicionan absolutas, riesgo bajo de CLS).
8. **Plan gratuito de Render**: el sitio se duerme tras inactividad y la base gratuita expira; subir de plan antes de lanzar.
9. `.gitignore` correcto (`.env`, `db.sqlite3`); `uv.lock` y `requirements.txt` deben actualizarse juntos al cambiar dependencias.
