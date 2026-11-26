/**
 * Vista ligera: la misma sala dibujada con HTML y CSS 3D (sin WebGL).
 * Se usa en equipos con poca capacidad gráfica, sin WebGL o si la persona la elige.
 * Misma API que la escena 3D: seleccionar, resaltar, vista, zoom, restablecer, marcarEstados, destruir.
 */
import { MEDIDAS, limites } from "./distribucion.js";

export function crearPlano(marco, mesas, { alSeleccionar, alResaltar } = {}) {
  const b = limites(mesas);
  const ancho = b.xMax - b.xMin, fondo = b.zMax - b.zMin;
  const pct = (v, min, total) => ((v - min) / total) * 100;

  marco.innerHTML = "";
  const escena = document.createElement("div");
  escena.className = "plano";
  escena.style.setProperty("--proporcion", `${ancho} / ${fondo}`);
  const piso = document.createElement("div");
  piso.className = "plano-piso";
  const division = document.createElement("div");
  division.className = "plano-division";
  division.style.left = `${pct(b.divisionX ?? 3.75, b.xMin, ancho)}%`;
  piso.append(division);

  const nodos = new Map();
  for (const m of mesas) {
    const med = MEDIDAS[m.modalidad] || MEDIDAS.carambola;
    const boton = document.createElement("button");
    boton.type = "button";
    boton.tabIndex = -1; // la selección por teclado se hace con las fichas de abajo
    boton.setAttribute("aria-hidden", "true");
    boton.className = `plano-mesa plano-mesa-${m.modalidad}`;
    boton.dataset.mesa = m.id;
    boton.style.left = `${pct(m.x, b.xMin, ancho)}%`;
    boton.style.top = `${pct(m.z, b.zMin, fondo)}%`;
    const girada = Math.abs(Math.sin(m.rot || 0)) > 0.7; // atravesada a lo ancho del salón
    const [enX, enZ] = girada ? [med.ancho, med.largo] : [med.largo, med.ancho];
    boton.style.width = `${((enX + 0.38) / ancho) * 100}%`;
    boton.style.height = `${((enZ + 0.38) / fondo) * 100}%`;
    if (girada) boton.classList.add("plano-mesa-girada");
    boton.innerHTML = `<span class="plano-pano">${
      m.modalidad === "pool"
        ? '<i class="bola b1"></i><i class="bola b2"></i><i class="bola b3"></i><i class="bola b4"></i><i class="bola bb"></i>'
        : '<i class="bola blanca"></i><i class="bola amarilla"></i><i class="bola roja"></i>'
    }</span><b class="plano-numero">${m.numero}</b>`;
    boton.addEventListener("click", () => alSeleccionar?.(String(m.id)));
    boton.addEventListener("pointerenter", () => alResaltar?.(String(m.id)));
    boton.addEventListener("pointerleave", () => alResaltar?.(null));
    piso.append(boton);
    nodos.set(String(m.id), boton);
  }
  escena.append(piso);
  marco.append(escena);
  marco.hidden = false;

  let zoom = 1;
  const aplicarZoom = () => escena.style.setProperty("--zoom", zoom.toFixed(2));

  return {
    tipo: "ligera",
    seleccionar(id) {
      for (const [k, n] of nodos) n.classList.toggle("es-elegida", k === String(id));
    },
    resaltar(id) {
      for (const [k, n] of nodos) n.classList.toggle("es-resaltada", k === String(id));
    },
    vista(nombre) { escena.dataset.vista = nombre; },
    zoom(paso) { zoom = Math.min(1.8, Math.max(0.8, zoom + paso * 0.2)); aplicarZoom(); },
    restablecer() { zoom = 1; aplicarZoom(); escena.dataset.vista = "iso"; },
    marcarEstados(estados) {
      for (const [k, n] of nodos) n.dataset.estado = estados?.get(k) || "";
    },
    destruir() { marco.innerHTML = ""; marco.hidden = true; },
  };
}
