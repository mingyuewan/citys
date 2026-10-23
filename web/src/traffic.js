/* Cars and buses along the major roads (and over the bridges), pedestrians and cyclists on the sidewalks and
   promenades. Ported verbatim from src/city.src.html (buildTraffic / stepTraffic / buildWalkers / stepWalkers). */
import { rng, hash1 } from "./world.js";
import { ROADW, LANES } from "./roads.js";
import * as THREE from "three";
import { InstDynamic, templateAttrs, PROP_LAYOUT, PROP_INST, LATE_SHADOW } from "./instancing.js";
import { makeInstMaterial, makeInstShadowMaterial } from "./materials/street.js";
import { makePointMaterial } from "./materials/fx.js";
import { TPL } from "./templates.js";

export function buildWalkers(osm, waterAt) {
  const side = [], prom = [], cyc = [];
  for (const r of osm.roads) {
    const cum = [0]; for (let i = 1; i < r.pts.length; i++) cum.push(cum[i - 1] + Math.hypot(r.pts[i][0] - r.pts[i - 1][0], r.pts[i][1] - r.pts[i - 1][1]));
    const L = cum[cum.length - 1]; if (L < 30) continue;
    const ln = { r, cum, L };
    if (LANES[r.hw] && !r._ribbon) { ln.off = ROADW[r.hw] / 2 + 1.6; side.push(ln); }
    else if (/^(footway|cycleway|path|pedestrian)$/.test(r.hw)) {
      const m = r.pts[r.pts.length >> 1];
      const nearW = waterAt(m[0] + 35, m[1]) || waterAt(m[0] - 35, m[1]) || waterAt(m[0], m[1] + 35) || waterAt(m[0], m[1] - 35);
      ln.off = 0;
      if (r.hw === "cycleway") cyc.push(ln);
      if (nearW || hash1(m[0] + m[1]) < 0.35) prom.push(ln);
    }
  }
  const W = [], R = rng(808);
  const pick = (arr, n, kind) => {
    if (!arr.length) return;
    const tot = arr.reduce((a, l) => a + l.L, 0);
    for (let k = 0; k < n; k++) {
      let t = R() * tot, i = 0; while (i < arr.length - 1 && t > arr[i].L) { t -= arr[i].L; i++; }
      const l = arr[i], bike = kind === 1;
      const CL = [[0.85, 0.20, 0.18], [0.15, 0.30, 0.65], [0.92, 0.92, 0.90], [0.10, 0.10, 0.12], [0.95, 0.75, 0.20], [0.30, 0.55, 0.35], [0.85, 0.50, 0.60], [0.55, 0.55, 0.58]];
      W.push({ l, s: R() * l.L, dir: R() < 0.5 ? 1 : -1, lat: (l.off ? l.off * (R() < 0.5 ? 1 : -1) : (R() - 0.5) * 2.2) + (R() - 0.5) * 0.8, v: bike ? 4 + R() * 2 : 1.0 + R() * 0.6, col: CL[(R() * CL.length) | 0], bike });
    }
  };
  pick(side, 2600, 0); pick(prom, 1400, 0); pick(cyc.length ? cyc : prom, 320, 1);
  const peds = W.filter(w => !w.bike), bikes = W.filter(w => w.bike);
  return { peds, bikes, pInst: new Float32Array(peds.length * 8), bInst: new Float32Array(bikes.length * 8) };
}
export function stepWalkers(Wk, dt, t) {
  for (const [list, buf] of [[Wk.peds, Wk.pInst], [Wk.bikes, Wk.bInst]]) {
    for (let i = 0; i < list.length; i++) {
      const w = list[i], l = w.l;
      w.s += w.v * dt * w.dir; if (w.s > l.L) { w.s = l.L; w.dir = -1; } if (w.s < 0) { w.s = 0; w.dir = 1; }
      let k = 1; while (k < l.cum.length - 1 && l.cum[k] < w.s) k++;
      const a = l.r.pts[k - 1], q = l.r.pts[k], seg = (l.cum[k] - l.cum[k - 1]) || 1, f = (w.s - l.cum[k - 1]) / seg;
      const dx = (q[0] - a[0]) / seg, dz = (q[1] - a[1]) / seg;
      const o = i * 8;
      buf[o] = a[0] + (q[0] - a[0]) * f - dz * w.lat; buf[o + 2] = a[1] + (q[1] - a[1]) * f + dx * w.lat;
      buf[o + 1] = w.bike ? 0.05 : 0.04 + Math.abs(Math.sin(t * 7 + i)) * 0.06;
      buf[o + 3] = Math.atan2(dz * w.dir, dx * w.dir); buf[o + 4] = w.col[0]; buf[o + 5] = w.col[1]; buf[o + 6] = w.col[2]; buf[o + 7] = 1;
    }
  }
}
export function buildTraffic(osm, bridges) {
  const lines = [];
  for (const r of osm.roads) {
    if (!r.major && !/tertiary/.test(r.hw)) continue;
    const cum = [0];
    for (let i = 1; i < r.pts.length; i++) cum.push(cum[i - 1] + Math.hypot(r.pts[i][0] - r.pts[i - 1][0], r.pts[i][1] - r.pts[i - 1][1]));
    const L = cum[cum.length - 1]; if (L < 40) continue;
    lines.push({ r, cum, L, ribbon: !!r._ribbon, w: /motorway|trunk/.test(r.hw) ? 5 : 3 });
  }
  const weights = lines.map(l => l.L * (l.r.major ? 1 : 0.35));
  const total = weights.reduce((a, b) => a + b, 0);
  const N = Math.min(4500, Math.floor(total / 40));
  const cars = [];
  for (let c = 0; c < N; c++) {
    let t = Math.random() * total, k = 0; while (k < lines.length - 1 && t > weights[k]) { t -= weights[k]; k++; }
    const l = lines[k];
    const dir = l.r.oneway ? 1 : (Math.random() < 0.5 ? 1 : -1);
    const lane = l.r.oneway ? (Math.random() - 0.5) * 2 * l.w * 0.6 : l.w * (0.6 + Math.random() * 0.6);
    const h = Math.random(), bus = l.r.major && h < 0.07;
    const PAL = [[0.92, 0.92, 0.92], [0.92, 0.92, 0.92], [0.07, 0.07, 0.08], [0.62, 0.63, 0.65], [0.35, 0.36, 0.38], [0.60, 0.08, 0.06], [0.10, 0.15, 0.30], [0.80, 0.78, 0.72]];
    const col = bus ? [0.18, 0.55, 0.34] : h < 0.22 ? [0.16, 0.36, 0.78] : PAL[(Math.random() * PAL.length) | 0];
    cars.push({ l, s: Math.random() * l.L, dir, lane, v: (l.r.major ? 14 : 9) * (0.7 + Math.random() * 0.6) * (bus ? 0.75 : 1), hue: h, col, len: bus ? 2.6 : 1 });
  }
  return { cars, buf: new Float32Array(cars.length * 14), inst: new Float32Array(cars.length * 8), hAt: bridges.hAt };
}
export function stepTraffic(T, dt, night) {
  const b = T.buf;
  for (let i = 0; i < T.cars.length; i++) {
    const c = T.cars[i], l = c.l;
    c.s += c.v * dt * c.dir;
    if (c.s > l.L) c.s -= l.L; if (c.s < 0) c.s += l.L;
    let k = 1; while (k < l.cum.length - 1 && l.cum[k] < c.s) k++;
    const a = l.r.pts[k - 1], q = l.r.pts[k], seg = (l.cum[k] - l.cum[k - 1]) || 1, f = (c.s - l.cum[k - 1]) / seg;
    const dx = (q[0] - a[0]) / seg, dz = (q[1] - a[1]) / seg, side = c.dir > 0 ? 1 : -1;
    const x = a[0] + (q[0] - a[0]) * f - dz * c.lane * side, z = a[1] + (q[1] - a[1]) * f + dx * c.lane * side;
    const y = (l.ribbon ? T.hAt(c.s, l.L) : 0);
    const fx = dx * c.dir, fz = dz * c.dir, half = 2.2 * c.len;
    const I = T.inst, j = i * 8;
    I[j] = x; I[j + 1] = y + 0.02; I[j + 2] = z; I[j + 3] = Math.atan2(fz, fx); I[j + 4] = c.col[0]; I[j + 5] = c.col[1]; I[j + 6] = c.col[2]; I[j + 7] = c.len;
    const o = i * 14;
    b[o] = x + fx * half; b[o + 1] = y + 0.8; b[o + 2] = z + fz * half; b[o + 3] = 2.4; b[o + 4] = 2.2; b[o + 5] = 1.8; b[o + 6] = night ? 4.5 : 0;
    b[o + 7] = x - fx * half; b[o + 8] = y + 0.9; b[o + 9] = z - fz * half; b[o + 10] = 2.2; b[o + 11] = 0.2; b[o + 12] = 0.1; b[o + 13] = night ? 3.5 : 0;
  }
}

// ---- scene objects

export const TRAFFIC = { T: null, W: null, cars: null, peds: null, bikes: null, lights: null };
export function makeTraffic(osm, bridges, waterAt, scene, shadowScene) {
  const T = buildTraffic(osm, bridges), W = buildWalkers(osm, waterAt);
  TRAFFIC.T = T; TRAFFIC.W = W;
  TRAFFIC.cars = new InstDynamic({ T: templateAttrs(TPL.car, PROP_LAYOUT), src: T.inst, layout: PROP_INST, material: makeInstMaterial(2600), shadowMaterial: makeInstShadowMaterial(), shadowLayer: LATE_SHADOW, far: 2600, order: 3 }).add(scene, shadowScene);
  TRAFFIC.peds = new InstDynamic({ T: templateAttrs(TPL.person, PROP_LAYOUT), src: W.pInst, layout: PROP_INST, material: makeInstMaterial(750), far: 750, order: 3 }).add(scene);
  TRAFFIC.bikes = new InstDynamic({ T: templateAttrs(TPL.bike, PROP_LAYOUT), src: W.bInst, layout: PROP_INST, material: makeInstMaterial(750), far: 750, order: 3 }).add(scene);
  // head and tail lights: two points per car (pos3 col3 size1), drawn at night
  const g = new THREE.BufferGeometry(), ib = new THREE.InterleavedBuffer(T.buf, 7);
  g.setAttribute("position", new THREE.InterleavedBufferAttribute(ib, 3, 0)); g.setAttribute("color", new THREE.InterleavedBufferAttribute(ib, 3, 3)); g.setAttribute("size", new THREE.InterleavedBufferAttribute(ib, 1, 6));
  g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1e5);
  TRAFFIC.lights = new THREE.Points(g, makePointMaterial()); TRAFFIC.lights.frustumCulled = false; TRAFFIC.lights.renderOrder = 11;
  scene.add(TRAFFIC.lights);
  return TRAFFIC;
}
export function updateTraffic(dt, t, night, eye) {
  stepTraffic(TRAFFIC.T, dt, night);
  stepWalkers(TRAFFIC.W, dt, t);
  TRAFFIC.cars.pack(eye); TRAFFIC.peds.pack(eye); TRAFFIC.bikes.pack(eye);
  TRAFFIC.lights.visible = night && TRAFFIC.T.cars.length > 0;
  if (TRAFFIC.lights.visible) TRAFFIC.lights.geometry.attributes.position.data.needsUpdate = true;
}
