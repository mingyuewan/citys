/* Road ribbons (sidewalks + carriageways with lane data for the road shader), bridges, street lamps, traffic signals,
   bus stops, parked cars, median shrubs, sports grounds / pools / car parks.
   Ported verbatim from the "road surfaces / sports grounds / bridges" sections of src/city.src.html. */
import * as THREE from "three";
import { Geo, lerp, hash1, inIsle, prism, boxAt, circleRing, meshGeometry, orient } from "./world.js";
import { InstCells, templateAttrs, PROP_LAYOUT, PROP_INST, LATE_SHADOW } from "./instancing.js";
import { makeRoadMaterials, makeInstMaterial, makeInstShadowMaterial } from "./materials/street.js";
import { TPL } from "./templates.js";

export const ROADW = { motorway: 24, trunk: 22, primary: 18, secondary: 14, tertiary: 10, motorway_link: 8, trunk_link: 8, primary_link: 7, secondary_link: 7, tertiary_link: 6, residential: 7, unclassified: 7, living_street: 6, service: 4.5 };
export const LANES = { motorway: 3, trunk: 3, primary: 2, secondary: 2, tertiary: 1, residential: 1, unclassified: 1, motorway_link: 1, trunk_link: 1, primary_link: 1, secondary_link: 1, tertiary_link: 1, living_street: 0, service: 0 };
export function buildRoadMesh(osm) {
  const roads = osm.roads.filter(r => ROADW[r.hw] && !r._ribbon);
  const key = p => Math.round(p[0] * 0.5) + "," + Math.round(p[1] * 0.5);
  const deg = new Map();
  for (const r of roads) r.pts.forEach((p, i) => { const k = key(p); deg.set(k, (deg.get(k) || 0) + (i === 0 || i === r.pts.length - 1 ? 1 : 2)); });
  const v = []; let walkN = 0;
  for (const pass of [0, 1]) {               // 0: sidewalks underneath, 1: carriageways
    if (pass === 1) walkN = v.length / 11;
    for (const r of roads) {
      const P = r.pts, n = P.length, lanes0 = LANES[r.hw];
      if (pass === 0 && !lanes0) continue;
      const hw = ROADW[r.hw] / 2 + (pass === 0 ? 3.2 : 0);
      const lanes = r.oneway ? lanes0 + (lanes0 ? 1 : 0) : lanes0;
      const cum = [0]; for (let i = 1; i < n; i++) cum.push(cum[i - 1] + Math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]));
      if (cum[n - 1] < 1) continue;
      const isJ = P.map(p => (deg.get(key(p)) || 0) >= 3);
      const pj = [], nj = [];
      let lj = -1e6; for (let i = 0; i < n; i++) { if (isJ[i]) lj = cum[i]; pj.push(cum[i] - lj); }
      lj = 1e6; for (let i = n - 1; i >= 0; i--) { if (isJ[i]) lj = cum[i]; nj[i] = lj - cum[i]; }
      const NR = [];
      for (let i = 0; i < n; i++) {
        const segN = (a, b) => { const dx = b[0] - a[0], dz = b[1] - a[1], l = Math.hypot(dx, dz) || 1; return [-dz / l, dx / l]; };
        let nn;
        if (i === 0) nn = segN(P[0], P[1]); else if (i === n - 1) nn = segN(P[n - 2], P[n - 1]);
        else { const a = segN(P[i - 1], P[i]), b = segN(P[i], P[i + 1]); let mx = a[0] + b[0], mz = a[1] + b[1]; const l = Math.hypot(mx, mz) || 1; mx /= l; mz /= l; const k = 1 / Math.max(0.5, mx * a[0] + mz * a[1]); nn = [mx * k, mz * k]; }
        NR.push(nn);
      }
      const med = pass === 1 && !r.oneway && lanes0 >= 2 ? (/^(primary|trunk)$/.test(r.hw) ? 3.2 : 2.2) : 0;
      const kind = pass === 0 ? -1 : 1 + med;
      if (pass === 1 && lanes0 >= 1 && /^(trunk|primary|secondary|tertiary)$/.test(r.hw) && cum[n - 1] > 40 && SIGNALS.length < 900 * 8) {
        for (const end of [0, n - 1]) {
          if (!isJ[end]) continue;
          const base = P[end], nb = P[end === 0 ? 1 : n - 2];
          let dx = nb[0] - base[0], dz = nb[1] - base[1]; const dl = Math.hypot(dx, dz) || 1; dx /= dl; dz /= dl;
          const nx = -dz, nz = dx, off = hw + 0.8;
          const px = base[0] + dx * 13 - nx * off, pz = base[1] + dz * 13 - nz * off;
          if (!inIsle(px, pz, 10)) continue;
          SIGNALS.push(px, 0, pz, Math.atan2(nz, nx), 0, 0, 0, 1);
          SIGLIGHTS.push([px + nx * 5.4, 6.2, pz + nz * 5.4, Math.abs(dx) > Math.abs(dz) ? 0 : 1]);
        }
      }
      if (pass === 1 && /^(primary|secondary)$/.test(r.hw) && cum[n - 1] > 220) {
        for (let d0 = 160 + hash1(P[0][0]) * 120; d0 < cum[n - 1] - 60; d0 += 430) {
          let i = 0; while (i < n - 2 && cum[i + 1] < d0) i++;
          const a = P[i], b = P[i + 1], L = cum[i + 1] - cum[i]; if (L < 1) continue;
          const f = (d0 - cum[i]) / L, ux = (b[0] - a[0]) / L, uz = (b[1] - a[1]) / L, nx = -uz, nz = ux;
          const x = a[0] + (b[0] - a[0]) * f + nx * (hw + 2.4), z = a[1] + (b[1] - a[1]) * f + nz * (hw + 2.4);
          if (!inIsle(x, z, 10)) continue;
          const hc = hash1(x + z);
          BUSSTOPS.push(x, 0, z, Math.atan2(uz, ux), 0.4 + 0.6 * hc, 0.7, 1.0 - 0.5 * hc, 1);
          BUSLIGHTS.push([x + nx * 0.6, 2.4, z + nz * 0.6, x + ux * 3.2 + nx * 0.4, z + uz * 3.2 + nz * 0.4]);
        }
      }
      if (pass === 1) {
        const djAt = (i, f) => Math.min(lerp(pj[i], pj[i + 1], f), lerp(nj[i], nj[i + 1], f));
        const wantPark = /^(residential|unclassified|service|tertiary)$/.test(r.hw);
        for (let i = 0; i + 1 < n; i++) {
          const a = P[i], b = P[i + 1], L = cum[i + 1] - cum[i]; if (L < 0.5) continue;
          const ux = (b[0] - a[0]) / L, uz = (b[1] - a[1]) / L, nx = -uz, nz = ux;
          if (med > 0) for (let t = 3.5; t < L; t += 7) { if (djAt(i, t / L) > 18 && inIsle(a[0] + ux * t, a[1] + uz * t, 10)) SHRUBS.push(a[0] + ux * t, a[1] + uz * t); }
          if (wantPark && PARKED.length < 8000 * 8) for (let t = 3.2; t < L; t += 6.4) {
            if (djAt(i, t / L) < 16) continue;
            for (const sg of (r.hw === "service" ? [1] : [1, -1])) {
              const hh = hash1(a[0] * 3.1 + a[1] * 1.7 + t * 5.3 + sg); if (hh > 0.52) continue;
              const off = hw - (r.hw === "service" ? 1.1 : 1.25), x = a[0] + ux * t + nx * off * sg, z = a[1] + uz * t + nz * off * sg;
              if (!inIsle(x, z, 8)) continue;
              const PAL = [[0.92, 0.92, 0.92], [0.07, 0.07, 0.08], [0.62, 0.63, 0.65], [0.35, 0.36, 0.38], [0.60, 0.08, 0.06], [0.10, 0.15, 0.30], [0.80, 0.78, 0.72], [0.16, 0.36, 0.78]];
              const col = PAL[Math.floor(hash1(hh * 91.7) * PAL.length)];
              PARKED.push(x, 0.02, z, Math.atan2(uz, ux) + (hh < 0.26 ? Math.PI : 0), col[0], col[1], col[2], 1);
            }
          }
        }
      }
      const V = (i, sd) => { const p = P[i], q = NR[i]; v.push(p[0] + q[0] * hw * sd, 0, p[1] + q[1] * hw * sd, hw * sd, cum[i], pj[i], nj[i], hw, lanes, r.oneway ? 1 : 0, kind); };
      for (let i = 0; i + 1 < n; i++) { V(i, -1); V(i, 1); V(i + 1, 1); V(i, -1); V(i + 1, 1); V(i + 1, -1); }
    }
  }
  const out = new Float32Array(v); out.walkN = walkN; return out;
}

export const SHRUBS = [], PARKED = [], SIGNALS = [], SIGLIGHTS = [], BUSSTOPS = [], BUSLIGHTS = [];
// ---- sports grounds, courts, pools
export function buildFeatures(D) {
  const g = new Geo();
  const DIM = { 0: [104, 68, 12], 1: [60, 40, 12], 2: [30, 17, 14], 3: [31, 16, 13], 4: [34, 18, 15], 5: [176, 100, 16], 6: [46, 32, 19] };
  let n = 0;
  for (const [k, x, z, angD] of (D.features || [])) {
    if (!inIsle(x, z, 60)) continue;
    const [L, W, mat] = DIM[k]; const a = angD * Math.PI / 180, c = Math.cos(a), s2 = Math.sin(a), y = 0.12;
    const col = [L / 200, W / 200, 0];
    const P = [[-L / 2, -W / 2], [L / 2, -W / 2], [L / 2, W / 2], [-L / 2, W / 2]].map(([u, w]) => g.vert(x + c * u - s2 * w, y, z + s2 * u + c * w, 0, 1, 0, col, u, w, -1, mat));
    g.quad(P[0], P[1], P[2], P[3]);
    if (k === 6) {   // cars in the bays
      const PAL = [[0.92, 0.92, 0.92], [0.07, 0.07, 0.08], [0.62, 0.63, 0.65], [0.35, 0.36, 0.38], [0.60, 0.08, 0.06], [0.10, 0.15, 0.30], [0.80, 0.78, 0.72], [0.16, 0.36, 0.78]];
      for (const vr of [-(W / 2 - 3.2), W / 2 - 3.2]) for (let u = -L / 2 + 1.75; u < L / 2 - 1; u += 2.5) {
        const hh = hash1(x * 0.7 + z * 1.3 + u * 3.1 + vr); if (hh > 0.72) continue;
        const col = PAL[Math.floor(hash1(hh * 77.7) * PAL.length)];
        PARKED.push(x + c * u - s2 * vr, 0.15, z + s2 * u + c * vr, a + (vr > 0 ? -Math.PI / 2 : Math.PI / 2), col[0], col[1], col[2], 1);
      }
    }
    if (k === 0 || k === 1 || k === 5) {   // goals
      const hl = k === 5 ? 50 : L / 2 - 2, gw = k === 1 ? 2.5 : 3.66;
      for (const sg of [1, -1]) boxAt(g, x + c * (hl + 0.8) * sg, z + s2 * (hl + 0.8) * sg, 1.6, gw * 2, a, 0, 2.44, [0.95, 0.95, 0.95], 8, -1);
    }
    n++;
  }
  return { V: new Float32Array(g.v), I: new Uint32Array(g.i), n };
}
export const LAMPS = [];
export function streetLights(osm) {
  const out = [];
  for (const r of osm.roads) {
    if (!/^(trunk|primary|secondary)$/.test(r.hw) || r._ribbon) continue;
    const off = ROADW[r.hw] / 2 + 1.0;
    let acc = 8 + hash1(r.pts[0][0]) * 20;
    for (let i = 0; i + 1 < r.pts.length; i++) {
      const a = r.pts[i], b = r.pts[i + 1], L = Math.hypot(b[0] - a[0], b[1] - a[1]); if (L < 0.1) continue;
      const nx = -(b[1] - a[1]) / L, nz = (b[0] - a[0]) / L;
      let t = acc;
      while (t < L) {
        const f = t / L, px = a[0] + (b[0] - a[0]) * f, pz = a[1] + (b[1] - a[1]) * f;
        for (const sg of (r.oneway ? [1] : [1, -1])) {
          const x = px + nx * off * sg, z = pz + nz * off * sg;
          if (!inIsle(x, z, 10)) continue;
          const yaw = Math.atan2(-nz * sg, -nx * sg);
          out.push(x, 0, z, yaw, 0, 0, 0, 1);
          LAMPS.push([x + Math.cos(yaw) * 2.3, 9.1, z + Math.sin(yaw) * 2.3]);
        }
        t += 38;
      }
      acc = t - L;
    }
  }
  return new Float32Array(out);
}

// ---- bridges
export function buildBridges(osm) {
  const g = new Geo();
  const lines = [];
  for (const r of osm.roads) {
    if (!r.bridge || !/^(motorway|trunk|primary)/.test(r.hw)) continue;
    let L = 0; for (let i = 1; i < r.pts.length; i++) L += Math.hypot(r.pts[i][0] - r.pts[i - 1][0], r.pts[i][1] - r.pts[i - 1][1]);
    if (L < 250) continue;
    r._ribbon = true; r._len = L; lines.push(r);
  }
  const deck = 11, ramp = 160;
  const hAt = (s, L) => deck * Math.min(1, s / ramp, (L - s) / ramp);
  const col = [0.78, 0.77, 0.74];
  for (const r of lines) {
    const w = /motorway|trunk/.test(r.hw) ? 14 : 10; let s = 0, nextPillar = ramp;
    for (let i = 0; i + 1 < r.pts.length; i++) {
      const a = r.pts[i], b = r.pts[i + 1];
      const dx = b[0] - a[0], dz = b[1] - a[1], len = Math.hypot(dx, dz); if (len < 0.01) continue;
      const px = -dz / len * w / 2, pz = dx / len * w / 2;
      const ya = hAt(s, r._len), yb = hAt(s + len, r._len);
      const q = [g.vert(a[0] + px, ya, a[1] + pz, 0, 1, 0, col, -2, 0, -1, 9), g.vert(a[0] - px, ya, a[1] - pz, 0, 1, 0, col, -2, 0, -1, 9),
                 g.vert(b[0] - px, yb, b[1] - pz, 0, 1, 0, col, -2, 0, -1, 9), g.vert(b[0] + px, yb, b[1] + pz, 0, 1, 0, col, -2, 0, -1, 9)];
      g.quad(q[0], q[1], q[2], q[3]);
      for (const sd of [1, -1]) {
        const nx = sd * px / (w / 2), nz = sd * pz / (w / 2);
        const e = [g.vert(a[0] + sd * px, ya + 1.1, a[1] + sd * pz, nx, 0, nz, col, -2, 0, -1, 3), g.vert(b[0] + sd * px, yb + 1.1, b[1] + sd * pz, nx, 0, nz, col, -2, 0, -1, 3),
                   g.vert(b[0] + sd * px, yb - 1.8, b[1] + sd * pz, nx, 0, nz, col, -2, 0, -1, 3), g.vert(a[0] + sd * px, ya - 1.8, a[1] + sd * pz, nx, 0, nz, col, -2, 0, -1, 3)];
        g.quad(e[0], e[1], e[2], e[3]);
      }
      while (nextPillar < s + len && nextPillar < r._len - ramp * 0.5) {
        const f = (nextPillar - s) / len, cx = a[0] + dx * f, cz = a[1] + dz * f, top = hAt(nextPillar, r._len) - 1.8;
        prism(g, circleRing(cx, cz, 1.6, 8), 0, top, [0.72, 0.71, 0.68], 3, -1, { cap: false });
        nextPillar += 60;
      }
      s += len;
    }
  }
  return { V: new Float32Array(g.v), I: new Uint32Array(g.i), lines, hAt };
}

// ---- scene objects

const PROP_POS = (b, k) => [b[k * 8], b[k * 8 + 1], b[k * 8 + 2]];
export const ROADS = { mesh: null, bridge: null, lamps: null, signals: null, bus: null };
// bridges must be built before (they mark their roads as ribbons, which the road mesh and the ground skip)
export function makeRoads(osm, bridges, meshMat, scene, shadowScene) {
  const rv = buildRoadMesh(osm), g = new THREE.BufferGeometry();
  const ib = new THREE.InterleavedBuffer(rv, 11);
  g.setAttribute("position", new THREE.InterleavedBufferAttribute(ib, 3, 0));
  g.setAttribute("ra", new THREE.InterleavedBufferAttribute(ib, 4, 3)); g.setAttribute("rb", new THREE.InterleavedBufferAttribute(ib, 4, 7));
  const n = rv.length / 11;
  g.addGroup(0, rv.walkN, 0); g.addGroup(rv.walkN, n - rv.walkN, 1);   // sidewalks, then carriageways
  g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1e5);
  const m = new THREE.Mesh(g, makeRoadMaterials()); m.frustumCulled = false; m.renderOrder = -3;
  scene.add(m); ROADS.mesh = m;
  if (bridges.I.length) {
    orient(bridges.V, bridges.I);
    const b = new THREE.Mesh(meshGeometry(bridges.V, bridges.I), meshMat); b.frustumCulled = false; scene.add(b); ROADS.bridge = b;
    const s = new THREE.Mesh(b.geometry, shadowScene.userData.shadowMat); s.frustumCulled = false; shadowScene.add(s);
  }
  const cells = (tpl, inst, far, shadow) => new InstCells({ T: templateAttrs(tpl, PROP_LAYOUT), inst, layout: PROP_INST, pos: PROP_POS, pad: 12,
    material: makeInstMaterial(far), shadowMaterial: shadow ? makeInstShadowMaterial() : null, shadowLayer: LATE_SHADOW, far, order: 3 }).add(scene, shadow ? shadowScene : null);
  ROADS.lamps = cells(TPL.lamp, streetLights(osm), 1800, true);
  ROADS.signals = cells(TPL.signal, new Float32Array(SIGNALS), 1500, false);
  ROADS.bus = cells(TPL.busstop, new Float32Array(BUSSTOPS), 1500, false);
  return ROADS;
}
export function updateRoads(eye) { ROADS.lamps.update(eye); ROADS.signals.update(eye); ROADS.bus.update(eye); }
