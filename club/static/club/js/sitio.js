/* Club de Billares Guayabal — interacciones del sitio (sin dependencias). */
(function () {
  "use strict";

  // ---------- Analítica: window.evento + clics en [data-evento] ----------
  // Solo envía si existe gtag (Google Analytics configurado); si no, no hace nada.
  window.evento = function (nombre, params) {
    try {
      if (typeof window.gtag === "function") window.gtag("event", nombre, params || {});
    } catch { /* la analítica nunca debe romper la página */ }
  };
  document.addEventListener("click", (e) => {
    const el = e.target instanceof Element ? e.target.closest("[data-evento]") : null;
    if (!el) return;
    const params = {};
    if (el.dataset.eventoOrigen) params.origen = el.dataset.eventoOrigen;
    window.evento(el.dataset.evento, params);
  });

  // ---------- Encabezado: compacto y sólido al desplazar ----------
  const encabezado = document.getElementById("encabezado");
  const barra = document.getElementById("encabezado-barra");
  const logo = document.getElementById("encabezado-logo");
  let menuAbierto = false;
  function actualizarEncabezado() {
    const compacto = window.scrollY > 24;
    barra.classList.toggle("h-16", compacto);
    barra.classList.toggle("h-20", !compacto);
    barra.classList.toggle("lg:h-24", !compacto);
    logo.classList.toggle("h-11", compacto);
    logo.classList.toggle("h-14", !compacto);
    logo.classList.toggle("lg:h-16", !compacto);
    if (menuAbierto) return; // con el menú abierto la barra queda opaca y fija
    encabezado.classList.toggle("bg-carbon/85", compacto);
    encabezado.classList.toggle("backdrop-blur-xl", compacto);
    encabezado.classList.toggle("border-marfil/10", compacto);
    encabezado.classList.toggle("bg-gradient-to-b", !compacto);
    encabezado.classList.toggle("from-carbon/70", !compacto);
    encabezado.classList.toggle("border-transparent", !compacto);
  }
  window.addEventListener("scroll", actualizarEncabezado, { passive: true });
  actualizarEncabezado();

  // ---------- Menú móvil: cortina opaca (nunca transparente) ----------
  const boton = document.getElementById("boton-menu");
  const menu = document.getElementById("menu-movil");
  const contenido = document.getElementById("contenido");
  function abrirMenu(abrir, devolverFoco) {
    menuAbierto = abrir;
    menu.classList.toggle("abierto", abrir);
    if (!abrir) {
      menu.classList.add("cerrando");
      setTimeout(() => menu.classList.remove("cerrando"), 400);
    }
    menu.setAttribute("aria-hidden", String(!abrir));
    if ("inert" in menu) menu.inert = !abrir;
    if (contenido && "inert" in contenido) contenido.inert = abrir;
    boton.setAttribute("aria-expanded", String(abrir));
    boton.setAttribute("aria-label", abrir ? "Cerrar menú" : "Abrir menú");
    boton.querySelector('[data-icono="menu"]').classList.toggle("oculto", abrir);
    boton.querySelector('[data-icono="cerrar"]').classList.toggle("oculto", !abrir);
    document.body.style.overflow = abrir ? "hidden" : "";
    if (abrir) {
      // barra opaca al instante, sin transición
      encabezado.style.transition = "none";
      encabezado.classList.remove("bg-gradient-to-b", "from-carbon/70", "bg-carbon/85", "backdrop-blur-xl", "border-transparent");
      encabezado.classList.add("bg-carbon", "border-marfil/10");
      const primero = menu.querySelector("a");
      if (primero) setTimeout(() => primero.focus({ preventScroll: true }), 60);
    } else {
      encabezado.classList.remove("bg-carbon");
      requestAnimationFrame(() => { encabezado.style.transition = ""; });
      actualizarEncabezado();
      if (devolverFoco) boton.focus();
    }
  }
  if (menu && boton) {
    if ("inert" in menu) menu.inert = true;
    boton.addEventListener("click", () => abrirMenu(!menuAbierto, true));
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && menuAbierto) abrirMenu(false, true); });
    menu.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => abrirMenu(false, false)));
    // si la ventana crece hasta mostrar la navegación de escritorio, se cierra el menú
    window.matchMedia("(min-width: 1280px)").addEventListener("change", (m) => { if (m.matches && menuAbierto) abrirMenu(false, false); });
  }

  // ---------- Aparición al desplazar ----------
  const reducir = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const revelar = document.querySelectorAll(".revelar");
  if (reducir || !("IntersectionObserver" in window)) {
    revelar.forEach((el) => el.classList.add("visible"));
  } else {
    const obs = new IntersectionObserver((entradas) => {
      entradas.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("visible"); obs.unobserve(e.target); } });
    }, { rootMargin: "0px 0px -60px 0px" });
    revelar.forEach((el) => obs.observe(el));
  }

  // ---------- Resumen desplegable: abierto en escritorio, cerrado en móvil ----------
  document.querySelectorAll("details[data-abierto-lg]").forEach((d) => {
    const mq = window.matchMedia("(min-width: 1024px)");
    const ajustar = () => { d.open = mq.matches; };
    ajustar();
    mq.addEventListener("change", ajustar);
  });

  // ---------- Video del evento: se descarga solo al pulsar «play» ----------
  document.querySelectorAll(".video-evento").forEach((caja) => {
    const video = caja.querySelector("video");
    const play = caja.querySelector(".boton-play");
    if (!video || !play) return;
    play.addEventListener("click", () => {
      play.remove();
      video.controls = true;
      video.focus({ preventScroll: true });
      video.play();
      window.evento("video_play", { origen: "evento_club" });
    });
  });

  // ---------- Galería: filtros (botones con aria-pressed) y visor ----------
  const galeria = document.getElementById("galeria");
  if (galeria) {
    const items = [...galeria.querySelectorAll("[data-categoria]")];
    const filtros = [...document.querySelectorAll("[data-filtro]")];
    const estado = document.getElementById("galeria-estado");
    const visibles = () => items.filter((x) => !x.classList.contains("oculto"));
    filtros.forEach((b) => b.addEventListener("click", () => {
      const f = b.dataset.filtro;
      filtros.forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      items.forEach((it) => it.classList.toggle("oculto", f !== "todas" && it.dataset.categoria !== f));
      if (estado) estado.textContent = `Mostrando ${visibles().length} de ${items.length} fotos`;
    }));

    const visor = document.getElementById("visor");
    const visorImg = visor.querySelector("img");
    const visorTxt = visor.querySelector("figcaption");
    const btnCerrar = visor.querySelector("[data-cerrar]");
    let actual = 0;
    let origen = null;
    const mostrar = (i) => {
      const lista = visibles();
      if (!lista.length) return;
      actual = (i + lista.length) % lista.length;
      const img = lista[actual].querySelector("img");
      visorImg.src = img.currentSrc || img.src; visorImg.alt = img.alt; visorTxt.textContent = img.alt;
    };
    const abrir = (i, desde) => {
      origen = desde;
      mostrar(i);
      visor.classList.remove("oculto");
      document.body.style.overflow = "hidden";
      btnCerrar.focus();
    };
    const cerrar = () => {
      visor.classList.add("oculto");
      document.body.style.overflow = "";
      if (origen) origen.focus();
    };
    items.forEach((it) => { const b = it.querySelector("button"); b.addEventListener("click", () => abrir(visibles().indexOf(it), b)); });
    btnCerrar.addEventListener("click", cerrar);
    visor.querySelectorAll("[data-mover]").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); mostrar(actual + Number(b.dataset.mover)); }));
    visor.addEventListener("click", (e) => { if (e.target === visor) cerrar(); });
    document.addEventListener("keydown", (e) => {
      if (visor.classList.contains("oculto")) return;
      if (e.key === "Escape") cerrar();
      else if (e.key === "ArrowRight") mostrar(actual + 1);
      else if (e.key === "ArrowLeft") mostrar(actual - 1);
      else if (e.key === "Tab") {
        // el foco se queda dentro del visor mientras está abierto
        const foco = [...visor.querySelectorAll("button")];
        const primero = foco[0], ultimo = foco[foco.length - 1];
        if (e.shiftKey && document.activeElement === primero) { e.preventDefault(); ultimo.focus(); }
        else if (!e.shiftKey && document.activeElement === ultimo) { e.preventDefault(); primero.focus(); }
      }
    });
  }

  // ---------- Formularios que envían JSON a las APIs ----------
  window.csrf = () => (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || "";
  window.enviarJson = async (url, cuerpo) => {
    try {
      const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": window.csrf() }, body: JSON.stringify(cuerpo) });
      return await r.json();
    } catch {
      return { ok: false, error: "Sin conexión. Revisa tu internet e intenta de nuevo." };
    }
  };
  document.querySelectorAll("form[data-api]").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      form.querySelectorAll("[data-error]").forEach((el) => { el.textContent = ""; el.classList.add("oculto"); });
      form.querySelectorAll("[aria-invalid]").forEach((el) => { el.removeAttribute("aria-invalid"); el.removeAttribute("aria-describedby"); });
      const datos = {};
      new FormData(form).forEach((v, k) => { datos[k] = v; });
      form.querySelectorAll('input[type="checkbox"]').forEach((c) => { datos[c.name] = c.checked; });
      const enviar = form.querySelector('[type="submit"]');
      const texto = enviar.textContent;
      enviar.disabled = true; enviar.textContent = "Enviando…";
      const r = await window.enviarJson(form.dataset.api, datos);
      enviar.disabled = false; enviar.textContent = texto;
      const general = form.querySelector("[data-error-general]");
      if (r.ok) {
        const exito = document.getElementById(form.dataset.exito);
        const codigo = exito.querySelector("[data-codigo]");
        if (codigo && r.data.codigo) codigo.textContent = r.data.codigo;
        form.classList.add("oculto"); exito.classList.remove("oculto");
        exito.setAttribute("tabindex", "-1");
        exito.scrollIntoView({ behavior: reducir ? "auto" : "smooth", block: "center" });
        exito.focus({ preventScroll: true });
        window.evento("generate_lead", { formulario: form.dataset.exito });
        return;
      }
      if (general) { general.textContent = r.error; general.classList.remove("oculto"); general.setAttribute("role", "alert"); }
      let primero = null;
      Object.entries(r.campos || {}).forEach(([campo, msg]) => {
        const el = form.querySelector(`[data-error="${campo}"]`);
        const input = form.querySelector(`[name="${campo}"]`);
        if (el) {
          el.textContent = msg; el.classList.remove("oculto");
          if (!el.id) el.id = `error-${form.dataset.exito}-${campo}`;
        }
        if (input) {
          input.setAttribute("aria-invalid", "true");
          if (el) input.setAttribute("aria-describedby", el.id);
          if (!primero) primero = input;
        }
      });
      if (primero) primero.focus(); else if (general) general.scrollIntoView({ block: "center", behavior: reducir ? "auto" : "smooth" });
    });
  });
})();
