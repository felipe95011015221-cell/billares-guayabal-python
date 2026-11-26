/**
 * Texturas generadas en el navegador con <canvas> (madera, paño, piso, pared, letreros, números).
 * No se descargan imágenes: la sala completa pesa lo mismo que el código.
 */
import * as THREE from "../../vendor/three/three.module.min.js";

function lienzo(ancho, alto) {
  const c = document.createElement("canvas");
  c.width = ancho; c.height = alto;
  return [c, c.getContext("2d")];
}

// Ruido determinista para que la sala se vea igual en cada visita.
function aleatorio(semilla = 7) {
  let s = semilla;
  return () => ((s = (s * 16807) % 2147483647) - 1) / 2147483646;
}

function textura(canvas, { repetir = [1, 1], color = true, anisotropia = 4 } = {}) {
  const t = new THREE.CanvasTexture(canvas);
  if (color) t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(...repetir);
  t.anisotropy = anisotropia;
  return t;
}

/** Madera oscura con vetas (caoba / nogal). */
export function madera({ base = "#4a2015", oscuro = "#2a0f08", claro = "#6b3420", semilla = 3 } = {}) {
  const [c, g] = lienzo(512, 256);
  const r = aleatorio(semilla);
  g.fillStyle = base; g.fillRect(0, 0, 512, 256);
  for (let i = 0; i < 140; i++) {
    const y = r() * 256, h = 0.6 + r() * 2.4;
    g.strokeStyle = r() > 0.5 ? oscuro : claro;
    g.globalAlpha = 0.12 + r() * 0.3;
    g.lineWidth = h;
    g.beginPath();
    g.moveTo(0, y);
    for (let x = 0; x <= 512; x += 32) g.lineTo(x, y + Math.sin(x / (40 + r() * 60) + i) * (2 + r() * 4));
    g.stroke();
  }
  g.globalAlpha = 1;
  return textura(c);
}

/** Paño de billar: color uniforme con fibras finas. */
export function pano(color) {
  const [c, g] = lienzo(256, 256);
  const r = aleatorio(11);
  g.fillStyle = color; g.fillRect(0, 0, 256, 256);
  const img = g.getImageData(0, 0, 256, 256);
  for (let i = 0; i < img.data.length; i += 4) {
    const n = (r() - 0.5) * 22;
    img.data[i] += n; img.data[i + 1] += n; img.data[i + 2] += n;
  }
  g.putImageData(img, 0, 0);
  return textura(c, { repetir: [3, 2] });
}

/** Piso de tablones oscuros. */
export function piso() {
  const [c, g] = lienzo(1024, 1024);
  const r = aleatorio(5);
  const filas = 8, alto = 1024 / filas;
  for (let f = 0; f < filas; f++) {
    let x = -r() * 300;
    while (x < 1024) {
      const largo = 280 + r() * 260;
      const tono = 22 + Math.floor(r() * 14);
      g.fillStyle = `rgb(${tono + 14}, ${tono + 6}, ${tono})`;
      g.fillRect(x, f * alto, largo, alto);
      for (let v = 0; v < 10; v++) {
        g.strokeStyle = `rgba(0,0,0,${0.08 + r() * 0.12})`;
        g.lineWidth = 1 + r() * 2;
        const y = f * alto + r() * alto;
        g.beginPath(); g.moveTo(x, y); g.lineTo(x + largo, y + (r() - 0.5) * 6); g.stroke();
      }
      g.fillStyle = "rgba(0,0,0,0.55)";
      g.fillRect(x, f * alto, 2, alto);
      x += largo;
    }
    g.fillStyle = "rgba(0,0,0,0.6)";
    g.fillRect(0, f * alto, 1024, 2);
  }
  return textura(c, { repetir: [3, 1.6], anisotropia: 8 });
}

/** Alfombra de zona: tejido oscuro con borde. */
export function alfombra(color, borde) {
  const [c, g] = lienzo(512, 512);
  const r = aleatorio(17);
  g.fillStyle = color; g.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 9000; i++) {
    g.fillStyle = `rgba(255,255,255,${r() * 0.035})`;
    g.fillRect(r() * 512, r() * 512, 1.5, 1.5);
  }
  g.strokeStyle = borde; g.lineWidth = 10; g.strokeRect(16, 16, 480, 480);
  g.lineWidth = 2; g.strokeRect(34, 34, 444, 444);
  return textura(c, { repetir: [1, 1] });
}

/** Pared: paneles azul noche con zócalo de madera y filete dorado. */
export function pared() {
  const [c, g] = lienzo(1024, 256);
  const fondo = g.createLinearGradient(0, 0, 0, 256);
  fondo.addColorStop(0, "#0b1a33"); fondo.addColorStop(0.62, "#12284a"); fondo.addColorStop(0.62, "#c9a227");
  fondo.addColorStop(0.635, "#c9a227"); fondo.addColorStop(0.635, "#2b130b"); fondo.addColorStop(1, "#1d0c06");
  g.fillStyle = fondo; g.fillRect(0, 0, 1024, 256);
  g.strokeStyle = "rgba(0,0,0,0.35)"; g.lineWidth = 3;
  for (let x = 0; x < 1024; x += 128) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, 158); g.stroke(); }
  g.strokeStyle = "rgba(255,255,255,0.05)"; g.lineWidth = 1;
  for (let x = 2; x < 1024; x += 128) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, 158); g.stroke(); }
  return textura(c, { repetir: [4, 1] });
}

/** Letrero luminoso para la pared (texto dorado sobre transparente). */
export function letrero(texto, { tam = 150, color = "#f2c230", ancho = 1024 } = {}) {
  const [c, g] = lienzo(ancho, 256);
  g.font = `700 ${tam}px "Bricolage Grotesque", "Arial Narrow", system-ui, sans-serif`;
  g.textAlign = "center"; g.textBaseline = "middle";
  g.shadowColor = color; g.shadowBlur = 28;
  g.fillStyle = color;
  g.fillText(texto, ancho / 2, 132);
  g.shadowBlur = 0;
  g.fillStyle = "#fff5cf";
  g.globalAlpha = 0.55;
  g.fillText(texto, ancho / 2, 132);
  return textura(c, { repetir: [1, 1] });
}

/** Disco con el número de la mesa (normal y elegido). */
export function numero(n, elegido = false) {
  const [c, g] = lienzo(128, 128);
  g.beginPath(); g.arc(64, 64, 54, 0, Math.PI * 2);
  g.fillStyle = elegido ? "#f2c230" : "rgba(10,27,52,0.92)"; g.fill();
  g.lineWidth = 6; g.strokeStyle = elegido ? "#fff1b8" : "rgba(242,194,48,0.85)"; g.stroke();
  g.fillStyle = elegido ? "#0a1b34" : "#f3f5f0";
  g.font = '700 64px "Bricolage Grotesque", "Arial Narrow", system-ui, sans-serif';
  g.textAlign = "center"; g.textBaseline = "middle";
  g.fillText(String(n), 64, 69);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

/** Halo rectangular suave (para el resplandor bajo la mesa y la sombra de contacto). */
export function halo({ color = "255,255,255", fuerza = 1 } = {}) {
  const [c, g] = lienzo(256, 256);
  const grad = g.createRadialGradient(128, 128, 20, 128, 128, 128);
  grad.addColorStop(0, `rgba(${color},${fuerza})`);
  grad.addColorStop(0.55, `rgba(${color},${fuerza * 0.55})`);
  grad.addColorStop(1, `rgba(${color},0)`);
  g.fillStyle = grad; g.fillRect(0, 0, 256, 256);
  const t = new THREE.CanvasTexture(c);
  return t;
}

/** Bola de pool rayada: banda de color sobre blanco. */
export function bolaRayada(color) {
  const [c, g] = lienzo(128, 64);
  g.fillStyle = "#f7f5ec"; g.fillRect(0, 0, 128, 64);
  g.fillStyle = color; g.fillRect(0, 19, 128, 26);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
