/**
 * Sala interactiva de reservas: une la vista (3D o ligera), las fichas de mesa y el panel de reserva.
 * La escena 3D (Three.js) se descarga solo cuando la sala se acerca a la pantalla.
 */
import { ubicarMesas } from "./distribucion.js";
import { crearFormulario } from "./formulario.js";
import { crearPlano } from "./plano.js";
import { consultarDisponibilidad } from "./disponibilidad.js";
import { pesos } from "./precios.js";

const raiz = document.querySelector("[data-sala]");
const fuente = document.getElementById("sala-datos");

if (raiz && fuente) iniciar(JSON.parse(fuente.textContent));

function leerPreferencia() {
  try { return localStorage.getItem("sala-vista"); } catch { return null; }
}
function guardarPreferencia(valor) {
  try { localStorage.setItem("sala-vista", valor); } catch { /* sin almacenamiento: no pasa nada */ }
}

/** ¿El equipo aguanta la escena 3D? Si no, se usa la vista ligera. */
function equipoLimitado() {
  const nav = navigator;
  if (nav.connection?.saveData) return true;
  if (nav.deviceMemory && nav.deviceMemory < 4) return true;
  if (nav.hardwareConcurrency && nav.hardwareConcurrency <= 2) return true;
  return false;
}

function iniciar(datos) {
  raiz.hidden = false;
  const mesas = ubicarMesas(datos.mesas);
  const porId = new Map(mesas.map((m) => [String(m.id), m]));
  const escenario = raiz.querySelector("[data-sala-escenario]");
  const lienzo = raiz.querySelector("[data-sala-lienzo]");
  const marcoPlano = raiz.querySelector("[data-sala-plano]");
  const carga = raiz.querySelector("[data-sala-carga]");
  const etiqueta = raiz.querySelector("[data-sala-etiqueta]");
  const barra = raiz.querySelector("[data-sala-barra]");
  const barraTexto = raiz.querySelector("[data-sala-barra-texto]");
  const botonModo = raiz.querySelector("[data-sala-modo]");
  const ayuda = raiz.querySelector("[data-sala-ayuda]");
  const fichas = [...raiz.querySelectorAll(".sala-ficha")];
  const botonesVista = [...raiz.querySelectorAll("[data-vista]")];
  const reducido = matchMedia("(prefers-reduced-motion: reduce)").matches;

  let vista = null; // escena 3D o plano ligero (misma API)
  let elegida = null;

  const formulario = crearFormulario(raiz.querySelector("[data-sala-form]"), datos, {
    alCambiarMesa: (id) => elegir(id, { desde: "formulario" }),
  });

  function elegir(id, { desde = "sala" } = {}) {
    id = String(id);
    if (!porId.has(id)) return;
    elegida = id;
    for (const f of fichas) f.setAttribute("aria-pressed", String(f.dataset.mesa === id));
    vista?.seleccionar(id, { enfocar: true });
    if (desde !== "formulario") formulario.ponerMesa(id);
    const m = porId.get(id);
    barraTexto.innerHTML = `<b>${m.nombre}</b> ${m.modalidad === "pool" ? "Pool" : "Tres bandas"} · ${pesos(m.tarifa)} la hora`;
    barra.hidden = false;
    escenario.classList.add("hay-eleccion");
  }

  function resaltar(id, punto) {
    for (const f of fichas) f.classList.toggle("es-resaltada", f.dataset.mesa === String(id));
    const m = id ? porId.get(String(id)) : null;
    if (!m || !punto) { etiqueta.hidden = true; return; }
    etiqueta.innerHTML = `<b>${m.nombre}</b><span>${m.modalidadNombre}</span><span>${pesos(m.tarifa)} la hora</span>`;
    etiqueta.style.transform = `translate(${Math.round(punto.x + 16)}px, ${Math.round(punto.y + 16)}px)`;
    etiqueta.hidden = false;
  }

  const callbacks = {
    alSeleccionar: (id) => elegir(id),
    alResaltar: resaltar,
    alFallar: () => usarLigera({ recordar: false }),
    reducido,
  };

  function marcarVista(nombre) {
    for (const b of botonesVista) b.setAttribute("aria-pressed", String(b.dataset.vista === nombre));
  }

  function despuesDeMontar() {
    if (elegida) vista.seleccionar(elegida, { enfocar: false });
    marcarVista("iso");
    escenario.dataset.modo = vista.tipo;
    botonModo.hidden = false;
    botonModo.textContent = vista.tipo === "3d" ? "Usar vista ligera" : "Ver la sala en 3D";
    ayuda.textContent = vista.tipo === "3d"
      ? (matchMedia("(pointer: coarse)").matches
        ? "Desliza de lado para girar · pellizca para acercar"
        : "Arrastra para girar · Ctrl + rueda para acercar · clic en una mesa")
      : "Toca una mesa para elegirla";
    carga.hidden = true;
    // Disponibilidad en tiempo real: hoy devuelve null y no se marca nada.
    consultarDisponibilidad({}).then((estados) => { if (estados) vista.marcarEstados(estados); });
  }

  function usarLigera({ recordar = true } = {}) {
    vista?.destruir();
    if (recordar) guardarPreferencia("ligera");
    vista = crearPlano(marcoPlano, mesas, callbacks);
    despuesDeMontar();
  }

  async function usar3D({ recordar = true } = {}) {
    carga.hidden = false;
    try {
      const { crearEscena, soportaWebGL } = await import("./escena3d.js");
      if (!soportaWebGL()) throw new Error("sin WebGL");
      vista?.destruir();
      if (recordar) guardarPreferencia("3d");
      const coarse = matchMedia("(pointer: coarse)").matches;
      vista = crearEscena(lienzo, mesas, { ...callbacks, calidad: coarse || innerWidth < 900 ? "media" : "alta" });
      despuesDeMontar();
    } catch (error) {
      console.warn("Sala 3D no disponible; se usa la vista ligera.", error);
      usarLigera({ recordar: false });
    }
  }

  // ---------- controles ----------
  for (const f of fichas) {
    f.addEventListener("click", () => elegir(f.dataset.mesa, { desde: "ficha" }));
    f.addEventListener("pointerenter", () => vista?.resaltar(f.dataset.mesa));
    f.addEventListener("pointerleave", () => vista?.resaltar(null));
    f.addEventListener("focus", () => vista?.resaltar(f.dataset.mesa));
    f.addEventListener("blur", () => vista?.resaltar(null));
  }
  for (const b of botonesVista) b.addEventListener("click", () => { vista?.vista(b.dataset.vista); marcarVista(b.dataset.vista); });
  raiz.querySelectorAll("[data-zoom]").forEach((b) => b.addEventListener("click", () => vista?.zoom(Number(b.dataset.zoom))));
  raiz.querySelector("[data-restablecer]").addEventListener("click", () => { vista?.restablecer(); marcarVista("iso"); });
  botonModo.addEventListener("click", () => (vista?.tipo === "3d" ? usarLigera() : usar3D()));
  barra.querySelector("a").addEventListener("click", (e) => {
    e.preventDefault();
    const panel = document.getElementById("sala-panel");
    panel.scrollIntoView({ behavior: reducido ? "auto" : "smooth", block: "start" });
    setTimeout(() => panel.querySelector("#sala-fecha")?.focus({ preventScroll: true }), reducido ? 0 : 450);
  });

  // ?mesa=3 en la dirección preselecciona esa mesa (por número o id)
  const pedida = new URLSearchParams(location.search).get("mesa");
  if (pedida) {
    const m = mesas.find((x) => String(x.numero) === pedida || String(x.id) === pedida);
    if (m) elegir(m.id, { desde: "url" });
  }

  // ---------- arranque perezoso ----------
  const preferencia = leerPreferencia();
  const quiere3D = preferencia === "3d" || (preferencia !== "ligera" && !equipoLimitado());
  if (!quiere3D) { usarLigera({ recordar: false }); return; }
  const observador = new IntersectionObserver((entradas) => {
    if (entradas.some((e) => e.isIntersecting)) {
      observador.disconnect();
      usar3D({ recordar: false });
    }
  }, { rootMargin: "400px 0px" });
  observador.observe(escenario);
}
