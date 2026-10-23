/* Floating island body: layered rock, hanging spires, vines, waterfall sheets (data only for now), small islets.
   Ported verbatim from the "floating island body" section of src/city.src.html. */
import { Geo, rng, lerp, clamp, vn1, vn2, wrapA, isleR, norm3, cross3, frustum, prism, boxAt, rectRing, circleRing, triangulate } from "./world.js";
import { beacons } from "./buildings.js";
import * as THREE from "three";
import { makeFallMaterial } from "./materials/fx.js";

// profile rows: [y, radial scale, kind]  kind: 0 grass lip · 1 soil · 2 rock
export const ISLE_PROF = [[0.6, 1.0, 0], [-6, 1.014, 0], [-24, 1.004, 1], [-62, 0.99, 1], [-140, 0.955, 2], [-290, 0.905, 2], [-500, 0.83, 2], [-760, 0.73, 2],
  [-1040, 0.61, 2], [-1340, 0.48, 2], [-1640, 0.35, 2], [-1940, 0.23, 2], [-2230, 0.13, 2], [-2480, 0.055, 2], [-2640, 0.0, 2]];
export function isleScaleAt(y) { // horizontal scale of the underside at height y (for camera collision)
  if (y >= 0) return 1;
  for (let k = 1; k < ISLE_PROF.length; k++) if (y >= ISLE_PROF[k][0]) { const [y0, s0] = ISLE_PROF[k - 1], [y1, s1] = ISLE_PROF[k]; return lerp(s0, s1, (y - y0) / (y1 - y0)); }
  return 0;
}
// generic rock body: rFun(th) outline radius, prof rows, water(th) flag; returns row positions
function rockBody(g, cx, cy, cz, rFun, prof, N, seed, water, jag = 1) {
  const rows = [];
  const uS = rFun(0);
  for (let k = 0; k < prof.length; k++) {
    const [py, ps, kind] = prof[k], row = [];
    for (let i = 0; i <= N; i++) {
      const th = (i % N) / N * Math.PI * 2;
      let r = rFun(th) * ps, y = py;
      if (k >= 3) {
        const m = Math.min(1, (k - 2) / 3) * jag;
        r *= 1 + 0.16 * m * (vn2(th * 7 + seed, k * 0.8) - 0.5) + 0.06 * m * (vn2(th * 23 + seed, k * 1.7) - 0.5);
        y += (vn2(th * 11 + seed, k * 0.9) - 0.5) * 70 * m * (Math.abs(py) / 1000 + 0.3);
      }
      const wet = water && water(th);
      if (wet && k === 0) y = -1.6;
      if (wet && k === 1) r *= 0.995;
      row.push([cx + Math.cos(th) * r, cy + y, cz + Math.sin(th) * r, th, kind, wet]);
    }
    rows.push(row);
  }
  const K = rows.length, idx = [];
  for (let k = 0; k < K; k++) {
    const vi = [];
    for (let i = 0; i <= N; i++) {
      const P = rows[k][i], A = rows[k][(i + 1) % (N + 1) === 0 ? 1 : i + 1], B = rows[k][i === 0 ? N - 1 : i - 1];
      const U = rows[Math.max(0, k - 1)][i], Dn = rows[Math.min(K - 1, k + 1)][i];
      const T = [A[0] - B[0], A[1] - B[1], A[2] - B[2]], V = [Dn[0] - U[0], Dn[1] - U[1], Dn[2] - U[2]];
      let n = norm3(cross3(T, V));
      const out = [Math.cos(P[3]), -0.25, Math.sin(P[3])];
      if (n[0] * out[0] + n[1] * out[1] + n[2] * out[2] < 0) n = n.map(v => -v);
      const kind = P[4], dark = 1 - 0.35 * k / K;
      const col = kind === 0 ? [0.28, 0.42, 0.20] : kind === 1 ? [0.44, 0.33, 0.23] : [0.47 * dark, 0.43 * dark, 0.38 * dark];
      const c2 = P[5] && k < 3 ? [0.22, 0.27, 0.28] : col;
      vi.push(g.vert(P[0], P[1], P[2], n[0], n[1], n[2], c2, P[3] * uS, P[1], -1, kind === 0 ? 11 : 10));
    }
    idx.push(vi);
  }
  for (let k = 0; k + 1 < K; k++) for (let i = 0; i < N; i++) g.quad(idx[k][i], idx[k][i + 1], idx[k + 1][i + 1], idx[k + 1][i]);
  return rows;
}
export const FALLS = { v: [], groups: [] };   // waterfall sheets: pos3 uv2 edge1
function addFall(rimPts, H, seedU) {
  // rimPts: [[x, y, z, outwardX, outwardZ], ...] consecutive points along an edge
  const n = rimPts.length; if (n < 2) return;
  const rows = 18, cols = [];
  let u = seedU || 0;
  for (let i = 0; i < n; i++) {
    const [x, y, z, ox, oz] = rimPts[i];
    if (i) u += Math.hypot(x - rimPts[i - 1][0], z - rimPts[i - 1][2]);
    const h = H * (0.82 + 0.36 * vn1(u * 0.004 + (seedU || 0)));
    const edge = Math.min(1, i / 3, (n - 1 - i) / 3);
    const col = [];
    for (let j = 0; j <= rows; j++) {
      const t = j / rows, out = 6 + 150 * Math.pow(t, 1.5) * (H / 1400);
      col.push([x + ox * out, y - t * h, z + oz * out, u, t, edge]);
    }
    cols.push(col);
  }
  for (let i = 0; i + 1 < n; i++) for (let j = 0; j < rows; j++) {
    const q = [cols[i][j], cols[i + 1][j], cols[i + 1][j + 1], cols[i][j], cols[i + 1][j + 1], cols[i][j + 1]];
    for (const p of q) FALLS.v.push(p[0], p[1], p[2], p[3], p[4], p[5]);
  }
  const mid = rimPts[n >> 1];
  FALLS.groups.push({ x: mid[0], y: mid[1], z: mid[2], ox: mid[3], oz: mid[4], H, w: u - (seedU || 0) });
}
export const ISLETS = [];
function makeWater(maskImg, D) {
  const cv = document.createElement("canvas"); cv.width = cv.height = 1024;
  const c2 = cv.getContext("2d"); c2.drawImage(maskImg, 0, 0, 1024, 1024);
  const md = c2.getImageData(0, 0, 1024, 1024).data;
  return (x, z) => { const i = clamp(Math.floor((x + D.R) / (2 * D.R) * 1024), 0, 1023), j = clamp(Math.floor((z + D.R) / (2 * D.R) * 1024), 0, 1023); return md[(j * 1024 + i) * 4] > 127; };
}
export function buildIsland(maskImg, D) {
  const g = new Geo();
  // water lookup from the mask
  const waterAt = makeWater(maskImg, D);
  const N = 320;
  const wet = th => { const r = isleR(th) * 0.982; return waterAt(Math.cos(th) * r, Math.sin(th) * r); };
  const rows = rockBody(g, 0, 0, 0, isleR, ISLE_PROF, N, 1.3, wet);
  // hanging rock spires under the island
  const R = rng(4242);
  for (let s = 0; s < 70; s++) {
    const k = 4 + Math.floor(R() * 8), i = Math.floor(R() * N), P = rows[k][i];
    const sc = 0.93, x = P[0] * sc, z = P[2] * sc, y = P[1] + 25, rad = 25 + R() * 90, len = 120 + R() * 480;
    frustum(g, circleRing(x, z, rad, 9), circleRing(x + (R() - 0.5) * 30, z + (R() - 0.5) * 30, rad * 0.06, 9), y, y - len, [0.40, 0.37, 0.33], 10, -1, { cap: false, smooth: true });
  }
  // vines over the lip
  for (let i = 0; i < N; i++) {
    const P = rows[1][i]; if (P[5] || R() < 0.35) continue;
    const th = P[3], ox = Math.cos(th), oz = Math.sin(th), tx = -oz, tz = ox, len = 14 + R() * 90, w = 1.2 + R() * 2.5;
    const x = P[0] + ox * 1.5, z = P[2] + oz * 1.5, col = [0.14 + R() * 0.06, 0.27 + R() * 0.08, 0.11];
    const a = g.vert(x - tx * w, P[1], z - tz * w, ox, 0, oz, col, th * 2850, P[1], -1, 11), b = g.vert(x + tx * w, P[1], z + tz * w, ox, 0, oz, col, th * 2850 + 3, P[1], -1, 11);
    const c = g.vert(x + tx * w * 0.3 + ox * 3, P[1] - len, z + tz * w * 0.3 + oz * 3, ox, 0, oz, col, th * 2850 + 3, P[1] - len, -1, 11), d = g.vert(x - tx * w * 0.3 + ox * 3, P[1] - len, z - tz * w * 0.3 + oz * 3, ox, 0, oz, col, th * 2850, P[1] - len, -1, 11);
    g.quad(a, b, c, d);
  }
  // waterfalls where the bay meets the rim
  let run = [];
  const flushRun = () => {
    if (run.length >= 3) addFall(run.map(P => [P[0], 0.2, P[2], Math.cos(P[3]), Math.sin(P[3])]), 1500, run[0][3] * 2850);
    run = [];
  };
  for (let i = 0; i <= N; i++) { const P = rows[0][i % N]; if (P[5]) run.push(P); else flushRun(); }
  flushRun();
  // small floating islets around the main island
  const RI = rng(99);
  const spots = [[0.35, 5200, 380, 360], [1.15, 6100, -260, 240], [1.95, 4700, 620, 180], [2.6, 7200, 120, 470], [3.4, 5600, -520, 300], [4.1, 4500, 260, 140], [4.85, 6600, 760, 260], [5.5, 4900, -120, 420], [6.05, 7600, 450, 200], [2.25, 8800, -700, 330]];
  for (const [a, d, y, r] of spots) {
    const cx = Math.cos(a) * d, cz = Math.sin(a) * d, seed = RI() * 50;
    const rf = th => r * (1 + 0.12 * Math.sin(3 * th + seed) + 0.07 * Math.sin(5 * th + seed * 2) + 0.04 * Math.sin(9 * th));
    const prof = [[0, 1, 0], [-4, 1.03, 0], [-0.07 * r, 1.0, 1], [-0.25 * r, 0.9, 2], [-0.55 * r, 0.72, 2], [-0.9 * r, 0.48, 2], [-1.25 * r, 0.25, 2], [-1.55 * r, 0.08, 2], [-1.7 * r, 0, 2]];
    const hasFall = r > 330;
    const fallTh = RI() * Math.PI * 2;
    const wetF = hasFall ? th => Math.abs(wrapA(th - fallTh)) < 0.16 : null;
    const rws = rockBody(g, cx, y, cz, rf, prof, 48, seed, wetF, 0.8);
    // grassy top
    const top = rws[0].slice(0, 48).map(P => [P[0], P[2]]);
    const base = g.n;
    for (const p of top) g.vert(p[0], y + 0.6, p[1], 0, 1, 0, [0.27, 0.41, 0.19], p[0], p[1], -1, 11);
    for (const k of triangulate(top)) g.i.push(base + k);
    if (hasFall) {
      const pts = rws[0].filter(P => P[5]).map(P => [P[0], y + 0.2, P[2], Math.cos(P[3]), Math.sin(P[3])]);
      addFall(pts, 650 + r, a * 100);
      // a pond feeding the fall
      boxAt(g, cx + Math.cos(fallTh) * r * 0.55, cz + Math.sin(fallTh) * r * 0.55, r * 0.5, r * 0.35, fallTh, y + 0.6, y + 0.9, [0.20, 0.36, 0.42], 5, -1);
    }
    // trees
    const tx = [], ty = [], nT = Math.floor(r * r / 650);
    for (let k = 0; k < nT; k++) { const th = RI() * Math.PI * 2, rr = Math.sqrt(RI()) * rf(th) * 0.82; tx.push(cx + Math.cos(th) * rr, cz + Math.sin(th) * rr); ty.push(y + 0.5); }
    // a pavilion or a small tower on some islets
    const kind = RI();
    if (kind < 0.35) {           // 亭 pavilion
      const px = cx, pz = cz, ang = RI() * 3;
      prism(g, rectRing(px, pz, 22, 22, ang), y + 0.6, y + 2, [0.72, 0.70, 0.66], 3, -1);
      for (const [u, v] of [[-8, -8], [8, -8], [8, 8], [-8, 8]]) { const c = Math.cos(ang), s = Math.sin(ang); prism(g, circleRing(px + c * u - s * v, pz + s * u + c * v, 0.7, 6), y + 2, y + 10, [0.55, 0.16, 0.12], 8, -1, { cap: false }); }
      frustum(g, rectRing(px, pz, 26, 26, ang), rectRing(px, pz, 3, 3, ang), y + 10, y + 17, [0.20, 0.28, 0.26], 3, -1, { capCol: [0.2, 0.28, 0.26] });
    } else if (kind < 0.6) {     // little lighthouse
      frustum(g, circleRing(cx, cz, 7, 12), circleRing(cx, cz, 4.5, 12), y + 0.6, y + 34, [0.92, 0.92, 0.9], 3, -1, { smooth: true, capCol: [0.3, 0.3, 0.32] });
      prism(g, circleRing(cx, cz, 4.2, 12), y + 34, y + 39, [0.40, 0.55, 0.62], 5, -1, { capCol: [0.6, 0.15, 0.1] });
      beacons.push([cx, y + 41, cz, RI() * 6]);
    }
    ISLETS.push({ cx, cy: y, cz, r, tx, ty, hasFall });
  }
  return { V: new Float32Array(g.v), I: new Uint32Array(g.i), waterAt };
}

// ---- waterfall sheets (pos3 uv2 edge1 per vertex, non-indexed)
export function makeFalls() {
  const g = new THREE.BufferGeometry(), ib = new THREE.InterleavedBuffer(new Float32Array(FALLS.v), 6);
  g.setAttribute("position", new THREE.InterleavedBufferAttribute(ib, 3, 0)); g.setAttribute("uv", new THREE.InterleavedBufferAttribute(ib, 2, 3)); g.setAttribute("edge", new THREE.InterleavedBufferAttribute(ib, 1, 5));
  g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1e5);
  const m = new THREE.Mesh(g, makeFallMaterial()); m.frustumCulled = false; m.renderOrder = 10;
  return m;
}
