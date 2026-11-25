/** Cálculo del valor de una reserva y formatos en español de Colombia. Funciones puras (se prueban con Node). */

/**
 * Valor de la reserva por bloques de 30 minutos.
 * Un bloque que empieza antes de promo.hastaMin (y antes de medianoche) se cobra con la tarifa de la promoción.
 * @param {{tarifaHora:number, inicioMin:number, duracionMin:number, promo?:{valorHora:number, hastaMin:number}|null}} p
 */
export function calcularValor({ tarifaHora, inicioMin, duracionMin, promo = null }) {
  if (!tarifaHora || !duracionMin) return { total: null, minPromo: 0, minNormal: 0 };
  let total = 0, minPromo = 0, minNormal = 0;
  for (let t = inicioMin; t < inicioMin + duracionMin; t += 30) {
    const bloque = Math.min(30, inicioMin + duracionMin - t);
    const conPromo = promo && promo.valorHora < tarifaHora && t < promo.hastaMin;
    if (conPromo) { total += (promo.valorHora * bloque) / 60; minPromo += bloque; }
    else { total += (tarifaHora * bloque) / 60; minNormal += bloque; }
  }
  return { total: Math.round(total), minPromo, minNormal };
}

export function pesos(valor) {
  if (valor == null) return "Por confirmar";
  return "$ " + Math.round(valor).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

/** 570 -> «9:30 a. m.»; 1500 -> «1:00 a. m.» (madrugada del día siguiente). */
export function hora(min) {
  const m = ((min % 1440) + 1440) % 1440;
  const h24 = Math.floor(m / 60), mm = m % 60;
  const h12 = h24 % 12 === 0 ? 12 : h24 % 12;
  return `${h12}:${String(mm).padStart(2, "0")} ${h24 < 12 ? "a. m." : "p. m."}`;
}

/** 90 -> «1 h 30 min», 120 -> «2 horas», 60 -> «1 hora». */
export function duracion(min) {
  const h = Math.floor(min / 60), r = min % 60;
  if (!r) return h === 1 ? "1 hora" : `${h} horas`;
  return h ? `${h} h ${r} min` : `${r} min`;
}

/** «2026-11-25» -> «miércoles 25 de noviembre». */
export function fechaLarga(iso) {
  const [a, m, d] = iso.split("-").map(Number);
  const f = new Date(a, m - 1, d, 12);
  return new Intl.DateTimeFormat("es-CO", { weekday: "long", day: "numeric", month: "long" }).format(f).replace(",", "");
}

export function sumarDias(iso, dias) {
  const [a, m, d] = iso.split("-").map(Number);
  const f = new Date(Date.UTC(a, m - 1, d + dias));
  return f.toISOString().slice(0, 10);
}
