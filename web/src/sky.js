/* Time of day → lighting, the sky dome and the sea of clouds. Puff clouds come later (phase 1, clouds module). */
import * as THREE from "three";
import { clamp, smooth, norm3, rng } from "./world.js";
import { FALLS } from "./island.js";
import { makeCloudMaterial } from "./materials/fx.js";
import { makeSkyMaterial, makeSeaMaterial } from "./materials/sky.js";

// time of day → lighting
export function sky(tod) {
  const t = ((tod % 24) + 24) % 24;
  const a = (t - 6) / 12 * Math.PI;
  const sun = norm3([Math.cos(a), Math.sin(a) * 1.15, 0.38 + Math.sin(a) * 0.15]);
  const dayF = smooth(-0.07, 0.10, sun[1]);
  const night = 1 - dayF;
  const gold = dayF * (1 - smooth(0.04, 0.42, sun[1]));
  const moon = norm3([-0.35, 0.62, -0.45]);
  const sunCol = [1.0 * 1.15, (0.95 - 0.33 * gold) * 1.15, (0.88 - 0.5 * gold) * 1.15].map(v => v * clamp(sun[1] * 4 + 0.15, 0, 1));
  const moonCol = [0.030, 0.038, 0.060];
  const lightDir = dayF > 0.15 ? sun : moon;
  const lightCol = dayF > 0.15 ? sunCol : moonCol;
  // lights-on schedule: busiest in the evening, fewer after midnight
  const lit = t >= 17 ? 0.55 + 0.35 * smooth(17, 20, t) : t < 5 ? 0.5 - t * 0.04 : 0.35;
  return { sun, night, gold, lightDir, lightCol, moon, lit, dayF };
}
// skyAmb() of the shaders: skyColor((0, 1, 0)) desaturated, for the light L of sky(tod)
export function skyAmbient(L) {
  const sa = Math.max(L.sun[1], 0), gold = L.gold, mix = (a, b, t) => a.map((v, i) => v + (b[i] - v) * t);
  let day = mix([0.20, 0.40, 0.76], [0.28, 0.32, 0.58], gold * 0.7);
  day = day.map((v, i) => v + [1.0, 0.78, 0.52][i] * Math.pow(sa, 10) * (0.22 + 0.7 * gold));
  const night = [0.008, 0.013, 0.04].map((v, i) => v + [0.30, 0.15, 0.07][i] * Math.exp(-12) * 0.42);
  const s = mix(day, night, L.night), l = s[0] * 0.3 + s[1] * 0.5 + s[2] * 0.2;
  return s.map(v => (l + (v - l) * 0.45) * 1.05);
}
export function fmtTod(t) { t = ((t % 24) + 24) % 24; const h = Math.floor(t), m = Math.floor((t - h) * 60); return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`; }

// full-screen triangle (the vertex shader uses gl_VertexID; the attribute only sets the draw count)
export function makeSky() {
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(9), 3));
  const m = new THREE.Mesh(g, makeSkyMaterial());
  m.frustumCulled = false; m.renderOrder = -10;
  return m;
}
export const SEA_Y = -1900;
export function makeSea() {
  const G = 90000, g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(new Float32Array([-G, -G, G, -G, G, G, -G, -G, G, G, -G, G]), 2));
  g.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, SEA_Y, 0), G * Math.SQRT2);   // xz-only positions: three.js cannot compute it
  const m = new THREE.Mesh(g, makeSeaMaterial(SEA_Y));
  m.frustumCulled = false; m.renderOrder = -5;
  return m;
}

/* ---------------- clouds: camera-facing puffs above and below the island, mist at the waterfalls' feet ---------------- */
function puffTexture() {
  const S = 128, cv = document.createElement("canvas"); cv.width = cv.height = S;
  const g = cv.getContext("2d"); const R = rng(3);
  g.fillStyle = "#000"; g.fillRect(0, 0, S, S); g.globalCompositeOperation = "lighter";
  for (let i = 0; i < 22; i++) {
    const x = S / 2 + (R() - 0.5) * S * 0.45, y = S / 2 + (R() - 0.5) * S * 0.35, r = S * (0.12 + R() * 0.2);
    const gr = g.createRadialGradient(x, y, 0, x, y, r); gr.addColorStop(0, "rgba(255,255,255,0.32)"); gr.addColorStop(1, "rgba(255,255,255,0)");
    g.fillStyle = gr; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
  }
  const id = g.getImageData(0, 0, S, S), d = id.data;
  for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) {
    const k = (y * S + x) * 4, dx = (x - S / 2) / (S / 2), dy = (y - S / 2) / (S / 2), fall = clamp(1.25 - Math.hypot(dx, dy) * 1.2, 0, 1);
    const v = Math.min(255, d[k] * 1.2) * fall; d[k] = d[k + 1] = d[k + 2] = v; d[k + 3] = 255;
  }
  g.putImageData(id, 0, 0);
  const t = new THREE.CanvasTexture(cv); t.flipY = false; return t;
}
// tex: the GPT Image cloud sprite (alpha = coverage), or null for the procedural puff
export function makeClouds(tex) {
  const R = rng(11), puffs = [];
  for (let c = 0; c < 78; c++) {
    const below = c % 2 === 1;
    const cx = (R() - 0.5) * 15000, cz = (R() - 0.5) * 15000, cy = below ? -1500 + R() * 900 : 650 + R() * 450;
    const n = 6 + (R() * 9 | 0), size = 160 + R() * 160;
    for (let k = 0; k < n; k++) {
      const dx = (R() - 0.5) * size * 3.2, dz = (R() - 0.5) * size * 2.2, dy = R() * size * 0.5;
      puffs.push({ x: cx + dx, y: cy + dy, z: cz + dz, s: size * (0.7 + R() * 0.7), lit: clamp(0.35 + dy / (size * 0.5) * 0.6 + R() * 0.15, 0, 1), a: 0.55 + R() * 0.35 });
    }
  }
  // spray and mist at the foot of every waterfall (anchored, no drift)
  for (const G of FALLS.groups) {
    const n = Math.min(14, 3 + Math.floor(G.w / 160));
    for (let k = 0; k < n; k++) {
      const t = (k + 0.5) / n, along = (t - 0.5) * G.w * 0.9, tx = -G.oz, tz = G.ox;
      const out = 140 * (G.H / 1400);
      puffs.push({ x: G.x + tx * along + G.ox * out, y: G.y - G.H * (0.55 + R() * 0.25), z: G.z + tz * along + G.oz * out, s: 120 + R() * 160 * (G.H / 1400), lit: 0.85, a: 0.55, fixed: true });
      if (R() < 0.5) puffs.push({ x: G.x + tx * along + G.ox * 10, y: G.y - 40 - R() * 60, z: G.z + tz * along + G.oz * 10, s: 40 + R() * 40, lit: 1, a: 0.35, fixed: true });
    }
  }
  const g = new THREE.InstancedBufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(new Float32Array([-1, -1, 1, -1, 1, 1, -1, -1, 1, 1, -1, 1]), 2));
  const buf = new Float32Array(puffs.length * 6), ib = new THREE.InstancedInterleavedBuffer(buf, 6);
  g.setAttribute("puff", new THREE.InterleavedBufferAttribute(ib, 4, 0)); g.setAttribute("plit", new THREE.InterleavedBufferAttribute(ib, 2, 4));
  g.instanceCount = puffs.length; g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1e5);
  const mesh = new THREE.Mesh(g, makeCloudMaterial(tex || puffTexture()));
  mesh.frustumCulled = false; mesh.renderOrder = 14;
  const u = mesh.material.uniforms; u.uPuffA.value = tex ? 1 : 0; u.uAspect.value = tex ? 1.5 : 1;
  return { puffs, buf, ib, mesh };
}
// per frame: drift with the wind (wrapping round a 15 km square), sort far → near
export function updateClouds(C, wind, eye, night, camera) {
  const buf = C.buf, wx = wind[0], wz = wind[1];
  const list = C.puffs.map(p => {
    const x = p.fixed ? p.x : ((p.x + wx + 7500) % 15000 + 15000) % 15000 - 7500, z = p.fixed ? p.z : ((p.z + wz + 7500) % 15000 + 15000) % 15000 - 7500;
    return [x, p.y, z, p.s, p.lit, p.a, (x - eye[0]) ** 2 + (p.y - eye[1]) ** 2 + (z - eye[2]) ** 2];
  }).sort((a, b) => b[6] - a[6]);
  list.forEach((q, i) => { const o = i * 6; buf[o] = q[0]; buf[o + 1] = q[1]; buf[o + 2] = q[2]; buf[o + 3] = q[3]; buf[o + 4] = q[4]; buf[o + 5] = q[5] * (1 - night * 0.35); });
  C.ib.needsUpdate = true;
  const e = camera.matrixWorld.elements, u = C.mesh.material.uniforms;
  u.uCamR.value.set(e[0], e[1], e[2]); u.uCamU.value.set(e[4], e[5], e[6]);
}
