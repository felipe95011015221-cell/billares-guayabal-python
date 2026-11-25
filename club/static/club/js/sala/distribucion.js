/**
 * Distribución conceptual de la sala (en metros, vista desde arriba).
 * x crece hacia la derecha y z hacia el frente. Cuando el club tenga el plano real,
 * basta con cambiar SALA y PUESTOS: la escena 3D y el plano ligero se ajustan solos.
 */
export const SALA = {
  // límites del piso
  xMin: -8.6, xMax: 8.4, zMin: -4.2, zMax: 4.3,
  // separación entre la zona de tres bandas y la de pool
  divisionX: 3.75,
};

// Puestos por modalidad, en el orden de las mesas del panel (orden, id).
export const PUESTOS = {
  carambola: [
    { x: -6.2, z: -1.9 }, { x: -2.3, z: -1.9 }, { x: 1.6, z: -1.9 },
    { x: -4.25, z: 1.95 }, { x: -0.35, z: 1.95 },
  ],
  pool: [
    { x: 6.1, z: -1.9 }, { x: 6.1, z: 1.95 },
  ],
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
    const puesto = lista[i] || { x: SALA.xMin + 2 + extra++ * 3.9, z: SALA.zMax + 1.6 };
    return { ...m, ...puesto };
  });
}

/** Límites de la sala incluyendo mesas fuera de los puestos previstos. */
export function limites(mesas) {
  const b = { ...SALA };
  for (const m of mesas) {
    b.xMin = Math.min(b.xMin, m.x - 2); b.xMax = Math.max(b.xMax, m.x + 2);
    b.zMin = Math.min(b.zMin, m.z - 1.4); b.zMax = Math.max(b.zMax, m.z + 1.4);
  }
  return b;
}
