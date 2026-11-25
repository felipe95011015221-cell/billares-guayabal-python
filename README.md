# Club de Billares Guayabal · versión Python (Django)

Sitio web del Club de Billares Guayabal (Medellín) hecho en **Python con Django**.
Incluye reservas de mesas con protección contra doble reserva, escuela de billar, torneos,
eventos, galería, contacto con WhatsApp y un panel de administración en español.

## Tecnologías

- **Python 3.12** y **Django 5.1**
- **PostgreSQL** en producción, **SQLite** en el computador local
- **Tailwind CSS 4**, ya compilado en `club/static/club/css/sitio.css`. Para publicar no hace falta Node.
- JavaScript sin librerías: menú, galería, formularios y asistente de reservas
- **WhiteNoise** sirve los archivos estáticos y **Gunicorn** es el servidor de producción

## Estructura

```
config/            ajustes, URLs, WSGI
club/
  negocio.py       datos del club (nombre, dirección, teléfono, horario) con su estado de verificación
  disponibilidad.py reglas puras de horarios y cruces (sin base de datos)
  servicios.py     crear reservas, inscripciones y cuadros de torneo (transacciones)
  api.py           endpoints JSON que usan los formularios
  admin.py         panel de administración
  templates/club/  páginas
  static/club/     CSS, JS, fotos y video
  tests.py         pruebas automáticas
tailwind/entrada.css  fuente de los estilos (solo para recompilar el CSS)
build.sh, render.yaml despliegue en Render
```

## Ejecutar en tu computador

Se necesita [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env      # pon DJANGO_DEBUG=1 para desarrollo
uv sync
uv run python manage.py migrate
uv run python manage.py cargar_datos_iniciales --demo   # --demo agrega reservas ficticias de prueba
uv run python manage.py createsuperuser                  # tu usuario del panel
uv run python manage.py runserver
```

- Sitio: http://localhost:8000
- Panel: http://localhost:8000/admin

Pruebas:

```bash
uv run python manage.py test club
```

Si cambias clases de Tailwind en las plantillas, recompila el CSS con Node:

```bash
npx @tailwindcss/cli@4.3.5 -i tailwind/entrada.css -o club/static/club/css/sitio.css --minify
```

## Cómo se evita la doble reserva

1. Antes de guardar, el servidor vuelve a verificar que la mesa esté libre dentro de una transacción que bloquea la mesa (`select_for_update`).
2. En PostgreSQL, la restricción `reservas_sin_solapamiento` (EXCLUDE con `btree_gist`) impide en la propia base de datos que dos reservas activas de la misma mesa se crucen, aunque lleguen al mismo tiempo.
3. Si alguien gana la carrera, la otra persona ve: «Otra persona acaba de tomar esta mesa en ese horario».

Los horarios son intervalos `[inicio, fin)`: una reserva de 8 a 10 y otra de 10 a 12 no chocan. Todo se calcula en hora de Bogotá (America/Bogota).

## Publicar en Render

1. Sube esta carpeta a un repositorio de GitHub.
2. En [render.com](https://render.com) elige **New → Blueprint** y selecciona el repositorio. Render lee `render.yaml` y crea:
   - el servicio web `billares-guayabal`
   - la base de datos PostgreSQL `billares-guayabal-db`
   - una `DJANGO_SECRET_KEY` aleatoria
3. Render te pedirá estas variables. Escríbelas tú, directamente en Render:
   - `SITE_URL`: la URL pública, por ejemplo `https://billares-guayabal.onrender.com`
   - `DJANGO_ALLOWED_HOSTS`: tu dominio propio si lo tienes; si no, déjala vacía
   - `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD`: tu usuario del panel. Se crea en el primer despliegue.
4. Cada despliegue ejecuta `build.sh`, que instala dependencias, copia los estáticos, migra la base y carga los datos iniciales. Nunca carga datos ficticios.

### Límites del plan gratuito de Render

- El sitio "se duerme" tras 15 minutos sin visitas. La primera visita después tarda unos 30–60 segundos.
- La base de datos gratuita **vence a los 30 días**. Para uso real conviene el plan pago, o una base externa (Neon o Supabase) conectada con `DATABASE_URL`.
- Las fotos que subas desde el panel se guardan en el disco del servidor, que en Render se borra en cada despliegue. Las fotos incluidas con el sitio (`club/static`) no se pierden. Para subir fotos desde el panel de forma permanente se necesita un disco persistente o un almacenamiento externo.

## Publicar en Vercel

Vercel detecta Django solo (por `manage.py`). Lo que hace en cada despliegue:

1. Instala las dependencias de `pyproject.toml`.
2. Corre `vercel_build.py`: migraciones, tabla de caché, datos iniciales y administrador.
3. Ejecuta `collectstatic` y sirve los estáticos desde su CDN.

Pasos:

1. En Vercel: **Add New → Project** e importa este repositorio.
2. En **Storage**, crea una base **Neon (Postgres)** y conéctala al proyecto. Vercel agrega `DATABASE_URL` sola.
3. En **Settings → Environment Variables** agrega:
   - `DJANGO_SECRET_KEY`: una clave larga y aleatoria
   - `SITE_URL`: por ejemplo `https://billares-guayabal-python.vercel.app`
   - `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD`: tu usuario del panel
4. Despliega. El dominio `*.vercel.app` se permite solo.

En Vercel el disco es de solo lectura, así que el panel no permite subir fotos nuevas. Las fotos se agregan en `club/static/club/img` y en `GALERIA_INICIAL` de `negocio.py`.

## Sala interactiva de reservas

La página `/reservas/` muestra la sala del club en 3D. Cada mesa es un objeto independiente, numerado y seleccionable, con su propia lámpara. Al elegir una mesa, el panel arma la reserva: mesa, modalidad, fecha, hora, duración, jugadores, nombre y valor estimado. El botón abre WhatsApp con todo escrito.

- **Tecnología**: [Three.js](https://threejs.org) r170 (WebGL), incluido en `club/static/club/vendor/three` con su licencia MIT. Se descarga solo cuando la sala se acerca a la pantalla, y las texturas se generan en el navegador, sin imágenes.
- **Vista ligera**: plano en CSS 3D, sin WebGL. Se usa sola en equipos con poca memoria o en modo de ahorro de datos, si falla WebGL, o si la persona la elige.
- **Distribución**: `club/static/club/js/sala/distribucion.js` (en metros). Cuando el club tenga el plano real, se cambian `SALA` y `PUESTOS` y la escena 3D y el plano ligero se ajustan solos.
- **Valor**: `precios.js` calcula por bloques de 30 minutos. Usa la tarifa de cada mesa del panel y la promoción de `negocio.py` (`PROMO_HORA_VALOR`, hasta `PROMO_HORA_HASTA_MIN`). La promoción solo se aplica mientras haya en el panel una promoción vigente cuyo título incluya «8.000».
- **Disponibilidad y pagos**: hoy no hay ocupación en línea, así que la sala no muestra estados y avisa que la reserva queda sujeta a confirmación. `disponibilidad.js` es el punto para conectar la disponibilidad en tiempo real; la escena ya pinta los estados (`marcarEstados`). Ahí mismo se agregaría un canal de pago.
- **Pruebas de JavaScript**: `node --test tests_js/`.

## Datos pendientes de confirmar con el club

En `club/negocio.py` cada dato tiene un estado: `confirmado`, `publico` (visto en fuentes públicas) o `pendiente`.

| Dato | Estado |
|---|---|
| Nombre | Confirmado |
| Dirección | Verificar con el club |
| Teléfono / WhatsApp 314 773 0533 | Verificar con el club |
| Horario | Verificar con el club |
| Número y tipo de mesas | Confirmado: 5 de carambola a tres bandas y 2 de pool. Tarifa por hora: COP 15.000. Renómbralas en el panel si quieres. |
| Tarifas | Por confirmar. Sin tarifa, la web muestra «Tarifa por confirmar». |
| Clases e instructores | Programas propuestos. Márcalos como «confirmada» en el panel cuando estén aprobados. |
| Torneos | Solo se publican los que marques como «publicado» en el panel. |

Mientras el club no confirme, las reservas en línea quedan como **«Solicitud pendiente de confirmación»**: el club las confirma desde el panel. Si prefieres confirmación automática, cambia el modo en *Configuración*.
