# Informe ejecutivo · Mejora integral de Billares Guayabal
Fecha: 2026-11-23 · Estado: listo para desplegar (sin publicar; falta confirmación del propietario)

## Equipo y método
Orquestador + 4 especialistas en paralelo (UX/UI y branding, Full Stack, Marketing y SEO, Calidad/Seguridad/Rendimiento), cada uno con archivos propios y contratos de integración entre ellos. El orquestador integró los resultados y verificó el conjunto.

## Qué cambió
**Diseño y UX** — Identidad inspirada en la mesa (azul paño, verde billar, amarillo y rojo de bola), tipografía Bricolage Grotesque + Hanken Grotesk, "marcador" de carambola como elemento propio. Hero con dos CTA (Reservar / WhatsApp) y datos reales del club, barra móvil con llamar, llegar, WhatsApp y reservar, menú móvil con foco gestionado, visor de galería accesible, formularios que enfocan el primer error. Objetivos táctiles ≥ 44 px, contraste AA, `prefers-reduced-motion`.
**Comercial** — Sección de **promociones administrable** desde el panel (no se publicó ninguna: el club no las ha confirmado), CTA persistentes, preguntas frecuentes, eventos corporativos con formulario más corto, WhatsApp prellenado con el código de reserva, medición de conversiones con `window.evento` (Google Analytics si hay `GA_ID`).
**Contenido y SEO** — Títulos y descripciones por página (40–51 y 118–134 caracteres), un H1 con intención de búsqueda por página, canonical, hreflang es-CO, Open Graph/Twitter, JSON-LD (WebSite + SportsActivityLocation + ReserveAction) solo con datos confirmados, sitemap. Plan de palabras clave, textos y checklist de Google Business Profile en `docs/SEO.md`.
**Rendimiento** — Fuentes propias (112 KB, sin Google Fonts), CSS 77 → 12,7 KB con gzip, HTML 45 → 10 KB con gzip, imágenes recomprimidas (p. ej. 675 → 299 KB), `<img>` con dimensiones, compresión de texto.
**Seguridad** — Correcciones de la auditoría (500 por JSON inválido, límite de envíos evadible, bucle por intervalo 0, HTML sin escapar), CSP, Permissions-Policy, COOP, HSTS 1 año, límite de envíos en caché compartida, validación de imágenes subidas (tipo y 5 MB), acciones masivas que respetan cupos, CSV con neutralización de fórmulas.
**Panel** — Promociones, origen de la reserva, exportación CSV, búsquedas y filtros.

## Pruebas
- 71 pruebas automáticas, todas OK (25 al inicio; 46 nuevas, incluidas regresiones de cada hallazgo).
- `check --deploy` con variables de producción: solo avisos de HSTS con subdominios/preload, desactivados a propósito mientras el dominio sea *.onrender.com.
- Chrome sin ventana: 5 páginas sin violaciones de CSP; capturas revisadas de inicio, reservas, eventos, galería y contacto.
- Enlaces: 0 rotos, local y producción (Unsplash responde 401 a bots: aviso, no error).
- No se detectaron secretos en el repositorio.

## Qué NO se pudo comprobar o queda abierto
1. **Benchmarking limitado**: solo se verificó un referente local (una nota de prensa de 2014); el resto son clubes internacionales. Las prácticas son generales, no datos del mercado de Medellín (`docs/BENCHMARK.md`).
2. **Móvil real a 390 px, tabletas y navegadores reales** (Safari iOS): Chrome sin ventana tiene ancho mínimo ~500 px; se revisó a 500 px.
3. **Datos del negocio sin confirmar**: dirección, teléfono, horario, correo, redes, tarifas, instructores. Siguen marcados «por confirmar» y el JSON-LD los incluirá solos al confirmarse.
4. **Fotos subidas desde el panel se pierden en Render** (disco efímero). Decidir almacenamiento antes de usarlas (`docs/MEDIA.md`).
5. **Política de datos** sigue en borrador; debe revisarla el responsable (razón social, NIT, canal) y mencionar Google Maps/Analytics.
6. **Video de 8,7 MB** sin recomprimir (no hay ffmpeg) y sin subtítulos.
7. **CSP** conserva `'unsafe-inline'` en scripts; endurecer requiere mover scripts en línea.
8. **Dominio propio**: configurar `SITE_URL`, redirección 301 desde onrender.com y luego HSTS con subdominios.
9. El plan gratuito de Render duerme el sitio y su base de datos expira.
10. No se midió Core Web Vitals reales ni se comparó 1 a 1 con producción (la comparación local usa servidor de desarrollo).

## Para publicar (requiere su aprobación)
Los cambios están solo en el equipo local (`~/billares-guayabal-python`); no se ha subido nada a GitHub ni a Render. Al desplegar, `build.sh` ejecuta migraciones (0003: promociones y origen de reserva), crea la tabla de caché y verifica el despliegue.
