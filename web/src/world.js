/* World: coordinate helpers, the floating-island outline, hash/rng, and the geometry builder.
   Ported from the "math / floating island outline / geometry builder" sections of src/city.src.html. */
import * as THREE from "three";

export const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
export const lerp = (a, b, t) => a + (b - a) * t;
export const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
export function hash1(n) { n = Math.sin(n * 12.9898 + 4.1414) * 43758.5453; return n - Math.floor(n); }
export function rng(seed) { let s = (seed >>> 0) || 1; return () => { s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; }; }
export function ringArea(r) { let a = 0; for (let i = 0, n = r.length; i < n; i++) { const p = r[i], q = r[(i + 1) % n]; a += p[0] * q[1] - q[0] * p[1]; } return a / 2; }
export function centroid(r) { let x = 0, z = 0; for (const p of r) { x += p[0]; z += p[1]; } return [x / r.length, z / r.length]; }
export const norm3 = v => { const l = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; };
export const cross3 = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
export function vn1(x) { const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f); return lerp(hash1(i), hash1(i + 1), u); }
export function vn2(x, y) { const i = Math.floor(x), j = Math.floor(y), f = x - i, g = y - j, u = f * f * (3 - 2 * f), v = g * g * (3 - 2 * g);
  const h = (a, b) => hash1(a * 127.1 + b * 311.7); return lerp(lerp(h(i, j), h(i + 1, j), u), lerp(h(i, j + 1), h(i + 1, j + 1), u), v); }
export function wrapA(a) { while (a > Math.PI) a -= 2 * Math.PI; while (a < -Math.PI) a += 2 * Math.PI; return a; }

/* ---------------- floating island outline ----------------
   One parameter set shared by JS (isleR) and GLSL (ISLE_GLSL): edit the waves / lobe here only. */
export const ISLE = { R0: 2850, thH: 0, lobe: 3390 };
const ISLE_WAVES = [[0.05, 3, 1], [0.035, 5, 2], [0.02, 9, 0.5], [0.012, 17, 3.1]];   // [amplitude, frequency, phase]
const ISLE_LOBE_W = 0.16, ISLE_SOFT = 60;
export function initIsle(D) {
  const hk = D.landmarks.find(l => l.k === "hanking");
  if (hk) { ISLE.thH = Math.atan2(hk.c[1], hk.c[0]); ISLE.lobe = Math.hypot(hk.c[0], hk.c[1]) + 75; }
}
export function isleR(th) {
  let w = 1; for (const [a, f, p] of ISLE_WAVES) w += a * Math.sin(f * th + p);
  const b = ISLE.R0 * w;
  const d = wrapA(th - ISLE.thH), l = ISLE.lobe * Math.exp(-((d / ISLE_LOBE_W) ** 2));
  const m = Math.max(b, l); return m + ISLE_SOFT * Math.log(Math.exp((b - m) / ISLE_SOFT) + Math.exp((l - m) / ISLE_SOFT));
}
export function inIsle(x, z, margin = 0) { return Math.hypot(x, z) < isleR(Math.atan2(z, x)) - margin; }
const f = x => { const s = String(x); return s.includes(".") ? s : s + ".0"; };
// uIsle = (R0, thH, lobe)
export const ISLE_GLSL = `
float isleR(float th){
  float b = uIsle.x * (1.0${ISLE_WAVES.map(([a, k, p]) => ` + ${f(a)} * sin(${f(k)} * th + ${f(p)})`).join("")});
  float d = mod(th - uIsle.y + 3.14159265, 6.28318531) - 3.14159265;
  float l = uIsle.z * exp(-(d / ${f(ISLE_LOBE_W)}) * (d / ${f(ISLE_LOBE_W)}));
  float m = max(b, l); return m + ${f(ISLE_SOFT)} * log(exp((b - m) / ${f(ISLE_SOFT)}) + exp((l - m) / ${f(ISLE_SOFT)}));
}`;

/* ---------------- geometry builder ----------------
   vertex: pos3 nrm3 col3 uv2 bid1 mat1 = 13 floats
   mats: 0 office glass · 1 residential · 2 podium/retail · 3 concrete/roof · 4 village
         5 metal · 6 lattice shell · 7 landmark glass (LED) · 8 matte paint · 9 bridge deck */
export const VS = 13;
export class Geo {
  constructor() { this.v = []; this.i = []; this.n = 0; }
  vert(x, y, z, nx, ny, nz, c, u, w, bid, mat) { this.v.push(x, y, z, nx, ny, nz, c[0], c[1], c[2], u, w, bid, mat); return this.n++; }
  tri(a, b, c) { this.i.push(a, b, c); }
  quad(a, b, c, d) { this.i.push(a, b, c, a, c, d); }
}
// interleaved Float32 vertices → BufferGeometry with attributes position, normal, color, uv, bid, mat
export function meshGeometry(V, I) {
  const g = new THREE.BufferGeometry();
  const ib = new THREE.InterleavedBuffer(V instanceof Float32Array ? V : new Float32Array(V), VS);
  for (const [name, n, off] of [["position", 3, 0], ["normal", 3, 3], ["color", 3, 6], ["uv", 2, 9], ["bid", 1, 11], ["mat", 1, 12]])
    g.setAttribute(name, new THREE.InterleavedBufferAttribute(ib, n, off));
  g.setIndex(new THREE.BufferAttribute(I instanceof Uint32Array ? I : new Uint32Array(I), 1));
  return g;
}
export function ccw(r) { return ringArea(r) < 0 ? r.slice().reverse() : r; }
export function triangulate(pts) {
  const n = pts.length; if (n < 3) return [];
  const idx = []; for (let i = 0; i < n; i++) idx.push(i);
  if (ringArea(pts) < 0) idx.reverse();
  const tris = [];
  const cross = (a, b, c) => (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
  const inside = (p, a, b, c) => cross(a, b, p) >= 0 && cross(b, c, p) >= 0 && cross(c, a, p) >= 0;
  let guard = 0, i = 0;
  while (idx.length > 3 && guard < n * n) {
    guard++;
    const m = idx.length, i0 = idx[(i + m - 1) % m], i1 = idx[i % m], i2 = idx[(i + 1) % m];
    const a = pts[i0], b = pts[i1], c = pts[i2];
    let ear = cross(a, b, c) > 1e-9;
    if (ear) for (let j = 0; j < m; j++) { const v = idx[j]; if (v === i0 || v === i1 || v === i2) continue; if (inside(pts[v], a, b, c)) { ear = false; break; } }
    if (ear) { tris.push(i0, i1, i2); idx.splice(i % m, 1); i = Math.max(0, i - 1); guard = 0; }
    else i = (i + 1) % idx.length;
    if (guard >= idx.length * 2 + 5) { for (let j = 1; j + 1 < idx.length; j++) tris.push(idx[0], idx[j], idx[j + 1]); return tris; }
  }
  if (idx.length === 3) tris.push(idx[0], idx[1], idx[2]);
  return tris;
}
// walls between ring A at y0 and ring B at y1 (same vertex count), optional cap on top
export function frustum(g, A, B, y0, y1, col, mat, bid, o = {}) {
  A = A.slice(); B = B.slice();
  if (ringArea(A) < 0) { A.reverse(); B.reverse(); }
  const n = A.length;
  let per = o.u0 || 0;
  const smoothN = o.smooth;
  const en = [];
  for (let i = 0; i < n; i++) {
    const a = A[i], b = A[(i + 1) % n], ta = B[i];
    const e1 = [b[0] - a[0], 0, b[1] - a[1]], e2 = [ta[0] - a[0], y1 - y0, ta[1] - a[1]];
    let nn = norm3(cross3(e2, e1));
    const out = [e1[2], 0, -e1[0]];
    if (nn[0] * out[0] + nn[2] * out[2] < 0) nn = [-nn[0], -nn[1], -nn[2]];
    en.push(nn);
  }
  for (let i = 0; i < n; i++) {
    const a = A[i], b = A[(i + 1) % n], ta = B[i], tb = B[(i + 1) % n];
    const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
    let na = en[i], nb = en[i];
    if (smoothN) { const p = en[(i + n - 1) % n], q = en[(i + 1) % n]; na = norm3([p[0] + en[i][0], p[1] + en[i][1], p[2] + en[i][2]]); nb = norm3([q[0] + en[i][0], q[1] + en[i][1], q[2] + en[i][2]]); }
    const u0 = o.uFix ? o.uFix * i / n : per, u1 = o.uFix ? o.uFix * (i + 1) / n : per + len;
    const v0 = g.vert(a[0], y0, a[1], na[0], na[1], na[2], col, u0, y0, bid, mat);
    const v1 = g.vert(b[0], y0, b[1], nb[0], nb[1], nb[2], col, u1, y0, bid, mat);
    const v2 = g.vert(tb[0], y1, tb[1], nb[0], nb[1], nb[2], col, u1, y1, bid, mat);
    const v3 = g.vert(ta[0], y1, ta[1], na[0], na[1], na[2], col, u0, y1, bid, mat);
    g.quad(v0, v1, v2, v3);
    per += len;
  }
  if (o.cap !== false && Math.abs(ringArea(B)) > 0.5) {
    const rc = o.capCol || col.map(x => x * 0.8);
    const base = g.n;
    for (const p of B) g.vert(p[0], y1, p[1], 0, 1, 0, rc, -1, y1, bid, o.capMat != null ? o.capMat : mat);
    for (const k of triangulate(B)) g.i.push(base + k);
  }
  return per;
}
export const prism = (g, R, y0, y1, col, mat, bid, o) => frustum(g, R, R, y0, y1, col, mat, bid, o);
export function boxAt(g, cx, cz, w, d, ang, y0, y1, col, mat, bid) { prism(g, rectRing(cx, cz, w, d, ang), y0, y1, col, mat, bid); }
export function scaleRing(R, s, cx, cz, dx = 0, dz = 0) { return R.map(p => [cx + (p[0] - cx) * s + dx, cz + (p[1] - cz) * s + dz]); }

// ring shapes in world space
export function xfRing(loc, cx, cz, ang) { const c = Math.cos(ang), s = Math.sin(ang); return loc.map(([u, v]) => [cx + c * u - s * v, cz + s * u + c * v]); }
export function rectRing(cx, cz, w, d, ang) { return xfRing([[-w / 2, -d / 2], [w / 2, -d / 2], [w / 2, d / 2], [-w / 2, d / 2]], cx, cz, ang); }
export function chamferRing(cx, cz, w, d, ang, k) {
  const cw = Math.min(w, d) * k, a = w / 2, b = d / 2;
  return xfRing([[-a + cw, -b], [a - cw, -b], [a, -b + cw], [a, b - cw], [a - cw, b], [-a + cw, b], [-a, b - cw], [-a, -b + cw]], cx, cz, ang);
}
export function superRing(cx, cz, w, d, ang, n = 4, seg = 24) {
  const L = [];
  for (let i = 0; i < seg; i++) { const t = i / seg * Math.PI * 2, c = Math.cos(t), s = Math.sin(t); L.push([w / 2 * Math.sign(c) * Math.pow(Math.abs(c), 2 / n), d / 2 * Math.sign(s) * Math.pow(Math.abs(s), 2 / n)]); }
  return xfRing(L, cx, cz, ang);
}
export function circleRing(cx, cz, r, seg) { const L = []; for (let i = 0; i < seg; i++) { const t = i / seg * Math.PI * 2; L.push([cx + Math.cos(t) * r, cz + Math.sin(t) * r]); } return L; }
export function crossRing(cx, cz, w, d, ang, k) {
  const a = w / 2, b = d / 2, p = w * k / 2, q = d * k / 2;
  return xfRing([[-p, -b], [p, -b], [p, -q], [a, -q], [a, q], [p, q], [p, b], [-p, b], [-p, q], [-a, q], [-a, -q], [-p, -q]], cx, cz, ang);
}
export function lRing(cx, cz, w, d, ang, k) {
  const a = w / 2, b = d / 2, sx = -a + w * k, sz = -b + d * k;
  return xfRing([[-a, -b], [a, -b], [a, sz], [sx, sz], [sx, b], [-a, b]], cx, cz, ang);
}
export function gableRoof(g, cx, cz, w, d, ang, y0, rh, col, bid) {
  const c = Math.cos(ang), s = Math.sin(ang), P = (u, v, y) => [cx + c * u - s * v, y, cz + s * u + c * v];
  const a = w / 2, b = d / 2;
  const pts = [P(-a, -b, y0), P(a, -b, y0), P(a, 0, y0 + rh), P(-a, 0, y0 + rh), P(a, b, y0), P(-a, b, y0)];
  const face = (i0, i1, i2, i3) => {
    const p0 = pts[i0], p1 = pts[i1], p3 = pts[i3];
    let n = norm3(cross3([p3[0] - p0[0], p3[1] - p0[1], p3[2] - p0[2]], [p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]]));
    if (n[1] < 0) n = n.map(x => -x);
    const vs = [i0, i1, i2, i3].map(k => g.vert(pts[k][0], pts[k][1], pts[k][2], n[0], n[1], n[2], col, -1, pts[k][1], bid, 3));
    g.quad(vs[0], vs[1], vs[2], vs[3]);
  };
  face(0, 1, 2, 3); face(5, 4, 2, 3);
  for (const [i0, i1, i2, sg] of [[0, 3, 5, -1], [1, 2, 4, 1]]) {
    const n = [c * sg, 0, s * sg];
    const vs = [i0, i1, i2].map(k => g.vert(pts[k][0], pts[k][1], pts[k][2], n[0], n[1], n[2], col.map(x => x * 1.05), -1, pts[k][1], bid, 3));
    g.tri(vs[0], vs[1], vs[2]);
  }
}
export function shell(g, cx, cz, a, b, ang, h, col, mat, bid, latN = 10, seg = 48) {
  const c = Math.cos(ang), s = Math.sin(ang);
  const rows = [];
  for (let i = 0; i <= latN; i++) {
    const phi = i / latN * Math.PI / 2, rs = Math.cos(phi), y = Math.sin(phi) * h;
    const row = [];
    for (let j = 0; j <= seg; j++) {
      const t = j / seg * Math.PI * 2, lu = Math.cos(t) * a * rs, lv = Math.sin(t) * b * rs;
      const nu = Math.cos(t) * rs / a, nv = Math.sin(t) * rs / b, ny = Math.sin(phi) / h;
      const nn = norm3([c * nu - s * nv, ny, s * nu + c * nv]);
      const u = t * (a + b) / 2, w = phi * (a + b) / 2 * 0.9;
      row.push(g.vert(cx + c * lu - s * lv, y, cz + s * lu + c * lv, nn[0], nn[1], nn[2], col, u, w, bid, mat));
    }
    rows.push(row);
  }
  for (let i = 0; i < latN; i++) for (let j = 0; j < seg; j++) g.quad(rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]);
}
