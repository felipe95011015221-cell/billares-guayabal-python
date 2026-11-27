// Pruebas de la sala interactiva (cálculo de valor, formatos y distribución). Ejecutar: node --test tests_js/
import { test } from "node:test";
import assert from "node:assert/strict";
import { calcularValor, duracion, hora, pesos, sumarDias } from "../club/static/club/js/sala/precios.js";
import { PUESTOS, SALA, huella, ubicarMesas } from "../club/static/club/js/sala/distribucion.js";

const promo = { valorHora: 8000, hastaMin: 15 * 60 };

test("tarifa normal sin promoción", () => {
  assert.equal(calcularValor({ tarifaHora: 15000, inicioMin: 18 * 60, duracionMin: 120, promo }).total, 30000);
  assert.equal(calcularValor({ tarifaHora: 15000, inicioMin: 18 * 60, duracionMin: 90 }).total, 22500);
});

test("promoción de $ 8.000 la hora hasta las 3:00 p. m.", () => {
  assert.equal(calcularValor({ tarifaHora: 15000, inicioMin: 10 * 60, duracionMin: 120, promo }).total, 16000);
  const mixto = calcularValor({ tarifaHora: 15000, inicioMin: 14 * 60, duracionMin: 120, promo });
  assert.deepEqual(mixto, { total: 23000, minPromo: 60, minNormal: 60 });
  const media = calcularValor({ tarifaHora: 15000, inicioMin: 14 * 60 + 30, duracionMin: 60, promo });
  assert.equal(media.total, 4000 + 7500);
});

test("la madrugada no tiene promoción", () => {
  assert.equal(calcularValor({ tarifaHora: 15000, inicioMin: 24 * 60, duracionMin: 60, promo }).total, 15000);
});

test("sin tarifa el valor queda por confirmar", () => {
  assert.equal(calcularValor({ tarifaHora: null, inicioMin: 600, duracionMin: 60, promo }).total, null);
  assert.equal(pesos(null), "Por confirmar");
});

test("formatos en español de Colombia", () => {
  assert.equal(pesos(23000), "$ 23.000");
  assert.equal(pesos(1234567), "$ 1.234.567");
  assert.equal(hora(9 * 60), "9:00 a. m.");
  assert.equal(hora(12 * 60 + 30), "12:30 p. m.");
  assert.equal(hora(25 * 60), "1:00 a. m.");
  assert.equal(duracion(60), "1 hora");
  assert.equal(duracion(90), "1 h 30 min");
  assert.equal(duracion(120), "2 horas");
  assert.equal(sumarDias("2026-12-31", 1), "2027-01-01");
});

test("cada mesa recibe su puesto y las extra no se pierden", () => {
  const mesas = [...Array(5)].map((_, i) => ({ id: i + 1, modalidad: "carambola" }))
    .concat([{ id: 6, modalidad: "pool" }, { id: 7, modalidad: "pool" }, { id: 8, modalidad: "pool" }]);
  const ubicadas = ubicarMesas(mesas);
  const puesto = (m) => ({ x: m.x, z: m.z, y: m.y, rot: m.rot });
  assert.deepEqual(puesto(ubicadas[0]), PUESTOS.carambola[0]);
  assert.deepEqual(puesto(ubicadas[5]), PUESTOS.pool[0]);
  assert.ok(Number.isFinite(ubicadas[7].x) && Number.isFinite(ubicadas[7].z));
  const claves = new Set(ubicadas.map((m) => `${m.x},${m.z}`));
  assert.equal(claves.size, ubicadas.length); // dos mesas nunca comparten puesto
});

test("como el club: una sola fila a lo largo, cada mesa atravesada, 5 de tres bandas y luego 2 de pool", () => {
  const mesas = [...Array(5)].map((_, i) => ({ id: i + 1, modalidad: "carambola" }))
    .concat([{ id: 6, modalidad: "pool" }, { id: 7, modalidad: "pool" }]);
  const u = ubicarMesas(mesas);
  assert.ok(u.every((m) => m.z === 0 && Math.abs(m.rot - Math.PI / 2) < 1e-9));
  for (let i = 1; i < u.length; i++) assert.ok(u[i].x > u[i - 1].x); // en orden, de la 1 a la 7
  assert.ok(u[4].x < SALA.divisionX && u[5].x > SALA.divisionX); // las de pool, después de la división
});

test("las mesas 8 y 9 de pool van en el segundo piso, dentro de su plataforma", () => {
  const mesas = [...Array(5)].map((_, i) => ({ id: i + 1, modalidad: "carambola" }))
    .concat([6, 7, 8, 9].map((id) => ({ id, modalidad: "pool" })));
  const u = ubicarMesas(mesas);
  assert.deepEqual(u.map((m) => m.segundoPiso), [false, false, false, false, false, false, false, true, true]);
  const sp = SALA.segundoPiso;
  for (const m of u.slice(7)) {
    assert.equal(m.y, sp.y);
    const { hx } = huella(m);
    assert.ok(m.x - hx > sp.xMin && m.x + hx < sp.xMax); // la mesa cabe en el segundo piso
  }
  for (const m of u.slice(0, 7)) assert.ok(m.x + huella(m).hx < sp.xMin); // las del primer piso no quedan debajo
});
