# SEO local, copy y estrategia comercial · Club de Billares Guayabal

Fecha: 2026-11-23. Documento de trabajo del agente de marketing/SEO.
Convenciones: **[APLICAR]** = texto listo para pegar en plantillas/vistas. **[PROPUESTA]** = «propuesta sujeta a aprobación del club», no se publica sin visto bueno. **[CONFIRMAR]** = dato que debe validar el club. No hay precios, descuentos, años de trayectoria, premios, reseñas ni redes inventados.

## 0. Estado técnico implementado (ya en el repo)
- `head.html`: `<title>` único, description, `robots` (index o noindex según `seo_noindex`), canonical, `hreflang es-CO` y `x-default`, Open Graph con `og:image` (913×512, con alt y tipo), Twitter Card completa, `theme-color`, preconnect y fuentes sin cambios. Sin geo-meta ni `keywords` (obsoleto): la dirección está en estado «público», no confirmado.
- `context_processors.py`: JSON-LD en `@graph` (WebSite + SportsActivityLocation) con `ReserveAction` hacia `/reservas/`. **Solo** entran datos con estado «confirmado»: hoy, nombre y ciudad. Dirección, teléfono y horario entrarán solos cuando el club los confirme en `negocio.py`; `sameAs` cuando haya Instagram/Facebook confirmados; sin calificaciones.
- `sitemaps.py`: prioridades (inicio 1.0, reservas 0.9, torneos/escuela/eventos 0.8, club/contacto 0.7, galería 0.5) y changefreq por página. **Sin `lastmod`** en páginas fijas: no existe fecha real de edición y una inexacta perjudica. Si se quiere, Dev puede añadir un `modificado_en` a Torneo.
- `negocio.py`: mensajes de WhatsApp con origen y campos para completar; claves nuevas `reservas_carambola` y `reservas_pool`; alts descriptivos (las fotos de stock dicen «Foto de referencia» para no hacerlas pasar por el club).
- `robots.txt` ya bloquea `/admin/`, `/api/` y `/reservas/consultar/`.

## 1. Plan de palabras clave locales

| Palabra clave | Intención | Página destino | Dónde reforzar |
|---|---|---|---|
| billares en Medellín | Navegacional/local: encontrar un salón | Inicio | H1 de inicio, title, GBP |
| billar Guayabal / billares Guayabal | Local, alta intención de visita | Inicio y Contacto | Dirección, mapa, «cómo llegar» |
| club de billar Medellín | Informativa/comparativa | El club | H1 y texto de «El club» |
| carambola tres bandas Medellín | Específica de modalidad | El club (sección modalidades), Torneos | H2 de modalidad |
| jugar pool en Medellín | Transaccional ligera | Reservas, Inicio | Tarjeta de modalidad pool |
| reservar mesa de billar Medellín | Transaccional | Reservas | Title, H1, JSON-LD ReserveAction |
| clases de billar Medellín / aprender carambola | Transaccional | Escuela | H1 escuela, FAQ |
| torneos de billar Medellín | Informativa/transaccional | Torneos | Una URL por torneo con fecha |
| eventos corporativos billar Medellín / cumpleaños con billar | Transaccional B2B/B2C | Eventos | H2 por tipo de plan |
| cómo llegar billares Guayabal | Local, móvil | Contacto | Mapa, WhatsApp de ubicación |

Reglas: una intención por página; nada de relleno de palabras clave; la ciudad aparece en title y H1 solo donde aporta.

## 2. Estructura recomendada por página (H1/H2) **[APLICAR]**

- **Inicio**: H1 «El billar se vive en Guayabal». H2: «Carambola a tres bandas y pool», «Reserva tu mesa en línea», «Escuela de billar», «Torneos y eventos», «Así se vive el club», «Dónde estamos».
- **El club**: H1 «Un lugar para jugar, competir, aprender y compartir.» H2: «La mesa no miente», «Cuatro razones para volver», «Dos maneras de vivir el billar».
- **Reservas**: H1 «Reserva tu mesa de billar en Medellín». H2 de pasos: «Elige tu juego», «Fecha y hora», «Escoge tu mesa», «Tus datos». Añadir bloque «Antes de reservar» (reglas, ver §3) y FAQ corta.
- **Escuela**: H1 «Clases de billar en Medellín». H2: «Programas por niveles», «Próximos horarios», «Cómo funciona la pre-inscripción».
- **Torneos**: H1 «Torneos de billar en Medellín». H2: «Próximos torneos», «Cómo inscribirte», «Resultados anteriores».
- **Torneo (detalle)**: H1 = nombre del torneo; H2: «Formato y requisitos», «Cupos e inscripción», «Cuadro».
- **Eventos**: H1 «Eventos con billar en Medellín». H2: «Empresas», «Celebraciones», «Jornadas recreativas», «Cuéntanos tu plan».
- **Galería**: H1 «Galería del club». **Contacto**: H1 «Contacto y cómo llegar». Añadir H2 «Preguntas frecuentes» (§5) en Contacto o Reservas.

## 3. COPY DECK (español de Colombia)

### 3.1 Cabeceras y CTAs **[APLICAR]**
| Lugar | Texto |
|---|---|
| CTA principal | Reservar mesa |
| CTA secundario | Escribir por WhatsApp |
| Conocer | Conocer el club |
| Consultar | Consultar mi reserva |
| Escuela | Ver programas · Pre-inscribirme |
| Torneos | Ver torneos · Inscribirme al torneo |
| Eventos | Cotizar mi evento |
| Ubicación | Cómo llegar · Llamar al club |
| Cierre de página | «¿Listo para jugar? Reserva tu mesa o escríbenos por WhatsApp.» |
| Hero subtítulo | Carambola a tres bandas y pool en Guayabal, Medellín. Reserva tu mesa en línea en menos de dos minutos. |
| Inicio – El club | Un punto de encuentro en Medellín para quienes disfrutan el billar: jugar con amigos, entrenar el tiro de tres bandas o medirse con rivales. |
| Modalidad carambola | Tres bolas, una mesa sin buchacas. Geometría, paciencia y control. → «Reservar mesa de carambola» |
| Modalidad pool | Ritmo ágil, buchacas y estrategia. Ideal para grupos. → «Reservar mesa de pool» |
| Video | «Así se vivió nuestro último evento» (sábado 21 de noviembre de 2026) |

### 3.2 Reservas **[APLICAR]**
- Intro: «Elige modalidad, fecha y hora. Revisamos la disponibilidad de cada mesa antes de registrar tu solicitud.»
- Microcopy de campos: Nombre completo («Así te llamamos cuando llegues»); Celular («Lo usamos solo para confirmar tu reserva»); Correo («Te enviamos aquí el resumen de tu reserva»; si el correo es obligatorio hoy, confirmar con Dev).
- Consentimiento: «Autorizo el tratamiento de mis datos personales para gestionar esta reserva, según la política de datos (Ley 1581 de 2012).»
- Éxito (modo manual): «¡Listo! Recibimos tu solicitud. Tu código es XXXXXX. La reserva queda confirmada cuando el club la apruebe; te avisaremos por el celular que dejaste.»
- Éxito (modo automático): «¡Reserva confirmada! Guarda tu código XXXXXX. Te esperamos.»
- Error mesa tomada: «Otra persona acaba de tomar esta mesa en ese horario. Escoge otra mesa u otra hora.»
- Error genérico: «No pudimos enviar tu solicitud. Revisa tu conexión e inténtalo de nuevo, o escríbenos por WhatsApp.»
- Error de campo: «Escribe tu nombre completo.» · «Escribe un celular colombiano de 10 dígitos.» · «Revisa el correo: parece que falta algo.» · «Acepta el tratamiento de datos para continuar.»
- Sin horas: «Para esa fecha no hay horas disponibles. Prueba con otro día o escríbenos por WhatsApp.»
- Bloque «Antes de reservar» **[PROPUESTA]** (cada punto requiere confirmación del club): tiempo de espera de la mesa, cancelaciones y cambios, menores de edad, consumo mínimo. «Políticas por confirmar con el club.»

### 3.3 Escuela **[APLICAR]** (los programas son propuesta del club)
- Intro: «Programas por niveles para aprender desde cero o afinar tu técnica en carambola y pool.»
- Aviso: «Estos programas son una propuesta inicial. Instructores, precios y horarios se publican cuando el club los confirma. Puedes pre-inscribirte y te contactamos.»
- Éxito: «¡Pre-inscripción recibida! Tu código es XXXXXX. El club te contactará para confirmar horario, instructor y valor.»
- Sin horarios: «Aún no hay horarios publicados para este programa. Escríbenos por WhatsApp y deja tu interés.» → «Quiero que me avisen»
- Campo nivel: «¿Cuál es tu nivel?» · Nunca he jugado · Juego ocasionalmente · Juego con frecuencia · Compito.

### 3.4 Torneos **[APLICAR]**
- Intro: «Competencias de carambola a tres bandas y pool organizadas por el club. Consulta formato, requisitos y cupos.»
- Sin torneos: «Aún no hay torneos publicados. Cuando el club anuncie uno, verás aquí fecha, formato, cupos e inscripción.» → «Quiero que me avisen por WhatsApp»
- Inscripción éxito: «¡Inscripción recibida! Tu código es XXXXXX. Tu cupo queda pendiente hasta que el club lo confirme.»
- Torneo lleno: «Cupos completos. Escríbenos para entrar a la lista de espera.» **[CONFIRMAR]** que el club maneje lista de espera.
- Plantilla de torneo **[PROPUESTA]** (campos que el club llena en el panel): nombre · modalidad · fecha y hora de inscripción y de inicio · formato (eliminación directa, todos contra todos) · requisitos (nivel, edad) · cupos · valor · premiación **[CONFIRMAR]** · reglamento.

### 3.5 Eventos y corporativos **[APLICAR]** salvo lo marcado
- Intro: «Diseñamos contigo una experiencia de billar para tu grupo. Cuéntanos qué tienes en mente.»
- Tipos: Eventos privados · Encuentros empresariales · Celebraciones · Jornadas recreativas · Actividades grupales.
- Empresas: «Integra a tu equipo en un plan distinto a la oficina: partidas, mini torneo interno y buena conversación.»
- Celebraciones: «Cumpleaños, despedidas y reencuentros alrededor de la mesa.»
- Éxito: «Solicitud recibida. Tu código es XXXXXX. Está sujeta a disponibilidad y aprobación del club; te contactaremos para revisar los detalles.»
- Aviso: «Capacidad, paquetes y valores se definen con el club para cada evento.»
- Paquetes tipo **[PROPUESTA]** (sin precios): «Jornada integración», «Cumpleaños en mesa», «Mini torneo de empresa». Qué incluye cada uno: **[CONFIRMAR]**.

### 3.6 Promociones (plantillas) **[PROPUESTA: sujeta a aprobación del club; sin valores]**
- «Entre semana, más tiempo de mesa» → detalle de la oferta, días y horas: **[CONFIRMAR]**.
- «Trae a tu equipo» (grupos de oficina) → condiciones: **[CONFIRMAR]**.
- «Tu primera clase» → condiciones: **[CONFIRMAR]**.
- «Noche de torneo relámpago» → fecha, cupos y valor: **[CONFIRMAR]**.
Estructura de cada tarjeta: título, condición en una línea, vigencia, botón «Reservar mesa» o «Escribir por WhatsApp». Nunca publicar una promoción sin vigencia.

### 3.7 Contacto **[APLICAR]**
- Intro: «Escríbenos por WhatsApp según lo que necesites, o déjanos un mensaje.»
- Éxito formulario: «Mensaje enviado. Gracias por escribirnos; te responderemos lo antes posible.»
- Dirección y teléfono: mostrar con el sello «por confirmar» hasta validar (ya lo hace `negocio.py`).

## 4. Meta titles (≤60) y descriptions (≤155) **[APLICAR en views.py: pedir a Dev]**
Los títulos son completos: usar `seo_titulo_absoluto` (la plantilla agrega « · Club de Billares Guayabal» a `seo_titulo`, lo que pasa de 60 en Eventos, Torneos y Reservas).

| Página | Title | Description |
|---|---|---|
| Inicio | Billares en Medellín · Club de Billares Guayabal | Club de billar en Guayabal, Medellín: carambola a tres bandas y pool. Reserva tu mesa en línea y conoce la escuela, torneos y eventos. |
| Club | El club · Billar en Guayabal, Medellín | Conoce el Club de Billares Guayabal: mesas de carambola a tres bandas y pool, ambiente para jugar, aprender y competir en Medellín. |
| Reservas | Reservar mesa de billar en Medellín \| Guayabal | Reserva tu mesa de carambola o pool en el Club de Billares Guayabal. Mira la disponibilidad, escoge hora y recibe tu código. |
| Escuela | Clases de billar en Medellín · Escuela Guayabal | Clases de billar en Medellín: carambola a tres bandas y pool, para principiantes y jugadores avanzados. Pre-inscríbete en línea. |
| Torneos | Torneos de billar en Medellín · Guayabal | Torneos de carambola a tres bandas y pool en el Club de Billares Guayabal: fechas, formato, cupos e inscripción en línea. |
| Eventos | Eventos con billar en Medellín · Empresas y fiestas | Eventos empresariales, cumpleaños y celebraciones con billar en Guayabal, Medellín. Cuéntanos tu plan y te respondemos con propuesta. |
| Galería | Galería · Club de Billares Guayabal, Medellín | Fotos del Club de Billares Guayabal en Medellín: el salón, las mesas de carambola, la barra y el ambiente de las noches de juego. |
| Contacto | Contacto y cómo llegar · Billares Guayabal | Escríbenos por WhatsApp o déjanos un mensaje. Ubicación, mapa y cómo llegar al Club de Billares Guayabal, en Medellín. |
| Privacidad | Tratamiento de datos personales · Billares Guayabal | Política de tratamiento de datos personales del Club de Billares Guayabal. |
| Torneo (detalle) | `{nombre} · Torneo de billar en Medellín` (truncar a 60) | `{formato}. {descripción}` recortada a 155 en palabra completa (hoy corta a 160 sin cuidar palabra). |

Todas las longitudes se midieron: títulos 38–51, descriptions 74–135.

## 5. Preguntas frecuentes **[APLICAR]** (solo hechos del repo o «confirmar con el club»)

1. **¿Qué modalidades se juegan en el club?** Carambola a tres bandas (mesa sin buchacas) y pool (mesa con buchacas, bola 8 y bola 9).
2. **¿Cómo reservo una mesa?** Elige modalidad, fecha, hora y mesa en la página de Reservas, deja tus datos y recibes un código. También puedes escribirnos por WhatsApp.
3. **¿Mi reserva queda confirmada al instante?** Depende de la configuración del club. Si ves «solicitud», queda pendiente hasta que el club la confirme. Confirmar con el club cómo opera hoy.
4. **¿Cómo consulto o encuentro mi reserva?** En «Consultar mi reserva», con tu código y tu celular.
5. **¿Cuánto cuesta la mesa?** El valor por hora está por confirmar con el club; se muestra en el asistente de reservas cuando esté definido.
6. **¿Cuál es el horario?** Según plataformas públicas, todos los días de 9:00 a. m. a 2:00 a. m.; confirmar con el club.
7. **¿Dónde queda?** Carrera 52 #9-17, Guayabal, Medellín (dato por confirmar). Hay mapa y botón «Cómo llegar» en Contacto.
8. **¿Hay clases para principiantes?** La escuela tiene programas por niveles propuestos (desde cero hasta competencia); instructores, precios y horarios se confirman con el club. Puedes pre-inscribirte.
9. **¿Cómo me inscribo en un torneo?** Cuando hay un torneo publicado, la inscripción se hace desde su página; el cupo queda pendiente hasta que el club lo confirme.
10. **¿Pueden organizar eventos para empresas o cumpleaños?** Sí se reciben solicitudes de eventos privados, empresariales y celebraciones; quedan sujetas a disponibilidad y aprobación. Capacidad y valores: confirmar con el club.
11. **¿Cómo tratan mis datos?** Se usan para gestionar tu reserva, inscripción o mensaje, según la Ley 1581 de 2012 y la política de datos del sitio.

Añadir marcado `FAQPage` solo si estas respuestas se publican visibles en la página y ya están confirmadas (Google exige que el contenido sea visible). No agregado todavía.

## 6. Checklist fuera del sitio (para el club)

**Google Business Profile**
- [ ] Crear/reclamar la ficha «Club de Billares Guayabal» y verificarla (llamada o video).
- [ ] Categoría principal: salón de billar; secundarias: club deportivo, bar (según aplique).
- [ ] Dirección, teléfono y horario idénticos a los del sitio (NAP consistente) y confirmados en `negocio.py`.
- [ ] Enlaces: sitio, «Reservar» → `/reservas/`, WhatsApp.
- [ ] Mínimo 10 fotos reales (salón, mesas, barra, fachada, evento) y subir novedades cada semana (torneos, eventos).
- [ ] Servicios: carambola, pool, clases, eventos.
- [ ] Atributos: accesibilidad, pagos, consumo en sitio (los reales).

**Reseñas**
- [ ] Pedir reseña a clientes en persona y por WhatsApp con el enlace corto de GBP.
- [ ] Responder todas, buenas y malas, en 48 h. No comprar ni redactar reseñas.
- [ ] No mostrar estrellas en el sitio ni en JSON-LD hasta que existan reseñas verificables.

**Citas locales y enlaces**
- [ ] Registrar el club en directorios de billar, Páginas Amarillas, Foursquare, Apple Business Connect y Bing Places con los mismos datos.
- [ ] Contactar a la Liga Antioqueña de Billar y a la Federación para figurar como sede de torneos **[verificar existencia y requisitos]**.
- [ ] Enlaces de aliados: empresas cercanas en Guayabal, universidades, comunas, proveedores de mesas y paños.
- [ ] Notas de prensa o blogs locales cuando haya un torneo grande.

**Redes y analítica**
- [ ] Crear Instagram/Facebook y confirmar en `negocio.py` (activa `sameAs`).
- [ ] Verificar el sitio en Google Search Console y enviar `/sitemap.xml`; configurar GA4 (`GA_ID`).
- [ ] Dominio propio definitivo antes de lanzar (hoy onrender.com): cambiar `SITE_URL` y redirigir 301.
- [ ] Hacer que Render no duerma el sitio (plan de pago): la lentitud en el primer acceso penaliza posicionamiento y reservas.

## 7. Plan de fidelización **[PROPUESTA: sujeta a aprobación del club]**
1. **Lista de difusión por WhatsApp** (Business): invitar a clientes en la barra y en el formulario con casilla opcional de consentimiento (Ley 1581). Un mensaje semanal máximo: torneo, evento, horario especial. Confirmar con el club quién la administra.
2. **Torneos recurrentes**: un torneo mensual con la misma fecha («último sábado») y un ranking del año; resultados publicados en la página del torneo.
3. **Liga interna**: por modalidad, con fecha de cierre y puntos. Formato y premiación: **[CONFIRMAR]**.
4. **Tarjeta de lealtad** (física o digital): sellos por visita o por horas jugadas con un beneficio a definir por el club. Sin beneficio publicado hasta ser aprobado.
5. **Cumpleaños**: invitar a reservar mesa en su mes (usar dato solo si el cliente lo da).
6. **Clase de prueba y referidos**: «Trae a un amigo» con beneficio a definir.
7. **Mensaje posvisita** (WhatsApp, 1 día después): agradecimiento + enlace a reseña de Google.
8. **Medición**: reservas por semana, reservas repetidas por celular, clics a WhatsApp (evento en GA4), inscripciones por torneo.

## 8. Peticiones a otros agentes
- **Dev** (`views.py`): reemplazar `seo_titulo`/`seo_descripcion` por los de §4 usando `seo_titulo_absoluto` en todas las páginas indexables; en `torneo_detalle` recortar la description por palabra a 155. Opcional: `modificado_en` en Torneo para `lastmod`.
- **UX/UI**: pasar `wa_reservas_carambola`/`wa_reservas_pool` (nuevos en el context processor) a los botones «Reservar mesa de carambola/pool» y `wa_clases` a la escuela; evitar H1 duplicados; usar el alt de `negocio.FOTOS` en las `<img>` (hoy varias van con `alt=""` por ser decorativas, correcto).
- **Calidad**: tras los cambios de otros agentes, 11 pruebas fallan hoy por `no such table: club_promocion` (falta migración del modelo Promoción, no es de SEO); reconstruir el sitemap en el build y comprobar que los archivos de fuentes autoalojadas actualicen el `preconnect` de `head.html`.
- **Orquestador**: en la fase de aplicación, pegar §3 y §5 en plantillas; confirmar con el club dirección, teléfono, horario, correo y redes para activar JSON-LD completo.
