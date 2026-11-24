/* Club de Billares Guayabal — interacciones del sitio (sin dependencias). */
(function () {
  "use strict";

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
    encabezado.classList.toggle("bg-carbon/80", compacto);
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
  function abrirMenu(abrir) {
    menuAbierto = abrir;
    menu.classList.toggle("abierto", abrir);
    if (!abrir) {
      menu.classList.add("cerrando");
      setTimeout(() => menu.classList.remove("cerrando"), 400);
    }
    menu.setAttribute("aria-hidden", String(!abrir));
    boton.setAttribute("aria-expanded", String(abrir));
    boton.setAttribute("aria-label", abrir ? "Cerrar menú" : "Abrir menú");
    boton.querySelector('[data-icono="menu"]').classList.toggle("oculto", abrir);
    boton.querySelector('[data-icono="cerrar"]').classList.toggle("oculto", !abrir);
    document.body.style.overflow = abrir ? "hidden" : "";
    if (abrir) {
      // barra opaca al instante, sin transición
      encabezado.style.transition = "none";
      encabezado.classList.remove("bg-gradient-to-b", "from-carbon/70", "bg-carbon/80", "backdrop-blur-xl", "border-transparent");
      encabezado.classList.add("bg-carbon", "border-marfil/10");
    } else {
      encabezado.classList.remove("bg-carbon");
      requestAnimationFrame(() => { encabezado.style.transition = ""; });
      actualizarEncabezado();
    }
  }
  boton?.addEventListener("click", () => abrirMenu(!menuAbierto));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && menuAbierto) abrirMenu(false); });
  menu?.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => abrirMenu(false)));

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

  // ---------- Video del evento: se descarga solo al pulsar «play» ----------
  document.querySelectorAll(".video-evento").forEach((caja) => {
    const video = caja.querySelector("video");
    const play = caja.querySelector(".boton-play");
    play.addEventListener("click", () => {
      play.remove();
      video.controls = true;
      video.play();
    });
  });

  // ---------- Galería: filtros y visor ----------
  const galeria = document.getElementById("galeria");
  if (galeria) {
    const items = [...galeria.querySelectorAll("[data-categoria]")];
    document.querySelectorAll("[data-filtro]").forEach((b) => b.addEventListener("click", () => {
      const f = b.dataset.filtro;
      document.querySelectorAll("[data-filtro]").forEach((x) => {
        const activo = x === b;
        x.setAttribute("aria-selected", String(activo));
        x.classList.toggle("bg-oro", activo); x.classList.toggle("text-carbon", activo); x.classList.toggle("border-oro", activo);
        x.classList.toggle("text-marfil/70", !activo); x.classList.toggle("border-marfil/15", !activo);
      });
      items.forEach((it) => it.classList.toggle("oculto", f !== "todas" && it.dataset.categoria !== f));
    }));
    const visor = document.getElementById("visor");
    const visorImg = visor.querySelector("img");
    const visorTxt = visor.querySelector("figcaption");
    let actual = 0;
    const visibles = () => items.filter((x) => !x.classList.contains("oculto"));
    const mostrar = (i) => {
      const lista = visibles();
      actual = (i + lista.length) % lista.length;
      const img = lista[actual].querySelector("img");
      visorImg.src = img.src; visorImg.alt = img.alt; visorTxt.textContent = img.alt;
    };
    const abrir = (i) => { mostrar(i); visor.classList.remove("oculto"); document.body.style.overflow = "hidden"; };
    const cerrar = () => { visor.classList.add("oculto"); document.body.style.overflow = ""; };
    items.forEach((it) => it.querySelector("button").addEventListener("click", () => abrir(visibles().indexOf(it))));
    visor.querySelector("[data-cerrar]").addEventListener("click", cerrar);
    visor.querySelectorAll("[data-mover]").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); mostrar(actual + Number(b.dataset.mover)); }));
    visor.addEventListener("click", (e) => { if (e.target === visor) cerrar(); });
    document.addEventListener("keydown", (e) => {
      if (visor.classList.contains("oculto")) return;
      if (e.key === "Escape") cerrar();
      if (e.key === "ArrowRight") mostrar(actual + 1);
      if (e.key === "ArrowLeft") mostrar(actual - 1);
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
      form.querySelectorAll("[aria-invalid]").forEach((el) => el.removeAttribute("aria-invalid"));
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
        exito.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
      }
      general.textContent = r.error; general.classList.remove("oculto");
      Object.entries(r.campos || {}).forEach(([campo, msg]) => {
        const el = form.querySelector(`[data-error="${campo}"]`);
        const input = form.querySelector(`[name="${campo}"]`);
        if (el) { el.textContent = msg; el.classList.remove("oculto"); }
        if (input) input.setAttribute("aria-invalid", "true");
      });
    });
  });
})();
