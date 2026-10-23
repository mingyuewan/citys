/* Aerial actors and night lights: airliners, helicopters, egrets, delivery drones, tower cranes, boats, hot-air
   balloons, the airship, sky lanterns, traffic-signal / bus-stop / street lamps, warning beacons, the drone light
   show, landmark searchlights. initAir / updateAir are verbatim from src/city.src.html; what they draw goes through
   the helpers below: emit() places a pooled model per template by its transform (the old engine rebuilt every
   vertex each frame), dynVert() still writes the few procedural triangles (egrets, wakes), light() / beam() fill
   the point and beam buffers of which only the used part is uploaded. */
import * as THREE from "three";
import { Geo, VS, rng, lerp, clamp, norm3, cross3, inIsle, meshGeometry } from "./world.js";
import { TPL, tplNew, tplBox } from "./templates.js";
import { roofSpots, CONSTRUCT, beacons, LM_TOPS } from "./buildings.js";
import { SIGLIGHTS, BUSLIGHTS, LAMPS } from "./roads.js";
import { makeModelMaterial, makeModelShadowMaterial } from "./materials/building.js";
import { makePointMaterial, makeBeamMaterial } from "./materials/fx.js";

let D = null, waterAt = null;
const S = { get waterAt() { return waterAt; } };   // (initAir reads S.waterAt)

/* ---------------- drawing helpers ---------------- */
const G = { scene: null, shadow: null, mat: null, smat: null, pool: new Map(), used: new Map(), dyn: null, lights: null, beams: null };
function tplGeometry(t) {
  const g = new Geo();
  for (let k = 0; k < t.p.length; k++) { const p = t.p[k], n = t.n[k]; g.vert(p[0], p[1], p[2], n[0], n[1], n[2], t.c[k], -3, 0, -1, t.m[k]); }
  g.i = t.i.slice();
  return meshGeometry(new Float32Array(g.v), new Uint32Array(g.i));
}
// place the next model of template t: page rotation order (roll about x, pitch about z, then yaw about −y)
export function emit(t, pos, yaw, pitch, roll, scale = 1) {
  let list = G.pool.get(t); if (!list) G.pool.set(t, list = []);
  const k = G.used.get(t) || 0; G.used.set(t, k + 1);
  if (k === list.length) {
    const geo = tplGeometry(t), m = new THREE.Mesh(geo, G.mat), s = new THREE.Mesh(geo, G.smat);
    m.frustumCulled = s.frustumCulled = false; m.renderOrder = 4;
    G.scene.add(m); G.shadow.add(s); list.push([m, s]);
  }
  const [m, s] = list[k];
  m.position.set(pos[0], pos[1], pos[2]); m.rotation.set(roll, -yaw, pitch, "YZX"); m.scale.setScalar(scale);
  s.position.copy(m.position); s.quaternion.copy(m.quaternion); s.scale.copy(m.scale); m.visible = s.visible = true;
}
const DYN = { v: new Float32Array(4096 * VS), i: new Uint32Array(8192), nv: 0, ni: 0 };
function dynReset() { DYN.nv = 0; DYN.ni = 0; for (const k of G.used.keys()) G.used.set(k, 0); }
function dynVert(x, y, z, nx, ny, nz, c, mat) { if (DYN.nv >= 4096) return 0; const o = DYN.nv * VS, v = DYN.v; v[o] = x; v[o + 1] = y; v[o + 2] = z; v[o + 3] = nx; v[o + 4] = ny; v[o + 5] = nz; v[o + 6] = c[0]; v[o + 7] = c[1]; v[o + 8] = c[2]; v[o + 9] = -3; v[o + 10] = 0; v[o + 11] = -1; v[o + 12] = mat; return DYN.nv++; }
// hide the pooled models not placed this frame, upload the used part of the dynamic buffers
function dynFinish() {
  for (const [t, list] of G.pool) { const k = G.used.get(t) || 0; for (let j = k; j < list.length; j++) list[j][0].visible = list[j][1].visible = false; }
  const g = G.dyn.geometry;
  g.index.clearUpdateRanges(); g.index.addUpdateRange(0, DYN.ni); g.index.needsUpdate = true;
  const vb = g.attributes.position.data; vb.clearUpdateRanges(); vb.addUpdateRange(0, DYN.nv * VS); vb.needsUpdate = true;
  g.setDrawRange(0, DYN.ni); G.dyn.visible = DYN.ni > 0;
  const lg = G.lights.geometry, lb = lg.attributes.position.data; lb.clearUpdateRanges(); lb.addUpdateRange(0, AIR.nl * 7); lb.needsUpdate = true;
  lg.setDrawRange(0, AIR.nl); G.lights.visible = AIR.nl > 0;
  const bg = G.beams.geometry, bb = bg.attributes.position.data; bb.clearUpdateRanges(); bb.addUpdateRange(0, AIR.nb * 30); bb.needsUpdate = true;
  bg.setDrawRange(0, AIR.nb * 6); G.beams.visible = AIR.nb > 0;
}

export const AIR = { planes: [], helis: [], flocks: [], quads: [], show: null, lights: new Float32Array(20000 * 7), nl: 0, beams: new Float32Array(400 * 5 * 6), nb: 0 };
function light(x, y, z, r, g, b, size) { const o = AIR.nl * 7, L = AIR.lights; if (AIR.nl >= 20000) return; L[o] = x; L[o + 1] = y; L[o + 2] = z; L[o + 3] = r; L[o + 4] = g; L[o + 5] = b; L[o + 6] = size; AIR.nl++; }
export function initAir(osm, data, water) {
  D = data; waterAt = water;
  AIR.planes = [
    { a: [11000, 1500, 8000], b: [-11000, 700, -7500], T: 260, ph: 0.0, name: "进港航班" },
    { a: [-11000, -700, -1500], b: [11000, 1300, 5500], T: 240, ph: 0.45, name: "出港航班" },
    { a: [9000, 2100, -8000], b: [-10000, 1500, 3000], T: 280, ph: 0.75, name: "过境航班" }
  ];
  const cr = D.landmarks.find(l => l.k === "bamboo") || { c: [0, 0] };
  AIR.helis = [
    { type: "orbit", c: [cr.c[0], cr.c[1]], r: 650, y: 310, w: 0.05, ph: 0 },
    { type: "orbit", c: [-600, -1200], r: 900, y: 240, w: -0.035, ph: 2 },
    { type: "line", a: [1800, 160, -400], b: [900, 200, 2600], T: 70, ph: 0.3 }
  ];
  AIR.flocks = [
    { c: [1700, 1200], A: [700, 500], y: 45, w: 0.045, n: 18, ph: 0 },
    { c: [600, 900], A: [500, 300], y: 70, w: -0.05, n: 14, ph: 2 },
    { c: [2300, -200], A: [600, 600], y: 35, w: 0.035, n: 22, ph: 4 }
  ];
  // delivery drones between rooftops near the centre
  const spots = roofSpots.filter(p => Math.hypot(p[0] - 300, p[2]) < 1900);
  const R = rng(77);
  for (let i = 0; i < 14 && spots.length > 4; i++) {
    const q = { spots, from: spots[(R() * spots.length) | 0], to: spots[(R() * spots.length) | 0], t: R() * 30, dur: 40, R };
    planQuad(q); AIR.quads.push(q);
  }
  // tower cranes on CBD / tech-park construction sites
  AIR.cranes = [];
  const RC = rng(321);
  const cand = CONSTRUCT.filter(c => inIsle(c.x, c.z, 80));
  for (let k = 0; k < cand.length && AIR.cranes.length < 16; k++) {
    const c = cand[k], ux = Math.cos(c.ang), uz = Math.sin(c.ang);
    const x = c.x + ux * (c.w / 2 + 7), z = c.z + uz * (c.w / 2 + 7), H = c.h + 22 + RC() * 25;
    const mast = tplNew(); tplBox(mast, 0, H / 2, 0, 2.2, H, 2.2, [0.92, 0.70, 0.10], 8);
    for (let y = 8; y < H - 4; y += 8) tplBox(mast, 0, y, 0, 2.5, 0.35, 2.5, [0.80, 0.60, 0.08], 8);
    AIR.cranes.push({ x, z, H, mast, yaw0: RC() * 6.28, w: (RC() < 0.5 ? -1 : 1) * (0.03 + RC() * 0.04), ph: RC() * 6 });
  }
  // boats on the bay
  AIR.boats = [];
  const RB = rng(555), types = ["ferry", "speed", "cargo", "sail", "speed", "ferry", "sail", "speed", "cargo", "sail"];
  for (let tries = 0; tries < 400 && AIR.boats.length < 10; tries++) {
    const th = RB() * Math.PI * 2, rr = RB() * 2700, cx = Math.cos(th) * rr, cz = Math.sin(th) * rr;
    const rx = 140 + RB() * 380, rz = 80 + RB() * 260, rot = RB() * 3.14;
    let ok = true;
    for (let k = 0; k < 24 && ok; k++) {
      const a = k / 24 * Math.PI * 2, lx = Math.cos(a) * (rx + 60), lz = Math.sin(a) * (rz + 60);
      const x = cx + lx * Math.cos(rot) - lz * Math.sin(rot), z = cz + lx * Math.sin(rot) + lz * Math.cos(rot);
      ok = S.waterAt(x, z) && inIsle(x, z, 220);
    }
    if (!ok) continue;
    const type = types[AIR.boats.length];
    AIR.boats.push({ type, cx, cz, rx, rz, rot, w: (RB() < 0.5 ? -1 : 1) * ({ ferry: 7, speed: 16, cargo: 4.5, sail: 3.5 }[type]) / ((rx + rz) / 2), ph: RB() * 6.28, L: { ferry: 42, speed: 10, cargo: 66, sail: 12 }[type] });
  }
  // hot-air balloons, an airship and sky lanterns
  const RBl = rng(2468);
  AIR.balloons = TPL.balloons.map((tp, i) => ({ tp, c: [(RBl() - 0.5) * 7000, (RBl() - 0.5) * 7000], r: 600 + RBl() * 1600, y: 380 + RBl() * 700, w: (RBl() < 0.5 ? -1 : 1) * (0.006 + RBl() * 0.008), ph: RBl() * 6.28, bob: RBl() * 6 }));
  AIR.blimp = { r: 3900, y: 620, w: 0.012, ph: 1.2 };
  const pf = D.palms.length ? D.palms : D.trees;
  AIR.lanterns = Array.from({ length: 220 }, (_, i) => { const k = (Math.floor(RBl() * pf.length / 2)) * 2; return { x0: pf[k], z0: pf[k + 1], t0: RBl() * 600, vy: 1.4 + RBl() * 1.2, dx: (RBl() - 0.3) * 0.8, dz: (RBl() - 0.3) * 0.8, ph: RBl() * 6 }; }).filter(L => inIsle(L.x0, L.z0, 20));
  // drone show over the bay
  AIR.show = initShow();
}
function planQuad(q) {
  q.from = q.to; let to; let tries = 0;
  do { to = q.spots[(q.R() * q.spots.length) | 0]; tries++; } while ((Math.hypot(to[0] - q.from[0], to[2] - q.from[2]) < 300 || Math.hypot(to[0] - q.from[0], to[2] - q.from[2]) > 1400) && tries < 30);
  q.to = to; q.cruise = Math.max(q.from[1], to[1]) + 40; q.t = 0;
  const L = Math.hypot(to[0] - q.from[0], to[2] - q.from[2]);
  q.climb = (q.cruise - q.from[1]) / 5; q.descend = (q.cruise - to[1]) / 5; q.travel = L / 16; q.dur = q.climb + q.travel + q.descend + 4;
}
export function quadPos(q, t) {
  const f = q.from, to = q.to;
  if (t < q.climb) return [f[0], f[1] + (q.cruise - f[1]) * (t / q.climb), f[2]];
  t -= q.climb;
  if (t < q.travel) { const k = t / q.travel, e = k * k * (3 - 2 * k); return [lerp(f[0], to[0], e), q.cruise + Math.sin(k * Math.PI) * 10, lerp(f[2], to[2], e)]; }
  t -= q.travel;
  if (t < q.descend) return [to[0], q.cruise - (q.cruise - to[1]) * (t / q.descend), to[2]];
  return [to[0], to[1], to[2]];
}

/* drone light show */
function sampleText(txt, N, wMeters, font) {
  const cv = document.createElement("canvas"); cv.width = 520; cv.height = 180;
  const g = cv.getContext("2d"); g.fillStyle = "#fff"; g.textAlign = "center"; g.textBaseline = "middle";
  g.font = font; g.fillText(txt, 260, 92);
  const d = g.getImageData(0, 0, 520, 180).data, pts = [];
  for (let y = 0; y < 180; y += 3) for (let x = 0; x < 520; x += 3) if (d[(y * 520 + x) * 4 + 3] > 128) pts.push([x, y]);
  const out = [], R = rng(9);
  if (!pts.length) return null;
  for (let i = 0; i < N; i++) { const p = pts[(i * pts.length / N) | 0] || pts[(R() * pts.length) | 0]; out.push([(p[0] - 260) / 520 * wMeters, (90 - p[1]) / 520 * wMeters, (R() - 0.5) * 4]); }
  return out;
}
function initShow() {
  const N = 900;
  const anchorLm = [1750, 1250];
  const toCity = norm3([-anchorLm[0], 0, -anchorLm[1]]);          // view direction city → anchor is the opposite
  const f = norm3([anchorLm[0], 0, anchorLm[1]]);
  const right = norm3(cross3(f, [0, 1, 0]));
  const fonts = '900 150px "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif';
  const F = [];
  const R = rng(5);
  // 0: launch grid on the water
  F.push({ pts: Array.from({ length: N }, (_, i) => [((i % 45) - 22) * 7, -150 + 0.5, (Math.floor(i / 45) - 10) * 7]), flat: true, col: () => [0.3, 0.5, 1.0] });
  const t1 = sampleText("深圳湾", N, 430, fonts);
  if (t1) F.push({ pts: t1, col: (i, p) => [1.0, 0.85 + 0.1 * Math.sin(p[0] * 0.02), 0.55] });
  const heart = []; for (let i = 0; i < N; i++) { const t = i / N * Math.PI * 2, k = i % 3 === 0 ? 1 : 0.55 + R() * 0.45; heart.push([16 * Math.pow(Math.sin(t), 3) * 9 * k, (13 * Math.cos(t) - 5 * Math.cos(2 * t) - 2 * Math.cos(3 * t) - Math.cos(4 * t)) * 9 * k + 20, (R() - 0.5) * 8]); }
  F.push({ pts: heart, col: () => [1.0, 0.25, 0.42] });
  const sph = []; for (let i = 0; i < N; i++) { const y = 1 - (i + 0.5) / N * 2, r = Math.sqrt(1 - y * y), th = i * 2.399963; sph.push([Math.cos(th) * r * 110, y * 110 + 10, Math.sin(th) * r * 110]); }
  F.push({ pts: sph, spin: true, col: (i, p) => { const h = (p[1] + 110) / 220; return [0.3 + 0.7 * h, 0.4 * (1 - h) + 0.2, 1.0]; } });
  const t2 = sampleText("2026", N, 360, '900 160px "JetBrains Mono", "Noto Sans SC", monospace');
  if (t2) F.push({ pts: t2, col: (i, p) => [0.35, 0.95, 1.0] });
  const flw = []; for (let i = 0; i < N; i++) { const t = i / N * Math.PI * 2 * 3, r = 140 * Math.abs(Math.cos(3.5 * t)) * (0.4 + 0.6 * (i % 4) / 3); flw.push([Math.cos(t) * r, Math.sin(t) * r + 10, (R() - 0.5) * 10]); }
  F.push({ pts: flw, col: (i, p) => { const h = Math.atan2(p[1], p[0]) / (Math.PI * 2) + 0.5; return [0.5 + 0.5 * Math.cos(6.28 * h), 0.5 + 0.5 * Math.cos(6.28 * (h - 0.33)), 0.5 + 0.5 * Math.cos(6.28 * (h - 0.66))]; } });
  for (const fm of F) fm.cols = fm.pts.map((p, i) => fm.col(i, p));
  const delay = Array.from({ length: N }, () => R() * 1.2);
  return { N, F, anchor: [anchorLm[0], 260, anchorLm[1]], right, f, delay, t: 0, toCity };
}
function showWorld(S0, p, spin, t) {
  let [u, v, w] = p;
  if (spin) { const a = t * 0.5, c = Math.cos(a), s = Math.sin(a); const u2 = u * c - w * s; w = u * s + w * c; u = u2; }
  const A = S0.anchor;
  return [A[0] + S0.right[0] * u + S0.f[0] * w, A[1] + v, A[2] + S0.right[2] * u + S0.f[2] * w];
}

// ---- per frame
export function updateAir(t, dt, L, eye) {
  dynReset(); AIR.nl = 0; AIR.nb = 0;
  const night = L.night, blink = (ph, rate = 1.1) => (Math.sin((t + ph) * rate * Math.PI * 2) > 0.92 ? 1 : 0);
  const navK = 0.4 + night * 1.6;
  // planes
  AIR.planes.forEach((p, i) => {
    const u = ((t / p.T + p.ph) % 1);
    const pos = [lerp(p.a[0], p.b[0], u), lerp(p.a[1], p.b[1], u), lerp(p.a[2], p.b[2], u)];
    const d = [p.b[0] - p.a[0], p.b[1] - p.a[1], p.b[2] - p.a[2]];
    const yaw = Math.atan2(d[2], d[0]), pitch = Math.atan2(d[1], Math.hypot(d[0], d[2]));
    p.pos = pos; p.dir = norm3(d);
    emit(TPL.jet, pos, yaw, pitch, 0, 1);
    const side = [-Math.sin(yaw), 0, Math.cos(yaw)], fwd = [Math.cos(yaw), 0, Math.sin(yaw)];
    const at = (f, s, up) => [pos[0] + fwd[0] * f + side[0] * s, pos[1] + up, pos[2] + fwd[2] * f + side[2] * s];
    let q = at(-3, -17.5, 1.2); light(q[0], q[1], q[2], 3 * navK, 0.15, 0.1, 9);         // left wingtip red
    q = at(-3, 17.5, 1.2); light(q[0], q[1], q[2], 0.1, 3 * navK, 0.4, 9);               // right wingtip green
    if (blink(i * 0.3, 1.0)) { q = at(-24, 0, 2); light(q[0], q[1], q[2], 9, 9, 9, 22); q = at(-3, 17.5, 1); light(q[0], q[1], q[2], 9, 9, 9, 18); q = at(-3, -17.5, 1); light(q[0], q[1], q[2], 9, 9, 9, 18); }
    if (blink(i * 0.7 + 0.5, 0.8)) { q = at(0, 0, 2.6); light(q[0], q[1], q[2], 6, 0.4, 0.2, 14); }
    if (night > 0.3 && p.b[1] < p.a[1]) { q = at(19, 0, -1); light(q[0], q[1], q[2], 6 * night, 6 * night, 5 * night, 30); }
  });
  // helicopters
  AIR.helis.forEach((h, i) => {
    let pos, yaw, roll = 0;
    if (h.type === "orbit") {
      const a = t * h.w + h.ph; pos = [h.c[0] + Math.cos(a) * h.r, h.y + Math.sin(t * 0.3 + i) * 15, h.c[1] + Math.sin(a) * h.r];
      yaw = a + Math.sign(h.w) * Math.PI / 2; roll = -Math.sign(h.w) * 0.22;
    } else {
      const u = (t / h.T + h.ph) % 2, k = u < 1 ? u : 2 - u, e = k * k * (3 - 2 * k);
      pos = [lerp(h.a[0], h.b[0], e), lerp(h.a[1], h.b[1], e), lerp(h.a[2], h.b[2], e)];
      const dirS = u < 1 ? 1 : -1; yaw = Math.atan2((h.b[2] - h.a[2]) * dirS, (h.b[0] - h.a[0]) * dirS);
    }
    h.pos = pos; h.yaw = yaw;
    emit(TPL.heli, pos, yaw, 0.06, roll, 1.4);
    emit(TPL.rotor, [pos[0], pos[1] + 2.6 * 1.4, pos[2]], t * 22 + i, 0, 0, 1.4);
    if (blink(i * 0.4, 1.2)) light(pos[0], pos[1] - 2, pos[2], 7, 0.4, 0.2, 10);
    light(pos[0], pos[1] + 2.5, pos[2], 1.6 * navK, 0.2, 0.15, 5);
    if (night > 0.3 && i === 0) { light(pos[0] + Math.cos(yaw) * 4, pos[1] - 2.5, pos[2] + Math.sin(yaw) * 4, 3, 3, 2.6, 7); }
  });
  // egrets
  AIR.flocks.forEach((F, fi) => {
    const a = t * F.w + F.ph;
    const cx = F.c[0] + Math.sin(a) * F.A[0], cz = F.c[1] + Math.sin(a * 2 + 1) * F.A[1];
    const dx = Math.cos(a) * F.A[0] * F.w, dz = Math.cos(a * 2 + 1) * 2 * F.A[1] * F.w;
    const yaw = Math.atan2(dz, dx);
    const fwd = [Math.cos(yaw), Math.sin(yaw)], side = [-Math.sin(yaw), Math.cos(yaw)];
    F.pos = [cx, F.y, cz];
    for (let k = 0; k < F.n; k++) {
      const row = Math.ceil(k / 2), sg = k % 2 ? 1 : -1;
      const back = row * 7 + Math.sin(t * 0.7 + k) * 2, lat = sg * row * 5.5 + Math.cos(t * 0.5 + k * 1.3) * 1.5;
      const px = cx - fwd[0] * back + side[0] * lat, pz = cz - fwd[1] * back + side[1] * lat, py = F.y + Math.sin(t * 0.9 + k * 0.8) * 3 + row * 0.6;
      const flap = Math.sin(t * 6.5 + k * 0.9) * 0.6;
      const span = 3.2, body = 1.6, c = [0.97, 0.97, 0.95];
      const P0 = [px + fwd[0] * body, py, pz + fwd[1] * body], P1 = [px - fwd[0] * body, py, pz - fwd[1] * body];
      for (const s of [1, -1]) {
        const wx = px + side[0] * span * s * Math.cos(flap), wz = pz + side[1] * span * s * Math.cos(flap), wy = py + span * Math.sin(flap);
        const v0 = dynVert(P0[0], P0[1], P0[2], 0, 1, 0, c, 8), v1 = dynVert(P1[0], P1[1], P1[2], 0, 1, 0, c, 8), v2 = dynVert(wx - fwd[0] * 0.6, wy, wz - fwd[1] * 0.6, 0, 1, 0, c, 8);
        DYN.i[DYN.ni++] = v0; DYN.i[DYN.ni++] = v1; DYN.i[DYN.ni++] = v2;
      }
    }
  });
  // delivery drones
  AIR.quads.forEach((q, i) => {
    q.t += dt; if (q.t > q.dur) planQuad(q);
    const pos = quadPos(q, q.t), ahead = quadPos(q, q.t + 0.5);
    const yaw = Math.atan2(ahead[2] - pos[2], ahead[0] - pos[0]) || 0;
    q.pos = pos;
    emit(TPL.quad, pos, yaw, 0, 0, 2.2);
    if (blink(i * 0.37, 1.6)) light(pos[0], pos[1] - 1, pos[2], 0.2, 4, 0.5, 6);
    light(pos[0], pos[1] + 0.8, pos[2], 3 * navK, 0.6, 0.1, 3.5);
  });
  // tower cranes
  (AIR.cranes || []).forEach((c, i) => {
    emit(c.mast, [c.x, 0, c.z], 0, 0, 0, 1);
    const yaw = c.yaw0 + Math.sin(t * c.w + c.ph) * 1.4;
    emit(TPL.jib, [c.x, c.H, c.z], yaw, 0, 0, 1);
    const tip = [c.x + Math.cos(yaw) * 55, c.H + 2, c.z + Math.sin(yaw) * 55];
    const on = 0.5 + 0.5 * Math.sin(t * 2.4 + i);
    light(tip[0], tip[1], tip[2], (1 + 4 * night) * on, 0.15 * on, 0.08 * on, 6);
    light(c.x, c.H + 10.5, c.z, (1 + 4 * night) * on, 0.15 * on, 0.08 * on, 6);
  });
  // boats with wakes
  (AIR.boats || []).forEach((B, i) => {
    const a = t * B.w + B.ph, ca = Math.cos(B.rot), sa = Math.sin(B.rot);
    const lx = Math.cos(a) * B.rx, lz = Math.sin(a) * B.rz, tx = -Math.sin(a) * B.rx * Math.sign(B.w), tz = Math.cos(a) * B.rz * Math.sign(B.w);
    const x = B.cx + lx * ca - lz * sa, z = B.cz + lx * sa + lz * ca;
    const fx0 = tx * ca - tz * sa, fz0 = tx * sa + tz * ca, fl = Math.hypot(fx0, fz0) || 1, fx = fx0 / fl, fz = fz0 / fl;
    const yaw = Math.atan2(fz, fx);
    B.pos = [x, 1, z]; B.dir = [fx, 0, fz];
    emit(TPL[B.type], [x, 0.1, z], yaw, 0, B.type === "speed" ? 0.0 : 0, 1);
    const WC = [0.93, 0.96, 0.97], sx = x - fx * B.L / 2, sz = z - fz * B.L / 2, wl = B.L * (B.type === "speed" ? 7 : 3.5), sp = B.type === "speed" ? 0.34 : 0.26;
    for (const sg of [1, -1]) {
      const ex = sx - fx * wl + (-fz) * wl * sp * sg, ez = sz - fz * wl + fx * wl * sp * sg;
      const ox = -fz * 1.4, oz = fx * 1.4, dx = ex - sx, dz = ez - sz, dl = Math.hypot(dx, dz), px = -dz / dl * 1.8, pz = dx / dl * 1.8;
      const v0 = dynVert(sx + ox * sg, 0.3, sz + oz * sg, 0, 1, 0, WC, 8), v1 = dynVert(sx + ox * sg + px, 0.3, sz + oz * sg + pz, 0, 1, 0, WC, 8);
      const v2 = dynVert(ex + px * 2.5, 0.3, ez + pz * 2.5, 0, 1, 0, WC, 8), v3 = dynVert(ex, 0.3, ez, 0, 1, 0, WC, 8);
      DYN.i[DYN.ni++] = v0; DYN.i[DYN.ni++] = v1; DYN.i[DYN.ni++] = v2; DYN.i[DYN.ni++] = v0; DYN.i[DYN.ni++] = v2; DYN.i[DYN.ni++] = v3;
    }
    const bw = B.L * 0.12, cl = wl * 0.45;
    const q0 = dynVert(sx - fz * bw, 0.28, sz + fx * bw, 0, 1, 0, WC, 8), q1 = dynVert(sx + fz * bw, 0.28, sz - fx * bw, 0, 1, 0, WC, 8);
    const q2 = dynVert(sx - fx * cl + fz * bw * 0.4, 0.28, sz - fz * cl - fx * bw * 0.4, 0, 1, 0, WC, 8), q3 = dynVert(sx - fx * cl - fz * bw * 0.4, 0.28, sz - fz * cl + fx * bw * 0.4, 0, 1, 0, WC, 8);
    DYN.i[DYN.ni++] = q0; DYN.i[DYN.ni++] = q1; DYN.i[DYN.ni++] = q2; DYN.i[DYN.ni++] = q0; DYN.i[DYN.ni++] = q2; DYN.i[DYN.ni++] = q3;
    if (night > 0.3) {
      light(x - fz * B.L * 0.12, 3, z + fx * B.L * 0.12, 0.1, 2.5, 0.4, 3.5); light(x + fz * B.L * 0.12, 3, z - fx * B.L * 0.12, 2.5, 0.15, 0.1, 3.5);
      light(x, B.L * 0.25 + 4, z, 2.5, 2.5, 2.2, 4);
      if (B.type === "ferry") for (let k = -3; k <= 3; k++) light(x + fx * k * 4, 5.2, z + fz * k * 4, 2.0, 1.4, 0.7, 4.5);
    }
  });
  // balloons and the airship
  (AIR.balloons || []).forEach((B, i) => {
    const a = t * B.w + B.ph, x = B.c[0] + Math.cos(a) * B.r, z = B.c[1] + Math.sin(a) * B.r, y = B.y + Math.sin(t * 0.15 + B.bob) * 25;
    B.pos = [x, y, z];
    emit(B.tp, [x, y, z], t * 0.02 + i, 0, 0, 1.6);
    if (night > 0.3 && Math.sin(t * 0.7 + i * 2) > 0.6) light(x, y + 1, z, 5 * night, 2.6 * night, 0.8 * night, 22);
  });
  if (AIR.blimp) {
    const Bm = AIR.blimp, a = t * Bm.w + Bm.ph;
    const x = Math.cos(a) * Bm.r, z = Math.sin(a) * Bm.r, yaw = a + Math.PI / 2;
    Bm.pos = [x, Bm.y, z]; Bm.dir = [Math.cos(yaw), 0, Math.sin(yaw)];
    emit(TPL.blimp, Bm.pos, yaw, 0.02, 0, 1.4);
    if (blink(0.2, 0.9)) light(x - Math.cos(yaw) * 52, Bm.y + 8, z - Math.sin(yaw) * 52, 8, 8, 8, 14);
  }
  // sky lanterns rising from the waterfront at night
  if (night > 0.6) for (const Ln of (AIR.lanterns || [])) {
    const age = (t + Ln.t0) % 600, y = 5 + age * Ln.vy;
    if (y > 950) continue;
    const fl = 0.8 + 0.2 * Math.sin(t * 9 + Ln.ph);
    light(Ln.x0 + age * Ln.dx + Math.sin(t * 0.3 + Ln.ph) * 6, y, Ln.z0 + age * Ln.dz, 4.5 * fl, 2.1 * fl, 0.6 * fl, 7);
  }
  // traffic signals (two phase groups) and bus-stop light boxes
  {
    const cyc = t % 34;
    for (const sg of SIGLIGHTS) {
      const ph = sg[3] ? (cyc + 17) % 34 : cyc;
      const col = ph < 14 ? [0.1, 2.6, 0.9] : ph < 17 ? [2.8, 1.6, 0.1] : [2.8, 0.15, 0.1];
      const k = 0.6 + 1.6 * night;
      light(sg[0], sg[1], sg[2], col[0] * k, col[1] * k, col[2] * k, 2.4);
    }
    if (night > 0.3) for (const b of BUSLIGHTS) { light(b[0], b[1], b[2], 2.2 * night, 1.8 * night, 1.3 * night, 5); light(b[3], 1.4, b[4], 1.6 * night, 2.0 * night, 2.6 * night, 3.5); }
  }
  // street lights
  if (night > 0.3) for (const p of LAMPS) light(p[0], p[1], p[2], 2.4 * night, 1.45 * night, 0.62 * night, 4.2);
  // static aircraft warning beacons
  for (const b of beacons) { const on = 0.5 + 0.5 * Math.sin(t * 2.1 + b[3]); light(b[0], b[1], b[2], (1.5 + 5 * night) * on, 0.15 * on, 0.08 * on, 7); }
  // drone show (night)
  const SH = AIR.show;
  SH.active = night > 0.6;
  if (SH.active) {
    SH.t += dt;
    const hold = 9, move = 3.2, per = hold + move;
    const F = SH.F, nF = F.length - 1;
    const cyc = SH.t / per, idx = Math.floor(cyc), local = SH.t - idx * per;
    const from = idx === 0 ? F[0] : F[1 + ((idx - 1) % nF)], to = F[1 + (idx % nF)];
    for (let i = 0; i < SH.N; i++) {
      const k = clamp((local - hold * 0 - SH.delay[i]) / move, 0, 1), e = k * k * (3 - 2 * k);
      const a = showWorld(SH, from.pts[i], from.spin, SH.t), b = showWorld(SH, to.pts[i], to.spin, SH.t);
      if (from.flat) a[1] = 2;
      const ca = from.cols[i], cb = to.cols[i];
      const tw = 0.85 + 0.15 * Math.sin(t * 5 + i);
      const x = lerp(a[0], b[0], e), y = lerp(a[1], b[1], e) + Math.sin(e * Math.PI) * 30, z = lerp(a[2], b[2], e);
      light(x, y, z, lerp(ca[0], cb[0], e) * 3.2 * tw, lerp(ca[1], cb[1], e) * 3.2 * tw, lerp(ca[2], cb[2], e) * 3.2 * tw, 5);
    }
  } else SH.t = 0;
  // searchlights from landmark tops (night)
  if (night > 0.5) {
    LM_TOPS.slice(0, 6).forEach((top, i) => {
      for (let k = 0; k < 2; k++) {
        const a = t * (0.35 + i * 0.03) * (k ? -1 : 1) + i * 1.7 + k * Math.PI, tilt = 0.25 + 0.18 * Math.sin(t * 0.3 + i + k);
        const dir = [Math.cos(a) * Math.sin(tilt), Math.cos(tilt), Math.sin(a) * Math.sin(tilt)];
        beam(top, dir, 2600, eye);
      }
    });
  }
}
function beam(p0, dir, len, eye) {
  const B = AIR.beams; if (AIR.nb >= 390) return;
  const p1 = [p0[0] + dir[0] * len, p0[1] + dir[1] * len, p0[2] + dir[2] * len];
  const mid = [(p0[0] + p1[0]) / 2 - eye[0], (p0[1] + p1[1]) / 2 - eye[1], (p0[2] + p1[2]) / 2 - eye[2]];
  const side = norm3(cross3(dir, mid));
  const w0 = 3, w1 = 120;
  const v = [[p0, -w0, 0, 1, 0], [p0, w0, 0, -1, 0], [p1, w1, 1, -1, 1], [p1, -w1, 1, 1, 1]];
  const verts = v.map(([p, w, _, sx, ty]) => [p[0] + side[0] * w, p[1] + side[1] * w, p[2] + side[2] * w, sx, ty]);
  const order = [0, 1, 2, 0, 2, 3];
  let o = AIR.nb * 30;
  for (const k of order) { const q = verts[k]; B[o++] = q[0]; B[o++] = q[1]; B[o++] = q[2]; B[o++] = q[3]; B[o++] = q[4]; }
  AIR.nb++;
}

/* ---------------- scene objects ---------------- */
export function makeAir(osm, data, water, scene, shadowScene) {
  G.scene = scene; G.shadow = shadowScene; G.mat = makeModelMaterial(); G.smat = makeModelShadowMaterial();
  // egrets and boat wakes: rebuilt each frame in world space (identity transform)
  G.dyn = new THREE.Mesh(meshGeometry(DYN.v, DYN.i), G.mat); G.dyn.frustumCulled = false; G.dyn.renderOrder = 4;
  G.dyn.geometry.attributes.position.data.setUsage(THREE.DynamicDrawUsage); G.dyn.geometry.index.setUsage(THREE.DynamicDrawUsage);
  scene.add(G.dyn);
  { const g = new THREE.BufferGeometry(), ib = new THREE.InterleavedBuffer(AIR.lights, 7).setUsage(THREE.DynamicDrawUsage);
    g.setAttribute("position", new THREE.InterleavedBufferAttribute(ib, 3, 0)); g.setAttribute("color", new THREE.InterleavedBufferAttribute(ib, 3, 3)); g.setAttribute("size", new THREE.InterleavedBufferAttribute(ib, 1, 6));
    G.lights = new THREE.Points(g, makePointMaterial()); G.lights.frustumCulled = false; G.lights.renderOrder = 12; scene.add(G.lights); }
  { const g = new THREE.BufferGeometry(), ib = new THREE.InterleavedBuffer(AIR.beams, 5).setUsage(THREE.DynamicDrawUsage);
    g.setAttribute("position", new THREE.InterleavedBufferAttribute(ib, 3, 0)); g.setAttribute("bt", new THREE.InterleavedBufferAttribute(ib, 2, 3));
    G.beams = new THREE.Mesh(g, makeBeamMaterial()); G.beams.frustumCulled = false; G.beams.renderOrder = 13; scene.add(G.beams); }
  initAir(osm, data, water);
  return G;
}
// per frame, after updateAir: hide unused models, upload buffers; uPx: pixels per metre at 1 m
export function finishAir(uPx) { dynFinish(); const u = G.lights.material.uniforms; u.uPx.value = uPx; u.uAdd.value = 1; }
