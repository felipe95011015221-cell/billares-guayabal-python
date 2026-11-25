/**
 * Sala 3D del club con Three.js (WebGL).
 * Cada mesa es un objeto independiente, numerado y seleccionable, con su propia lámpara y luz.
 * Se dibuja solo cuando algo cambia (cámara, animación o cursor) y se pausa fuera de pantalla.
 */
import * as THREE from "../../vendor/three/three.module.min.js";
import { OrbitControls } from "../../vendor/three/OrbitControls.js";
import { RoundedBoxGeometry } from "../../vendor/three/RoundedBoxGeometry.js";
import { RoomEnvironment } from "../../vendor/three/RoomEnvironment.js";
import * as tx from "./texturas.js";
import { MEDIDAS, limites } from "./distribucion.js";

const ORO = new THREE.Color("#f2c230");
const LUZ_CALIDA = new THREE.Color("#ffd9a0");
const ALTO_PANO = 0.79; // altura del paño
const R_BOLA = 0.045; // radio visual (un poco mayor que el real para que se lea desde lejos)

export function soportaWebGL() {
  try {
    const c = document.createElement("canvas");
    return Boolean(window.WebGL2RenderingContext && c.getContext("webgl2")) || Boolean(c.getContext("webgl"));
  } catch {
    return false;
  }
}

const suavizar = (actual, meta, dt, velocidad = 9) => actual + (meta - actual) * (1 - Math.exp(-velocidad * dt));
const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

export function crearEscena(contenedor, mesasDatos, opciones = {}) {
  const { alSeleccionar, alResaltar, alFallar, reducido = false, calidad = "alta" } = opciones;
  const alta = calidad === "alta";
  const b = limites(mesasDatos);
  const centro = new THREE.Vector3((b.xMin + b.xMax) / 2, 0.3, (b.zMin + b.zMax) / 2);

  // ---------- renderizador ----------
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, alta ? 2 : 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = alta;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.setClearColor(0x000000, 0);
  const lienzo = renderer.domElement;
  lienzo.setAttribute("aria-hidden", "true");
  contenedor.append(lienzo);

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.22;
  pmrem.dispose();

  const camera = new THREE.PerspectiveCamera(30, 1, 0.3, 140);

  // ---------- materiales compartidos ----------
  const M = {
    madera: new THREE.MeshPhysicalMaterial({ map: tx.madera(), roughness: 0.4, clearcoat: 0.8, clearcoatRoughness: 0.22 }),
    maderaClara: new THREE.MeshPhysicalMaterial({ map: tx.madera({ base: "#5a2a18", claro: "#7a4026", semilla: 9 }), roughness: 0.35, clearcoat: 0.9, clearcoatRoughness: 0.18 }),
    panoAzul: new THREE.MeshStandardMaterial({ map: tx.pano("#1e5fc0"), roughness: 0.94 }),
    bandaAzul: new THREE.MeshStandardMaterial({ map: tx.pano("#18509f"), roughness: 0.9 }),
    panoVerde: new THREE.MeshStandardMaterial({ map: tx.pano("#0e7a4b"), roughness: 0.94 }),
    bandaVerde: new THREE.MeshStandardMaterial({ map: tx.pano("#0b623c"), roughness: 0.9 }),
    laton: new THREE.MeshStandardMaterial({ color: "#d4a83a", metalness: 1, roughness: 0.28 }),
    cromo: new THREE.MeshStandardMaterial({ color: "#dfe4ea", metalness: 1, roughness: 0.16 }),
    nacar: new THREE.MeshStandardMaterial({ color: "#f4efe2", roughness: 0.3 }),
    tronera: new THREE.MeshBasicMaterial({ color: "#050505" }),
    pantalla: new THREE.MeshStandardMaterial({ color: "#0b6b4b", metalness: 0.55, roughness: 0.32 }),
    cable: new THREE.MeshStandardMaterial({ color: "#151515", roughness: 0.6 }),
    oscuro: new THREE.MeshStandardMaterial({ color: "#0d0a08", roughness: 0.9 }),
    cuero: new THREE.MeshStandardMaterial({ color: "#14284a", roughness: 0.55 }),
  };
  const bolaMat = (color) => new THREE.MeshPhysicalMaterial({ color, roughness: 0.14, clearcoat: 1, clearcoatRoughness: 0.05 });
  const geoBola = new THREE.SphereGeometry(R_BOLA, alta ? 24 : 16, alta ? 16 : 12);
  const texHalo = tx.halo();
  const texSombra = tx.halo({ color: "0,0,0", fuerza: 0.9 });

  // ---------- sala: piso, alfombras, paredes ----------
  const anchoSala = b.xMax - b.xMin, fondoSala = b.zMax - b.zMin;
  const matPiso = new THREE.MeshStandardMaterial({ map: tx.piso(), roughness: 0.5 });
  matPiso.map.repeat.set(anchoSala / 5.5, fondoSala / 5.5);
  const losa = new THREE.Mesh(new THREE.BoxGeometry(anchoSala, 0.3, fondoSala),
    [M.oscuro, M.oscuro, matPiso, M.oscuro, M.oscuro, M.oscuro]);
  losa.position.set(centro.x, -0.15, centro.z);
  losa.receiveShadow = true;
  scene.add(losa);

  const alfombra = (x0, x1, color, borde) => {
    const a = new THREE.Mesh(new THREE.PlaneGeometry(x1 - x0, fondoSala - 1.2),
      new THREE.MeshStandardMaterial({ map: tx.alfombra(color, borde), roughness: 1 }));
    a.rotation.x = -Math.PI / 2;
    a.position.set((x0 + x1) / 2, 0.004, centro.z + 0.2);
    a.receiveShadow = true;
    scene.add(a);
  };
  const division = b.divisionX ?? 3.75;
  alfombra(b.xMin + 0.5, division - 0.35, "#0d1d3a", "rgba(201,162,39,0.35)");
  alfombra(division + 0.35, b.xMax - 0.4, "#0a2a21", "rgba(201,162,39,0.35)");

  const ALTO_PARED = 3.3;
  const texPared = tx.pared();
  const pared = (largo, x, z, rotY) => {
    const t = texPared.clone();
    t.needsUpdate = true;
    t.repeat.set(largo / 4.2, 1);
    const m = new THREE.Mesh(new THREE.BoxGeometry(largo, ALTO_PARED, 0.16),
      [M.oscuro, M.oscuro, M.oscuro, M.oscuro, new THREE.MeshStandardMaterial({ map: t, roughness: 0.7 }), M.oscuro]);
    m.position.set(x, ALTO_PARED / 2, z);
    m.rotation.y = rotY;
    m.receiveShadow = true;
    scene.add(m);
  };
  pared(anchoSala + 0.16, centro.x + 0.08, b.zMin - 0.08, 0);
  pared(fondoSala, b.xMin - 0.08, centro.z, Math.PI / 2);

  const letrero = (texto, x, y, z, rotY, ancho, tam) => {
    const mat = new THREE.MeshBasicMaterial({ map: tx.letrero(texto, { tam }), transparent: true, toneMapped: false, depthWrite: false });
    const p = new THREE.Mesh(new THREE.PlaneGeometry(ancho, ancho / 4), mat);
    p.position.set(x, y, z);
    p.rotation.y = rotY;
    scene.add(p);
  };
  letrero("Tres bandas", (b.xMin + division) / 2, 2.55, b.zMin + 0.02, 0, 4.2, 140);
  letrero("Pool", (division + b.xMax) / 2, 2.55, b.zMin + 0.02, 0, 3.2, 150);
  letrero("Guayabal", b.xMin + 0.02, 2.5, centro.z, Math.PI / 2, 4.4, 160);

  // media pared con pasamanos de latón entre las dos zonas
  const muro = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.95, 4.6), M.madera);
  muro.position.set(division, 0.475, b.zMin + 2.3);
  muro.castShadow = muro.receiveShadow = true;
  const pasamanos = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.05, 4.7), M.laton);
  pasamanos.position.set(division, 0.97, b.zMin + 2.3);
  scene.add(muro, pasamanos);

  // bancas de espectadores contra la pared del fondo y portatacos en la pared izquierda
  const banca = (x) => {
    const base = new THREE.Mesh(new RoundedBoxGeometry(1.9, 0.42, 0.5, 2, 0.04), M.madera);
    base.position.set(x, 0.21, b.zMin + 0.38);
    const cojin = new THREE.Mesh(new RoundedBoxGeometry(1.86, 0.1, 0.48, 2, 0.04), M.cuero);
    cojin.position.set(x, 0.47, b.zMin + 0.38);
    base.castShadow = cojin.castShadow = true;
    scene.add(base, cojin);
  };
  [-6.2, -2.3, 1.6, 6.1].forEach(banca);

  const geoTaco = new THREE.CylinderGeometry(0.008, 0.016, 1.45, 8);
  const portatacos = (z) => {
    const tabla = new THREE.Mesh(new THREE.BoxGeometry(0.05, 1.5, 0.9), M.madera);
    tabla.position.set(b.xMin + 0.03, 1.15, z);
    scene.add(tabla);
    for (let i = 0; i < 7; i++) {
      const taco = new THREE.Mesh(geoTaco, M.maderaClara);
      taco.position.set(b.xMin + 0.1, 1.12, z - 0.36 + i * 0.12);
      taco.rotation.x = (i - 3) * 0.015;
      scene.add(taco);
    }
  };
  portatacos(-1.9);
  portatacos(1.95);

  // ---------- luces de ambiente ----------
  scene.add(new THREE.HemisphereLight(0x35548a, 0x1a0e08, 0.55));
  const clave = new THREE.DirectionalLight(0xc9d8ff, 0.55);
  clave.position.set(centro.x + 5, 13, centro.z + 7);
  clave.target.position.copy(centro);
  if (alta) {
    clave.castShadow = true;
    clave.shadow.mapSize.set(2048, 2048);
    Object.assign(clave.shadow.camera, { left: -12, right: 12, top: 9, bottom: -9, near: 2, far: 40 });
    clave.shadow.bias = -0.0004;
    clave.shadow.normalBias = 0.02;
  }
  scene.add(clave, clave.target);

  // ---------- mesas ----------
  const mesas = new Map();
  const cajas = [];
  const geoDomo = new THREE.SphereGeometry(0.2, alta ? 28 : 18, 10, 0, Math.PI * 2, 0, Math.PI * 0.45);

  function crearMesa(m, indice) {
    const esPool = m.modalidad === "pool";
    const med = MEDIDAS[m.modalidad] || MEDIDAS.carambola;
    const L = med.largo, W = med.ancho, c = 0.05, r = 0.15;
    const OL = L + 2 * (c + r), OW = W + 2 * (c + r);
    const grupo = new THREE.Group();
    grupo.position.set(m.x, 0, m.z);
    const cuerpo = new THREE.Group(); // lo que se eleva al elegir la mesa
    grupo.add(cuerpo);
    const add = (geo, mat, x, y, z, sombra = true) => {
      const o = new THREE.Mesh(geo, mat);
      o.position.set(x, y, z);
      o.castShadow = sombra && alta;
      o.receiveShadow = true;
      cuerpo.add(o);
      return o;
    };
    const pano = esPool ? M.panoVerde : M.panoAzul;
    const banda = esPool ? M.bandaVerde : M.bandaAzul;

    add(new RoundedBoxGeometry(OL - 0.18, 0.2, OW - 0.18, 2, 0.05), M.madera, 0, 0.66, 0);
    add(new THREE.BoxGeometry(L + 2 * c, 0.05, W + 2 * c), pano, 0, ALTO_PANO - 0.025, 0, false);
    for (const s of [-1, 1]) {
      add(new THREE.BoxGeometry(L + 2 * c, 0.035, c), banda, 0, ALTO_PANO + 0.0175, s * (W / 2 + c / 2), false);
      add(new THREE.BoxGeometry(c, 0.035, W), banda, s * (L / 2 + c / 2), ALTO_PANO + 0.0175, 0, false);
      add(new RoundedBoxGeometry(OL, 0.055, r, 2, 0.02), M.madera, 0, ALTO_PANO + 0.02, s * (W / 2 + c + r / 2));
      add(new RoundedBoxGeometry(r, 0.055, W + 2 * c + 0.002, 2, 0.02), M.madera, s * (L / 2 + c + r / 2), ALTO_PANO + 0.02, 0);
    }
    // patas cónicas con pies de latón
    const geoPata = new THREE.CylinderGeometry(0.085, 0.11, 0.56, 4);
    const geoPie = new THREE.CylinderGeometry(0.1, 0.11, 0.04, 16);
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
      const pata = add(geoPata, M.madera, sx * (OL / 2 - 0.34), 0.3, sz * (OW / 2 - 0.3));
      pata.rotation.y = Math.PI / 4;
      add(geoPie, M.laton, sx * (OL / 2 - 0.34), 0.02, sz * (OW / 2 - 0.3), false);
    }
    // diamantes de nácar sobre los rieles
    const geoDiamante = new THREE.CircleGeometry(0.014, 10);
    geoDiamante.rotateX(-Math.PI / 2);
    const diamantes = new THREE.InstancedMesh(geoDiamante, M.nacar, 20);
    const tmp = new THREE.Object3D();
    let k = 0;
    const yR = ALTO_PANO + 0.0485;
    for (const s of [-1, 1]) {
      for (let i = 1; i <= 7; i++) { if (esPool && i === 4) continue; tmp.position.set(-L / 2 + (L * i) / 8, yR, s * (W / 2 + c + r / 2)); tmp.updateMatrix(); diamantes.setMatrixAt(k++, tmp.matrix); }
      for (let i = 1; i <= 3; i++) { tmp.position.set(s * (L / 2 + c + r / 2), yR, -W / 2 + (W * i) / 4); tmp.updateMatrix(); diamantes.setMatrixAt(k++, tmp.matrix); }
    }
    diamantes.count = k;
    cuerpo.add(diamantes);

    if (esPool) {
      // seis troneras con aro cromado
      const geoTronera = new THREE.CylinderGeometry(0.066, 0.066, 0.02, 20);
      const geoAro = new THREE.TorusGeometry(0.07, 0.013, 8, 24);
      geoAro.rotateX(Math.PI / 2);
      const puntos = [];
      for (const sz of [-1, 1]) { puntos.push([-L / 2 - 0.012, sz * (W / 2 + 0.012)], [L / 2 + 0.012, sz * (W / 2 + 0.012)], [0, sz * (W / 2 + 0.035)]); }
      for (const [x, z] of puntos) {
        add(geoTronera, M.tronera, x, ALTO_PANO + 0.04, z, false);
        add(geoAro, M.cromo, x, ALTO_PANO + 0.05, z, false);
      }
    } else {
      // esquineros de latón
      const geoEsquina = new RoundedBoxGeometry(0.17, 0.06, 0.17, 2, 0.02);
      for (const sx of [-1, 1]) for (const sz of [-1, 1]) add(geoEsquina, M.laton, sx * (OL / 2 - 0.08), ALTO_PANO + 0.024, sz * (OW / 2 - 0.08), false);
    }

    // bolas
    const yB = ALTO_PANO + R_BOLA;
    const bola = (mat, x, z) => {
      const o = new THREE.Mesh(geoBola, mat);
      o.position.set(x, yB, z);
      o.castShadow = alta;
      cuerpo.add(o);
    };
    if (esPool) {
      const colores = ["#f4c20d", "#1f4fbf", "#d62b1e", "#5b2a86", "#f07c12", "#0f7a3c", "#7a1616", "#101010"];
      const lisas = colores.map(bolaMat);
      const rayadas = colores.slice(0, 7).map((col) => new THREE.MeshPhysicalMaterial({ map: tx.bolaRayada(col), roughness: 0.14, clearcoat: 1 }));
      const orden = [0, 8, 1, 9, 7, 2, 10, 3, 11, 12, 4, 13, 5, 14, 6]; // 1 en la punta, 8 en el centro
      const juego = (n) => (n < 8 ? lisas[n] : rayadas[n - 8]);
      if (indice % 2 === 0) {
        const d = R_BOLA * 2.04, pie = L * 0.25;
        let n = 0;
        for (let fila = 0; fila < 5; fila++) for (let j = 0; j <= fila; j++) {
          bola(juego(orden[n++]), pie + fila * d * 0.866, (j - fila / 2) * d);
        }
      } else {
        const azar = (() => { let s = 31; return () => ((s = (s * 16807) % 2147483647) - 1) / 2147483646; })();
        const puestos = [];
        for (let n = 0; n < 9; n++) {
          let x, z, intentos = 0;
          do { x = (azar() - 0.5) * (L - 0.3); z = (azar() - 0.5) * (W - 0.3); intentos++; }
          while (intentos < 30 && puestos.some(([px, pz]) => Math.hypot(px - x, pz - z) < R_BOLA * 3));
          puestos.push([x, z]);
          bola(juego(orden[n + 3]), x, z);
        }
      }
      bola(bolaMat("#f7f5ec"), -L * 0.27, 0.05);
    } else {
      bola(bolaMat("#f7f5ec"), -L * 0.22, W * 0.12);
      bola(bolaMat("#f2c21b"), -L * 0.3, -W * 0.2);
      bola(bolaMat("#d3271c"), L * 0.24, W * 0.04);
    }
    if (indice % 3 === 1) {
      const taco = add(geoTaco, M.maderaClara, -L * 0.05, ALTO_PANO + 0.016, W * 0.28, true);
      taco.rotation.z = Math.PI / 2;
      taco.rotation.y = 0.22;
    }

    // sombra de contacto y halo de selección
    const sombra = new THREE.Mesh(new THREE.PlaneGeometry(OL + 0.9, OW + 0.9),
      new THREE.MeshBasicMaterial({ map: texSombra, transparent: true, depthWrite: false, opacity: 0.75 }));
    sombra.rotation.x = -Math.PI / 2;
    sombra.position.y = 0.008;
    grupo.add(sombra);
    const halo = new THREE.Mesh(new THREE.PlaneGeometry(OL + 1.5, OW + 1.5),
      new THREE.MeshBasicMaterial({ map: texHalo, color: ORO, transparent: true, depthWrite: false, opacity: 0, blending: THREE.AdditiveBlending, toneMapped: false }));
    halo.rotation.x = -Math.PI / 2;
    halo.position.y = 0.012;
    grupo.add(halo);

    // lámpara de tres pantallas, colgada del techo
    const lampara = new THREE.Group();
    const yL = 2.05;
    const barra = new THREE.Mesh(new THREE.BoxGeometry(L * 0.78, 0.035, 0.05), M.laton);
    barra.position.y = yL + 0.2;
    lampara.add(barra);
    for (const s of [-1, 1]) {
      const cable = new THREE.Mesh(new THREE.CylinderGeometry(0.006, 0.006, 0.7, 6), M.cable);
      cable.position.set(s * L * 0.36, yL + 0.55, 0);
      lampara.add(cable);
    }
    const interiores = [];
    for (const px of [-L / 3, 0, L / 3]) {
      const domo = new THREE.Mesh(geoDomo, M.pantalla);
      domo.position.set(px, yL, 0);
      domo.scale.y = 0.85;
      const interior = new THREE.Mesh(geoDomo, new THREE.MeshBasicMaterial({ color: 0x000000, side: THREE.BackSide, toneMapped: false }));
      interior.position.copy(domo.position);
      interior.scale.set(0.97, 0.83, 0.97);
      const foco = new THREE.Mesh(new THREE.SphereGeometry(0.05, 12, 8), interior.material);
      foco.position.set(px, yL + 0.04, 0);
      const varilla = new THREE.Mesh(new THREE.CylinderGeometry(0.008, 0.008, 0.2, 6), M.laton);
      varilla.position.set(px, yL + 0.13, 0);
      lampara.add(domo, interior, foco, varilla);
      interiores.push(interior.material);
    }
    grupo.add(lampara);

    const foco = new THREE.SpotLight(LUZ_CALIDA, 0, 6, 0.78, 0.75, 1.6);
    foco.position.set(0, yL - 0.05, 0);
    foco.target.position.set(0, 0, 0);
    grupo.add(foco, foco.target);

    // número flotante
    const texNormal = tx.numero(m.numero), texElegido = tx.numero(m.numero, true);
    const etiqueta = new THREE.Sprite(new THREE.SpriteMaterial({ map: texNormal, depthTest: false, transparent: true }));
    etiqueta.scale.set(0.4, 0.4, 1);
    etiqueta.position.set(-OL / 2 + 0.05, 1.18, OW / 2 - 0.05);
    etiqueta.renderOrder = 10;
    grupo.add(etiqueta);

    // caja invisible para detectar el cursor y el toque
    const caja = new THREE.Mesh(new THREE.BoxGeometry(OL + 0.2, 1.0, OW + 0.2), new THREE.MeshBasicMaterial({ visible: false }));
    caja.position.y = 0.5;
    caja.userData.id = String(m.id);
    grupo.add(caja);
    cajas.push(caja);

    scene.add(grupo);
    mesas.set(String(m.id), {
      datos: m, grupo, cuerpo, halo, foco, interiores, etiqueta, texNormal, texElegido, lampara, OL, OW,
      encendido: reducido ? 1 : 0, metaEncendido: reducido ? 1 : 0, retraso: 0.35 + indice * 0.12,
      hover: 0, metaHover: 0, sel: 0, metaSel: 0, estado: "",
    });
  }
  mesasDatos.forEach(crearMesa);

  // ---------- cámara y controles ----------
  const controles = new OrbitControls(camera, lienzo);
  Object.assign(controles, {
    enableDamping: true, dampingFactor: 0.08, rotateSpeed: 0.55, zoomSpeed: 0.8, panSpeed: 0.7,
    screenSpacePanning: false, minDistance: 3, maxPolarAngle: 1.36, minPolarAngle: 0,
  });
  controles.touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN };
  lienzo.style.touchAction = "pan-y"; // deslizar en vertical sigue moviendo la página en el celular
  controles.target.copy(centro);

  // La rueda del mouse mueve la página; con Ctrl/⌘ (o pellizco en el trackpad) acerca la sala.
  const filtrarRueda = (e) => { if (!e.ctrlKey && !e.metaKey) e.stopPropagation(); };
  contenedor.addEventListener("wheel", filtrarRueda, { capture: true });

  const esVertical = () => camera.aspect < 1;
  const VISTAS = {
    iso: () => (esVertical() ? { theta: 1.5, phi: 0.86 } : { theta: 0.64, phi: 0.98 }),
    cenital: () => ({ theta: esVertical() ? Math.PI / 2 : 0, phi: 0.001 }),
    ras: () => ({ theta: esVertical() ? 1.2 : 0.5, phi: 1.22, acercar: 0.62 }),
  };

  const esferica = new THREE.Spherical();
  const posDesde = (target, theta, phi, radio) =>
    new THREE.Vector3().setFromSpherical(esferica.set(radio, phi, theta)).add(target);

  // Encuadre: distancia y punto de mira para que el contorno llene la pantalla, centrado, con un margen.
  function encuadrar(puntos, target, theta, phi, margen = 0.9) {
    let d = 20;
    const mira = target.clone();
    const guardada = camera.position.clone(), guardadaQ = camera.quaternion.clone();
    const derecha = new THREE.Vector3(), arriba = new THREE.Vector3();
    for (let i = 0; i < 6; i++) {
      camera.position.copy(posDesde(mira, theta, phi, d));
      camera.up.set(0, 1, 0);
      camera.lookAt(mira);
      camera.updateMatrixWorld();
      let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
      for (const p of puntos) {
        const v = p.clone().project(camera);
        x0 = Math.min(x0, v.x); x1 = Math.max(x1, v.x); y0 = Math.min(y0, v.y); y1 = Math.max(y1, v.y);
      }
      const medioAlto = d * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
      derecha.setFromMatrixColumn(camera.matrixWorld, 0);
      arriba.setFromMatrixColumn(camera.matrixWorld, 1);
      mira.addScaledVector(derecha, ((x0 + x1) / 2) * medioAlto * camera.aspect);
      mira.addScaledVector(arriba, ((y0 + y1) / 2) * medioAlto);
      d *= Math.max((x1 - x0) / 2, (y1 - y0) / 2) / margen;
    }
    camera.position.copy(guardada);
    camera.quaternion.copy(guardadaQ);
    camera.updateMatrixWorld();
    return { radio: d, target: mira };
  }
  const contornoSala = [];
  for (const x of [b.xMin, b.xMax]) for (const z of [b.zMin, b.zMax]) contornoSala.push(new THREE.Vector3(x, 0, z));
  contornoSala.push(new THREE.Vector3(b.xMin, 2.6, b.zMin), new THREE.Vector3(b.xMax, 2.6, b.zMin), new THREE.Vector3(b.xMin, 2.6, b.zMax));

  // ---------- animación de cámara ----------
  let tween = null;
  let vistaActual = "iso";
  function estadoCamara() {
    esferica.setFromVector3(camera.position.clone().sub(controles.target));
    return { target: controles.target.clone(), theta: esferica.theta, phi: esferica.phi, radio: esferica.radius };
  }
  function animarCamara(destino, ms = 900) {
    const desde = estadoCamara();
    let dTheta = destino.theta - desde.theta;
    dTheta = Math.atan2(Math.sin(dTheta), Math.cos(dTheta)); // camino más corto
    const hacia = { ...destino, theta: desde.theta + dTheta };
    if (reducido || ms === 0) { aplicarCamara(hacia); return; }
    tween = { desde, hacia, inicio: performance.now(), ms };
    controles.enabled = false;
  }
  function aplicarCamara({ target, theta, phi, radio }) {
    controles.target.copy(target);
    camera.position.copy(posDesde(target, theta, Math.max(phi, 0.001), radio));
    camera.lookAt(target);
    controles.update();
    sucio = true;
  }
  function pasoTween(ahora) {
    if (!tween) return false;
    const t = Math.min(1, (ahora - tween.inicio) / tween.ms), e = easeInOut(t);
    const { desde: a, hacia: z } = tween;
    aplicarCamara({
      target: a.target.clone().lerp(z.target, e),
      theta: a.theta + (z.theta - a.theta) * e, phi: a.phi + (z.phi - a.phi) * e, radio: a.radio + (z.radio - a.radio) * e,
    });
    if (t >= 1) { tween = null; controles.enabled = true; }
    return true;
  }
  function destinoVista(nombre) {
    const v = VISTAS[nombre]();
    const e = encuadrar(contornoSala, centro, v.theta, Math.max(v.phi, 0.001), 0.97);
    const radio = e.radio * (v.acercar || 1);
    controles.maxDistance = Math.max(Number.isFinite(controles.maxDistance) ? controles.maxDistance : 0, e.radio * 1.5);
    return { target: v.acercar ? e.target.lerp(centro, 0.5) : e.target, theta: v.theta, phi: v.phi, radio };
  }
  function enfocarMesa(id) {
    const m = mesas.get(id);
    if (!m) return;
    const actual = estadoCamara();
    const phi = Math.min(Math.max(actual.phi, 0.62), 1.12);
    const target = new THREE.Vector3(m.grupo.position.x, 0.55, m.grupo.position.z);
    const puntos = [];
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) puntos.push(new THREE.Vector3(target.x + sx * (m.OL / 2 + 0.5), 0, target.z + sz * (m.OW / 2 + 0.5)));
    puntos.push(new THREE.Vector3(target.x, 2.2, target.z));
    const e = encuadrar(puntos, target, actual.theta, phi, 0.7);
    animarCamara({ target: e.target, theta: actual.theta, phi, radio: Math.min(actual.radio, e.radio) }, 1000);
  }

  // ---------- tamaño ----------
  let primeraVez = true, interactuo = false, elegidaCamara = false;
  controles.addEventListener("start", () => { interactuo = true; });
  function ajustarTamano() {
    const { width, height } = contenedor.getBoundingClientRect();
    if (!width || !height) return;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    if (primeraVez) {
      primeraVez = false;
      const meta = destinoVista("iso");
      if (reducido) aplicarCamara(meta);
      else {
        aplicarCamara({ ...meta, theta: meta.theta - 0.55, phi: 0.42, radio: meta.radio * 1.35 });
        animarCamara(meta, 2200);
      }
    } else if (!interactuo && !elegidaCamara) {
      tween = null;
      controles.enabled = true;
      aplicarCamara(destinoVista(vistaActual));
    }
    sucio = true;
  }
  const observadorTamano = new ResizeObserver(ajustarTamano);
  observadorTamano.observe(contenedor);

  // ---------- cursor y toque ----------
  const raycaster = new THREE.Raycaster();
  const puntero = new THREE.Vector2();
  let pendienteHover = null, idHover = null, inicioToque = null;

  function mesaEn(clientX, clientY) {
    const r = lienzo.getBoundingClientRect();
    puntero.set(((clientX - r.left) / r.width) * 2 - 1, -((clientY - r.top) / r.height) * 2 + 1);
    raycaster.setFromCamera(puntero, camera);
    const hit = raycaster.intersectObjects(cajas, false)[0];
    return hit ? hit.object.userData.id : null;
  }
  lienzo.addEventListener("pointermove", (e) => {
    if (e.pointerType === "mouse") pendienteHover = { x: e.clientX, y: e.clientY };
  });
  lienzo.addEventListener("pointerleave", () => { pendienteHover = null; ponerHover(null); });
  lienzo.addEventListener("pointerdown", (e) => { inicioToque = { x: e.clientX, y: e.clientY, t: performance.now() }; });
  lienzo.addEventListener("pointerup", (e) => {
    if (!inicioToque) return;
    const mov = Math.hypot(e.clientX - inicioToque.x, e.clientY - inicioToque.y);
    const rapido = performance.now() - inicioToque.t < 600;
    inicioToque = null;
    if (mov > 8 || !rapido) return;
    const id = mesaEn(e.clientX, e.clientY);
    if (id) alSeleccionar?.(id);
  });

  function ponerHover(id, punto) {
    if (id === idHover) return;
    idHover = id;
    for (const [k, m] of mesas) m.metaHover = k === id ? 1 : 0;
    lienzo.style.cursor = id ? "pointer" : "";
    alResaltar?.(id, punto);
  }

  // ---------- bucle de dibujo (solo cuando algo cambia) ----------
  let sucio = true, raf = 0, ultimo = performance.now(), visible = true, inicioEscena = performance.now();
  const colorInterior = new THREE.Color();

  function cuadro(ahora) {
    raf = requestAnimationFrame(cuadro);
    const dt = Math.min(0.05, (ahora - ultimo) / 1000);
    ultimo = ahora;
    let cambio = pasoTween(ahora);
    if (controles.enabled && controles.update()) cambio = true;

    if (pendienteHover && !tween) {
      const r = lienzo.getBoundingClientRect();
      ponerHover(mesaEn(pendienteHover.x, pendienteHover.y), { x: pendienteHover.x - r.left, y: pendienteHover.y - r.top });
      pendienteHover = null;
    }

    const transcurrido = (ahora - inicioEscena) / 1000;
    for (const m of mesas.values()) {
      if (!reducido && transcurrido > m.retraso) m.metaEncendido = 1;
      const antes = m.encendido + m.hover + m.sel;
      m.encendido = suavizar(m.encendido, m.metaEncendido, dt, 5);
      m.hover = suavizar(m.hover, m.metaHover, dt, 12);
      m.sel = suavizar(m.sel, m.metaSel, dt, 8);
      if (Math.abs(m.encendido + m.hover + m.sel - antes) < 1e-4) continue;
      cambio = true;
      const apagada = m.estado === "ocupada" || m.estado === "mantenimiento" ? 0.35 : 1;
      m.foco.intensity = 9 * m.encendido * apagada * (1 + 0.55 * m.hover + 1.1 * m.sel);
      colorInterior.copy(LUZ_CALIDA).multiplyScalar((0.15 + 0.85 * m.encendido) * apagada * (1 + 0.4 * m.hover + 0.6 * m.sel));
      for (const mat of m.interiores) mat.color.copy(colorInterior);
      m.halo.material.opacity = 0.25 * m.hover + 0.6 * m.sel;
      m.cuerpo.position.y = 0.05 * m.sel;
    }
    if (cambio) sucio = true;
    if (sucio && visible) {
      renderer.render(scene, camera);
      sucio = false;
    }
  }

  const observadorVista = new IntersectionObserver((entradas) => {
    visible = entradas[entradas.length - 1].isIntersecting; // el aviso más reciente manda
    if (visible && !raf) { ultimo = performance.now(); raf = requestAnimationFrame(cuadro); sucio = true; }
    if (!visible && raf) { cancelAnimationFrame(raf); raf = 0; }
  });
  observadorVista.observe(contenedor);
  controles.addEventListener("change", () => {
    // que la cámara no se vaya lejos de la sala al desplazarla
    controles.target.x = THREE.MathUtils.clamp(controles.target.x, b.xMin, b.xMax);
    controles.target.z = THREE.MathUtils.clamp(controles.target.z, b.zMin, b.zMax);
    controles.target.y = THREE.MathUtils.clamp(controles.target.y, 0, 1.5);
    sucio = true;
  });
  lienzo.addEventListener("webglcontextlost", (e) => { e.preventDefault(); alFallar?.(); });
  raf = requestAnimationFrame(cuadro);

  let elegida = null;
  return {
    tipo: "3d",
    seleccionar(id, { enfocar = true } = {}) {
      id = id == null ? null : String(id);
      elegida = id;
      for (const [k, m] of mesas) {
        m.metaSel = k === id ? 1 : 0;
        m.etiqueta.material.map = k === id ? m.texElegido : m.texNormal;
        m.halo.material.color.copy(ORO);
      }
      if (id && enfocar) { elegidaCamara = true; enfocarMesa(id); }
      sucio = true;
    },
    resaltar(id) {
      for (const [k, m] of mesas) m.metaHover = k === String(id) ? 1 : 0;
    },
    vista(nombre) {
      if (!VISTAS[nombre]) return;
      vistaActual = nombre;
      for (const m of mesas.values()) m.lampara.visible = nombre !== "cenital";
      animarCamara(destinoVista(nombre), 1100);
    },
    zoom(paso) {
      const a = estadoCamara();
      const radio = THREE.MathUtils.clamp(a.radio * (paso > 0 ? 0.72 : 1 / 0.72), controles.minDistance, controles.maxDistance);
      animarCamara({ ...a, radio }, 450);
    },
    restablecer() {
      this.vista(vistaActual === "cenital" ? "cenital" : "iso");
    },
    marcarEstados(estados) {
      for (const [k, m] of mesas) { m.estado = estados?.get(k) || ""; m.encendido -= 1e-3; }
    },
    get elegida() { return elegida; },
    destruir() {
      cancelAnimationFrame(raf);
      raf = 0;
      observadorTamano.disconnect();
      observadorVista.disconnect();
      contenedor.removeEventListener("wheel", filtrarRueda, { capture: true });
      controles.dispose();
      scene.traverse((o) => {
        o.geometry?.dispose?.();
        const mats = Array.isArray(o.material) ? o.material : o.material ? [o.material] : [];
        for (const mt of mats) { mt.map?.dispose?.(); mt.dispose?.(); }
      });
      renderer.dispose();
      lienzo.remove();
    },
  };
}
