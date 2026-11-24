/* Asistente de reservas: modalidad → fecha/hora → mesa → datos → código. */
(function () {
  "use strict";
  const cfg = JSON.parse(document.getElementById("config-reserva").textContent);
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  const DIAS = ["L", "M", "M", "J", "V", "S", "D"];
  const ESTADOS = {
    disponible: { texto: "Disponible", clase: "border-ok/50 text-[#8fd0ad]", punto: "bg-[#5fbf8a]" },
    pendiente: { texto: "Pendiente de confirmación", clase: "border-alerta/40 text-alerta", punto: "bg-alerta" },
    reservada: { texto: "Reservada", clase: "border-oro/40 text-oro", punto: "bg-oro" },
    ocupada: { texto: "Ocupada", clase: "border-error/40 text-[#e09080]", punto: "bg-error" },
    bloqueada: { texto: "Bloqueada", clase: "border-marfil/20 text-marfil/50", punto: "bg-marfil/40" },
  };
  const NOMBRES_PASO = ["Modalidad", "Fecha y hora", "Mesa", "Tus datos"];
  const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const cop = (v) => (v == null ? "Tarifa por confirmar" : "$ " + Number(v).toLocaleString("es-CO"));
  const fmtFecha = new Intl.DateTimeFormat("es-CO", { timeZone: "America/Bogota", weekday: "long", day: "numeric", month: "long", year: "numeric" });
  const fmtHora = new Intl.DateTimeFormat("es-CO", { timeZone: "America/Bogota", hour: "numeric", minute: "2-digit", hour12: true });
  const etiquetaMin = (m) => { const h = Math.floor(m / 60) % 24; const h12 = h % 12 === 0 ? 12 : h % 12; return `${h12}:${String(m % 60).padStart(2, "0")} ${h < 12 ? "a. m." : "p. m."}`; };

  const st = { paso: 0, modalidad: null, fecha: null, duracion: null, inicio: null, mesa: null, mes: cfg.hoy.slice(0, 7), mesas: [] };
  st.duracion = cfg.duraciones.some((d) => d.min === 120) ? 120 : cfg.duraciones[0].min;

  function error(msg) { const e = $("#error-asistente"); e.textContent = msg || ""; e.classList.toggle("oculto", !msg); }

  function irA(p) {
    st.paso = p; error("");
    $$("[data-paso]").forEach((el) => el.classList.toggle("oculto", Number(el.dataset.paso) !== p));
    $$("[data-paso-ind]").forEach((li) => {
      const i = Number(li.dataset.pasoInd);
      li.querySelector("span").className = `block h-0.5 rounded-full ${i <= p ? "bg-oro" : "bg-marfil/15"}`;
      const t = li.querySelectorAll("span")[1]; t.classList.toggle("text-oro", i === p); t.classList.toggle("text-marfil/75", i !== p);
    });
    $("#paso-movil").textContent = `Paso ${p + 1} de 4 · ${NOMBRES_PASO[p]}`;
    $("#asistente").scrollIntoView({ behavior: "smooth", block: "start" });
    if (p === 2) cargarMesas();
    resumen();
  }
  $$("[data-ir]").forEach((b) => b.addEventListener("click", () => irA(Number(b.dataset.ir))));

  function resumen() {
    $("#r-modalidad").textContent = st.modalidad ? (st.modalidad === "pool" ? "Pool" : "Carambola a tres bandas") : "—";
    $("#r-fecha").textContent = st.fecha ? fmtFecha.format(new Date(`${st.fecha}T12:00:00-05:00`)) : "—";
    $("#r-horario").textContent = st.inicio != null ? `${etiquetaMin(st.inicio)} – ${etiquetaMin(st.inicio + st.duracion)}` : "—";
    $("#r-duracion").textContent = cfg.duraciones.find((d) => d.min === st.duracion)?.texto || "—";
    const m = st.mesas.find((x) => x.id === st.mesa);
    $("#r-mesa").textContent = m ? m.nombre : "—";
    $("#r-valor").textContent = m ? cop(m.valor_estimado) : "—";
  }

  // ---- Paso 0: modalidad
  $$("[data-modalidad]").forEach((b) => b.addEventListener("click", () => {
    st.modalidad = b.dataset.modalidad;
    $$("[data-modalidad]").forEach((x) => { x.classList.toggle("border-oro", x === b); x.classList.toggle("bg-oro/10", x === b); });
    reiniciarHora(); irA(1);
  }));

  // ---- Paso 1: calendario
  function pintarCalendario() {
    const [a, m] = st.mes.split("-").map(Number);
    $("#mes-titulo").textContent = `${MESES[m - 1]} ${a}`;
    $("#mes-anterior").disabled = st.mes <= cfg.hoy.slice(0, 7);
    $("#mes-siguiente").disabled = st.mes >= cfg.maximo.slice(0, 7);
    const cal = $("#calendario");
    cal.innerHTML = DIAS.map((d) => `<div class="pb-2 text-center text-xs font-semibold text-marfil/40">${d}</div>`).join("");
    const desfase = (new Date(Date.UTC(a, m - 1, 1)).getUTCDay() + 6) % 7;
    const diasMes = new Date(Date.UTC(a, m, 0)).getUTCDate();
    for (let i = 0; i < desfase; i++) cal.insertAdjacentHTML("beforeend", "<div></div>");
    for (let d = 1; d <= diasMes; d++) {
      const f = `${st.mes}-${String(d).padStart(2, "0")}`;
      const off = f < cfg.hoy || f > cfg.maximo;
      const sel = f === st.fecha;
      const b = document.createElement("button");
      b.type = "button"; b.textContent = d; b.disabled = off; b.setAttribute("aria-label", f); b.setAttribute("aria-selected", String(sel));
      b.className = `relative flex aspect-square min-h-11 items-center justify-center rounded-lg text-sm font-medium transition ${sel ? "bg-oro text-carbon" : "hover:bg-marfil/10"} ${off ? "cursor-not-allowed text-marfil/20 hover:bg-transparent" : ""}`;
      b.addEventListener("click", () => { st.fecha = f; pintarCalendario(); reiniciarHora(); cargarFranjas(); resumen(); });
      cal.appendChild(b);
    }
  }
  function moverMes(delta) { const [a, m] = st.mes.split("-").map(Number); st.mes = new Date(Date.UTC(a, m - 1 + delta, 1)).toISOString().slice(0, 7); pintarCalendario(); }
  $("#mes-anterior").addEventListener("click", () => moverMes(-1));
  $("#mes-siguiente").addEventListener("click", () => moverMes(1));

  function pintarDuraciones() {
    $("#duraciones").innerHTML = "";
    cfg.duraciones.forEach((d) => {
      const b = document.createElement("button");
      b.type = "button"; b.textContent = d.texto; b.setAttribute("aria-pressed", String(st.duracion === d.min));
      b.className = `h-14 rounded-xl border text-sm font-semibold transition ${st.duracion === d.min ? "border-oro bg-oro text-carbon" : "border-marfil/15 hover:border-oro/60"}`;
      b.addEventListener("click", () => { st.duracion = d.min; pintarDuraciones(); reiniciarHora(); cargarFranjas(); resumen(); });
      $("#duraciones").appendChild(b);
    });
  }
  function reiniciarHora() { st.inicio = null; st.mesa = null; }

  async function obtener(url) {
    const r = await fetch(url, { cache: "no-store" });
    const j = await r.json();
    if (!j.ok) throw new Error(j.error);
    return j.data;
  }

  async function cargarFranjas() {
    const caja = $("#franjas");
    if (!st.fecha || !st.modalidad) return;
    caja.innerHTML = `<div class="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-6">${"<div class='h-14 animate-pulse rounded-xl bg-marfil/5'></div>".repeat(12)}</div>`;
    try {
      const d = await obtener(`/api/disponibilidad/?modalidad=${st.modalidad}&fecha=${st.fecha}&duracion=${st.duracion}`);
      if (!d.franjas.length) {
        caja.innerHTML = '<p class="rounded-xl border border-dashed border-marfil/15 p-6 text-sm text-marfil/55">No hay horarios disponibles para esta fecha y duración. Prueba otro día o una duración menor.</p>';
        return;
      }
      const grid = document.createElement("div");
      grid.className = "grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-6";
      d.franjas.forEach((f) => {
        const b = document.createElement("button");
        b.type = "button"; b.disabled = f.libres === 0;
        b.className = `flex h-14 flex-col items-center justify-center rounded-xl border text-sm transition ${f.libres === 0 ? "cursor-not-allowed border-marfil/5 text-marfil/25 line-through" : "border-marfil/15 hover:border-oro/60"}`;
        b.innerHTML = `<span class="font-semibold">${esc(f.etiqueta)}</span><span class="text-xs opacity-60">${f.libres === 0 ? "Sin mesas" : `${f.libres} libre${f.libres > 1 ? "s" : ""}`}</span>`;
        b.addEventListener("click", () => { st.inicio = f.inicio_min; st.mesa = null; irA(2); });
        grid.appendChild(b);
      });
      caja.innerHTML = ""; caja.appendChild(grid);
    } catch (e) {
      caja.innerHTML = ""; error(e.message || "No pudimos consultar la disponibilidad.");
    }
  }

  // ---- Paso 2: mesas
  async function cargarMesas() {
    const caja = $("#mesas");
    caja.innerHTML = "<div class='h-40 animate-pulse rounded-2xl bg-marfil/5'></div>".repeat(4);
    try {
      const d = await obtener(`/api/disponibilidad/?modalidad=${st.modalidad}&fecha=${st.fecha}&duracion=${st.duracion}&inicio=${st.inicio}`);
      st.mesas = d.mesas || [];
      if (!st.mesas.some((m) => m.id === st.mesa && m.estado === "disponible")) st.mesa = null;
      pintarMesas();
    } catch (e) {
      caja.innerHTML = ""; error(e.message);
    }
  }
  function pintarMesas() {
    const caja = $("#mesas");
    caja.innerHTML = "";
    if (!st.mesas.length) { caja.innerHTML = '<p class="rounded-xl border border-dashed border-marfil/15 p-6 text-sm text-marfil/55">No hay mesas configuradas para esta modalidad.</p>'; }
    st.mesas.forEach((m) => {
      const ui = ESTADOS[m.estado];
      const libre = m.estado === "disponible";
      const sel = st.mesa === m.id;
      const b = document.createElement("button");
      b.type = "button"; b.disabled = !libre; b.setAttribute("aria-pressed", String(sel));
      b.className = `rounded-2xl border p-6 text-left transition ${sel ? "border-oro bg-oro/10" : libre ? "border-marfil/15 hover:-translate-y-0.5 hover:border-oro/60" : "cursor-not-allowed border-marfil/10 opacity-55"}`;
      b.innerHTML = `${miniMesa(libre)}<span class="mt-5 flex items-center justify-between"><span class="font-display text-2xl">${esc(m.nombre)}</span>${sel ? '<span class="text-oro">✓</span>' : ""}</span>
        <span class="mt-3 inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-semibold ${ui.clase}"><span class="h-1.5 w-1.5 rounded-full ${ui.punto}"></span>${ui.texto}</span>
        <span class="mt-3 block text-xs text-marfil/55">${m.tarifa_hora == null ? "Tarifa por confirmar" : `${cop(m.tarifa_hora)} / hora`}</span>`;
      b.addEventListener("click", () => { st.mesa = m.id; pintarMesas(); resumen(); });
      caja.appendChild(b);
    });
    $("#continuar-datos").disabled = !st.mesa;
    resumen();
  }
  function miniMesa(activa) {
    const paño = activa ? "#164b37" : "#2a332e";
    const buchacas = st.modalidad === "pool" ? [[9, 9], [60, 8], [111, 9], [9, 55], [60, 56], [111, 55]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="3.4" fill="#0b0f0d"/>`).join("") : "";
    const bolas = st.modalidad === "pool" ? '<circle cx="38" cy="32" r="3.2" fill="#f2ebdd"/><circle cx="80" cy="32" r="3.2" fill="#c4453a"/><circle cx="86" cy="28" r="3.2" fill="#e8c44a"/><circle cx="86" cy="36" r="3.2" fill="#1f3c8a"/>' : '<circle cx="40" cy="30" r="3.2" fill="#f2ebdd"/><circle cx="78" cy="22" r="3.2" fill="#e8c44a"/><circle cx="70" cy="40" r="3.2" fill="#c4453a"/>';
    return `<svg viewBox="0 0 120 64" class="h-14 w-auto" aria-hidden="true"><rect x="2" y="2" width="116" height="60" rx="6" fill="#3a2a1d"/><rect x="9" y="9" width="102" height="46" rx="2" fill="${paño}"/>${buchacas}${bolas}</svg>`;
  }
  $("#actualizar-mesas").addEventListener("click", cargarMesas);
  $("#continuar-datos").addEventListener("click", () => irA(3));

  // ---- Paso 3: envío
  $("#form-reserva").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.currentTarget;
    $$("[data-error]", form).forEach((el) => { el.textContent = ""; el.classList.add("oculto"); });
    const fd = new FormData(form);
    const cuerpo = {
      modalidad: st.modalidad, fecha: st.fecha, inicio: st.inicio, duracion: st.duracion, mesa_id: st.mesa,
      nombre: fd.get("nombre"), celular: fd.get("celular"), correo: fd.get("correo"),
      acepta_datos: form.acepta_datos.checked, website: fd.get("website"),
    };
    const boton = $('[type="submit"]', form);
    const texto = boton.textContent;
    boton.disabled = true; boton.textContent = "Verificando…";
    const r = await window.enviarJson("/api/reservas/", cuerpo);
    boton.disabled = false; boton.textContent = texto;
    if (r.ok) return mostrarResultado(r.data);
    error(r.error);
    Object.entries(r.campos || {}).forEach(([k, v]) => { const el = $(`[data-error="${k}"]`, form); if (el) { el.textContent = v; el.classList.remove("oculto"); } });
    if (/tomar esta mesa|disponible/i.test(r.error)) { irA(2); error(r.error); }
  });

  function mostrarResultado(d) {
    error("");
    const pendiente = d.estado === "pendiente";
    $("#asistente").classList.add("oculto");
    const res = $("#resultado");
    res.classList.remove("oculto");
    $("#res-titulo").textContent = pendiente ? "Solicitud pendiente de confirmación" : "Reserva confirmada";
    $("#res-texto").textContent = pendiente
      ? "Recibimos tu solicitud. Aún NO está aprobada: el club la revisará y te contactará por WhatsApp o llamada para confirmarla."
      : "Tu mesa quedó reservada. Te esperamos.";
    $("#res-codigo").textContent = d.codigo;
    $("#res-mesa").textContent = `${d.mesa} · ${d.modalidad === "pool" ? "Pool" : "Carambola"}`;
    $("#res-valor").textContent = d.valor_estimado == null ? "Por confirmar" : cop(d.valor_estimado);
    const ini = new Date(d.inicio), fin = new Date(d.fin);
    $("#res-fecha").textContent = `${fmtFecha.format(ini)} · ${fmtHora.format(ini)} – ${fmtHora.format(fin)}`;
    const texto = `Reserva Club de Billares Guayabal\nCódigo: ${d.codigo}\nEstado: ${d.estado_texto}\n${d.modalidad === "pool" ? "Pool" : "Carambola"} · ${d.mesa}\n${fmtFecha.format(ini)}, ${fmtHora.format(ini)} – ${fmtHora.format(fin)}`;
    $("#res-compartir").href = `https://wa.me/?text=${encodeURIComponent(texto)}`;
    // El servidor devuelve el enlace de WhatsApp ya prellenado con el código; si faltara, se arma en el navegador.
    $("#res-avisar").href = d.whatsapp_url || `${cfg.whatsapp}${encodeURIComponent("\n\n" + texto)}`;
    if (typeof window.evento === "function") { try { window.evento("reserva_creada", { modalidad: d.modalidad }); } catch (_) { /* la analítica nunca debe romper la reserva */ } }
    res.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // ---- Inicio
  pintarCalendario();
  pintarDuraciones();
  if (cfg.modalidadInicial) $(`[data-modalidad="${cfg.modalidadInicial}"]`).click();
})();
