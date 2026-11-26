/**
 * Distribución conceptual de la sala (en metros, vista desde arriba).
 * x crece hacia la derecha y z hacia el frente. Cuando el club tenga el plano real,
 * basta con cambiar SALA y PUESTOS: la escena 3D y el plano ligero se ajustan solos.
 */
export const SALA = {
  // Salón largo y angosto, como el club: las mesas van en una sola fila a lo largo (eje x).
  xMin: -11.6, xMax: 11.8, zMin: -3.3, zMax: 3.3,
  // separación entre la zona de tres bandas y la de pool
  divisionX: 5.05,
};

// Cada mesa atravesada a lo ancho del salón (rot = 90°): primero las 5 de tres bandas y al fondo las 2 de pool.
const A_LO_ANCHO = Math.PI / 2;
const PASO = 3.25; // de centro a centro entre mesas
export const PUESTOS = {
  carambola: [0, 1, 2, 3, 4].map((i) => ({ x: -9.75 + i * PASO, z: 0, rot: A_LO_ANCHO })),
  pool: [0, 1].map((i) => ({ x: 6.75 + i * PASO, z: 0, rot: A_LO_ANCHO })),
};

// Medidas de cada tipo de mesa (área de juego en metros).
export const MEDIDAS = {
  carambola: { largo: 2.84, ancho: 1.42 },
  pool: { largo: 2.54, ancho: 1.27 },
};

/** Asigna un puesto a cada mesa. Las que no tienen puesto definido se ubican en una fila extra al frente. */
export function ubicarMesas(mesas) {
  const usados = { carambola: 0, pool: 0 };
  let extra = 0;
  return mesas.map((m) => {
    const lista = PUESTOS[m.modalidad] || [];
    const i = usados[m.modalidad] ?? 0;
    usados[m.modalidad] = i + 1;
    const puesto = lista[i] || { x: SALA.xMin + 2 + extra++ * 3.9, z: SALA.zMax + 1.6, rot: 0 };
    return { rot: 0, ...m, ...puesto };
  });
}

/** Medio largo y medio ancho que ocupa una mesa en planta, según su giro. */
export function huella(m, margen = 0) {
  const med = MEDIDAS[m.modalidad] || MEDIDAS.carambola;
  const l = (med.largo + 0.4) / 2 + margen, a = (med.ancho + 0.4) / 2 + margen;
  const c = Math.abs(Math.cos(m.rot || 0)), s = Math.abs(Math.sin(m.rot || 0));
  return { hx: c * l + s * a, hz: s * l + c * a };
}

/** Límites de la sala incluyendo mesas fuera de los puestos previstos. */
export function limites(mesas) {
  const b = { ...SALA };
  for (const m of mesas) {
    const { hx, hz } = huella(m, 0.4);
    b.xMin = Math.min(b.xMin, m.x - hx); b.xMax = Math.max(b.xMax, m.x + hx);
    b.zMin = Math.min(b.zMin, m.z - hz); b.zMax = Math.max(b.zMax, m.z + hz);
  }
  return b;
}
