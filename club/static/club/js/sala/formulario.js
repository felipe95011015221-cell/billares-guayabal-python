/** Panel de reserva: campos, valor calculado y mensaje de WhatsApp con todo lo elegido. */
import { calcularValor, duracion, fechaLarga, hora, pesos, sumarDias } from "./precios.js";

const MARGEN_HOY_MIN = 15; // para hoy, solo horas que empiecen al menos 15 minutos después de ahora

export function crearFormulario(form, datos, { alCambiarMesa } = {}) {
  const $ = (sel) => form.querySelector(sel);
  const campos = {
    mesa: $("#sala-mesa"), fecha: $("#sala-fecha"), hora: $("#sala-hora"),
    duracion: $("#sala-duracion"), jugadores: $("#sala-jugadores"), nombre: $("#sala-nombre"),
  };
  const ui = {
    titulo: $("[data-sala-titulo]"), subtitulo: $("[data-sala-subtitulo]"), modalidad: $("[data-sala-modalidad]"),
    total: $("[data-sala-total]"), desglose: $("[data-sala-desglose]"), whatsapp: $("[data-sala-whatsapp]"),
    sinHoras: $("[data-sala-sin-horas]"), errorNombre: $("[data-sala-error-nombre]"),
  };
  const mesas = new Map(datos.mesas.map((m) => [String(m.id), m]));
  const cargado = Date.now();
  let elegida = false; // el usuario ya escogió una mesa (en la sala o en la lista)

  // ---------- fecha ----------
  const maxFecha = sumarDias(datos.hoy, datos.diasMax);
  campos.fecha.min = datos.hoy;
  campos.fecha.max = maxFecha;

  const ahoraMin = () => datos.ahoraMin + Math.floor((Date.now() - cargado) / 60000);

  function horasPosibles(fecha, dur) {
    const lista = [];
    const minimo = fecha === datos.hoy ? ahoraMin() + MARGEN_HOY_MIN : -Infinity;
    for (let t = datos.aperturaMin; t + dur <= datos.cierreMin; t += 30) {
      if (t >= minimo) lista.push(t);
    }
    return lista;
  }

  function llenarDuraciones() {
    campos.duracion.innerHTML = datos.duraciones
      .map((d) => `<option value="${d}"${d === 60 ? " selected" : ""}>${duracion(d)}</option>`).join("");
  }

  function llenarHoras() {
    const dur = Number(campos.duracion.value) || 60;
    const anterior = Number(campos.hora.value);
    const lista = horasPosibles(campos.fecha.value, dur);
    ui.sinHoras.hidden = lista.length > 0;
    campos.hora.disabled = !lista.length;
    campos.hora.innerHTML = lista.map((t) => `<option value="${t}">${hora(t)}${t >= 1440 ? " (madrugada)" : ""}</option>`).join("");
    if (!lista.length) return;
    const valor = lista.includes(anterior) ? anterior
      : lista.find((t) => t >= Math.max(anterior || 0, 18 * 60)) ?? lista[0];
    campos.hora.value = String(campos.fecha.value === datos.hoy && !anterior ? lista[0] : valor);
  }

  // Si hoy ya no quedan horarios (o es muy tarde), se propone mañana.
  campos.fecha.value = horasPosibles(datos.hoy, 60).length ? datos.hoy : sumarDias(datos.hoy, 1);
  llenarDuraciones();
  llenarHoras();

  // ---------- reserva actual y mensaje ----------
  function reservaActual() {
    const mesa = mesas.get(campos.mesa.value);
    const inicio = Number(campos.hora.value);
    const dur = Number(campos.duracion.value);
    const valor = mesa ? calcularValor({ tarifaHora: mesa.tarifa, inicioMin: inicio, duracionMin: dur, promo: datos.promo }) : { total: null };
    return {
      mesa, fecha: campos.fecha.value, inicioMin: inicio, duracionMin: dur,
      jugadores: Number(campos.jugadores.value), nombre: campos.nombre.value.trim(), valor,
      valida: Boolean(mesa && campos.fecha.value && !campos.hora.disabled && Number.isFinite(inicio)),
    };
  }

  function mensaje(r) {
    const lineas = [
      datos.mensaje, "",
      `Mesa: ${r.mesa.nombre} (${r.mesa.modalidadNombre.toLowerCase()}${r.mesa.segundoPiso ? ", segundo piso" : ""})`,
      `Fecha: ${fechaLarga(r.fecha)}`,
      `Hora: ${hora(r.inicioMin)} a ${hora(r.inicioMin + r.duracionMin)} (${duracion(r.duracionMin)})`,
      `Jugadores: ${r.jugadores}`,
      `Nombre: ${r.nombre || "—"}`,
      `Valor estimado: ${pesos(r.valor.total)}${r.valor.minPromo ? ` (incluye la promoción hasta las ${hora(datos.promo.hastaMin)})` : ""}`,
      "", "¿Me confirman la disponibilidad?",
    ];
    return lineas.join("\n");
  }

  function actualizar() {
    const r = reservaActual();
    const m = r.mesa;
    ui.titulo.textContent = elegida && m ? m.nombre : "Tu reserva";
    ui.subtitulo.textContent = elegida && m
      ? `${m.modalidadNombre}${m.segundoPiso ? " · Segundo piso" : ""} · ${pesos(m.tarifa)} la hora`
      : "Toca una mesa en la sala o elígela aquí.";
    ui.modalidad.textContent = m ? m.modalidadNombre : "—";
    if (!r.valida) {
      ui.total.textContent = "—";
      ui.desglose.textContent = "";
    } else {
      ui.total.textContent = pesos(r.valor.total);
      const partes = [];
      if (r.valor.minPromo) partes.push(`${duracion(r.valor.minPromo)} con promoción a ${pesos(datos.promo.valorHora)} la hora`);
      if (r.valor.minNormal) partes.push(`${duracion(r.valor.minNormal)} a ${pesos(m.tarifa)} la hora`);
      ui.desglose.textContent = `${partes.join(" + ")}. Se paga en el club.`;
    }
    if (r.valida) ui.whatsapp.href = `https://wa.me/${datos.telefono}?text=${encodeURIComponent(mensaje(r))}`;
    ui.whatsapp.setAttribute("aria-disabled", String(!r.valida));
  }

  // ---------- eventos ----------
  campos.mesa.addEventListener("change", () => { elegida = true; actualizar(); alCambiarMesa?.(campos.mesa.value); });
  campos.fecha.addEventListener("change", () => {
    if (!campos.fecha.value || campos.fecha.value < datos.hoy) campos.fecha.value = datos.hoy;
    if (campos.fecha.value > maxFecha) campos.fecha.value = maxFecha;
    llenarHoras(); actualizar();
  });
  campos.duracion.addEventListener("change", () => { llenarHoras(); actualizar(); });
  for (const c of [campos.hora, campos.jugadores]) c.addEventListener("change", actualizar);
  campos.nombre.addEventListener("input", () => {
    if (campos.nombre.value.trim()) { ui.errorNombre.hidden = true; campos.nombre.removeAttribute("aria-invalid"); }
    actualizar();
  });
  form.addEventListener("submit", (e) => e.preventDefault());

  ui.whatsapp.addEventListener("click", (e) => {
    const r = reservaActual();
    if (!r.valida) { e.preventDefault(); campos.hora.focus(); return; }
    if (!r.nombre) {
      e.preventDefault();
      ui.errorNombre.hidden = false;
      campos.nombre.setAttribute("aria-invalid", "true");
      campos.nombre.focus();
      return;
    }
    actualizar(); // el enlace sale con lo último que escribió
  });

  actualizar();

  return {
    /** Selecciona una mesa desde la sala (no vuelve a avisar a la sala). */
    ponerMesa(id) {
      if (!mesas.has(String(id))) return;
      elegida = true;
      campos.mesa.value = String(id);
      actualizar();
    },
    mesaActual: () => campos.mesa.value,
    reservaActual,
  };
}
