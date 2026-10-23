/* Low-poly templates for instanced props and aerial actors (local space: x forward, y up, z right).
   Ported verbatim from the "instanced props" / "dynamic mesh" sections of src/city.src.html. */
import { norm3 } from "./world.js";

// template → interleaved [pos3 nrm3 col3 part1] (stride 10) + Uint16 indices
export function propTemplate(build) {
  const t = tplNew(); build(t);
  const v = [];
  for (let k = 0; k < t.p.length; k++) v.push(...t.p[k], ...t.n[k], ...t.c[k], t.m[k]);
  return { v: new Float32Array(v), i: new Uint16Array(t.i) };
}
export function tplNew() { return { p: [], n: [], c: [], m: [], i: [] }; }
export function tplBox(t, cx, cy, cz, sx, sy, sz, col, mat) {
  const F = [[[1, 0, 0], [[1, -1, -1], [1, 1, -1], [1, 1, 1], [1, -1, 1]]], [[-1, 0, 0], [[-1, -1, 1], [-1, 1, 1], [-1, 1, -1], [-1, -1, -1]]],
    [[0, 1, 0], [[-1, 1, -1], [-1, 1, 1], [1, 1, 1], [1, 1, -1]]], [[0, -1, 0], [[-1, -1, 1], [-1, -1, -1], [1, -1, -1], [1, -1, 1]]],
    [[0, 0, 1], [[-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]]], [[0, 0, -1], [[1, -1, -1], [-1, -1, -1], [-1, 1, -1], [1, 1, -1]]]];
  for (const [n, q] of F) { const b = t.p.length; for (const [a, bb, c] of q) { t.p.push([cx + a * sx / 2, cy + bb * sy / 2, cz + c * sz / 2]); t.n.push(n); t.c.push(col); t.m.push(mat); } t.i.push(b, b + 1, b + 2, b, b + 2, b + 3); }
}
export function tplCylX(t, x0, x1, r0, r1, sides, col, mat, cy = 0, cz = 0) {
  const b = t.p.length;
  for (let i = 0; i <= sides; i++) {
    const a = i / sides * Math.PI * 2, c = Math.cos(a), s = Math.sin(a);
    t.p.push([x0, cy + c * r0, cz + s * r0], [x1, cy + c * r1, cz + s * r1]); t.n.push([0, c, s], [0, c, s]); t.c.push(col, col); t.m.push(mat, mat);
  }
  for (let i = 0; i < sides; i++) { const k = b + i * 2; t.i.push(k, k + 2, k + 3, k, k + 3, k + 1); }
}
export function tplWing(t, x, y, span, root, tip, sweep, thick, col, mat, dihedral = 0) {
  for (const sg of [1, -1]) {
    const pts = [[x + root / 2, y, 0], [x - root / 2, y, 0], [x - root / 2 - sweep, y + dihedral, sg * span / 2], [x - root / 2 - sweep + tip, y + dihedral, sg * span / 2]];
    for (const dy of [thick / 2, -thick / 2]) { const b = t.p.length; for (const p of pts) { t.p.push([p[0], p[1] + dy, p[2]]); t.n.push([0, Math.sign(dy), 0]); t.c.push(col); t.m.push(mat); } t.i.push(b, b + 1, b + 2, b, b + 2, b + 3); }
  }
}
export function tplFin(t, x, y, h, root, tip, sweep, col, mat) {
  const pts = [[x + root / 2, y, 0], [x - root / 2, y, 0], [x - root / 2 - sweep + 0, y + h, 0], [x - root / 2 - sweep + tip, y + h, 0]];
  for (const sg of [1, -1]) { const b = t.p.length; for (const p of pts) { t.p.push([p[0], p[1], p[2] + sg * 0.15]); t.n.push([0, 0, sg]); t.c.push(col); t.m.push(mat); } t.i.push(b, b + 1, b + 2, b, b + 2, b + 3); }
}
export const WHITE = [0.92, 0.93, 0.95], GREY = [0.55, 0.57, 0.6], DARK = [0.18, 0.19, 0.21];
export const TPL = {};
(() => {
  const jet = tplNew();
  tplCylX(jet, -18, 14, 2.0, 2.0, 10, WHITE, 8); tplCylX(jet, 14, 19.5, 2.0, 0.3, 10, WHITE, 8); tplCylX(jet, -24, -18, 0.6, 2.0, 10, WHITE, 8);
  tplWing(jet, 0, -0.6, 34, 7, 1.8, 6, 0.5, GREY, 8, 1.6); tplWing(jet, -20.5, 0.6, 12, 3.5, 1.2, 2.5, 0.3, GREY, 8, 0.4);
  tplFin(jet, -20, 1.6, 7, 5, 1.8, 4, [0.70, 0.12, 0.10], 8);
  tplCylX(jet, -1, 4, 1.1, 1.1, 8, GREY, 5, -1.8, 6.5); tplCylX(jet, -1, 4, 1.1, 1.1, 8, GREY, 5, -1.8, -6.5);
  TPL.jet = jet;
  const heli = tplNew();
  tplCylX(heli, -2.4, 2.6, 1.5, 1.2, 8, [0.20, 0.30, 0.55], 8); tplCylX(heli, 2.6, 3.8, 1.2, 0.4, 8, [0.20, 0.30, 0.55], 8);
  tplCylX(heli, -9.5, -2.4, 0.3, 0.7, 6, [0.20, 0.30, 0.55], 8); tplFin(heli, -9.2, 0.0, 2.2, 1.4, 0.8, 0.6, [0.20, 0.30, 0.55], 8);
  tplBox(heli, 0, -1.9, 1.2, 4.5, 0.15, 0.15, DARK, 8); tplBox(heli, 0, -1.9, -1.2, 4.5, 0.15, 0.15, DARK, 8);
  tplBox(heli, 0, 1.75, 0, 0.6, 0.6, 0.6, DARK, 8);
  TPL.heli = heli;
  const rotor = tplNew(); tplBox(rotor, 0, 0, 0, 11, 0.08, 0.35, DARK, 8); tplBox(rotor, 0, 0, 0, 0.35, 0.08, 11, DARK, 8); TPL.rotor = rotor;
  const quad = tplNew();
  tplBox(quad, 0, 0, 0, 1.6, 0.35, 0.9, [0.95, 0.80, 0.10], 8);
  tplBox(quad, 0, 0.15, 0, 2.8, 0.12, 0.16, DARK, 8); tplBox(quad, 0, 0.15, 0, 0.16, 0.12, 2.8, DARK, 8);
  for (const [a, b] of [[1.3, 1.3], [1.3, -1.3], [-1.3, 1.3], [-1.3, -1.3]]) tplBox(quad, a * 0.7, 0.3, b * 0.7, 1.1, 0.04, 1.1, [0.25, 0.25, 0.28], 8);
  tplBox(quad, 0, -0.6, 0, 0.8, 0.6, 0.8, [0.98, 0.78, 0.05], 8);
  TPL.quad = quad;
  TPL.car = propTemplate(t => {
    tplBox(t, 0, 0.72, 0, 4.4, 0.72, 1.8, [1, 1, 1], 1);
    tplBox(t, -0.25, 1.36, 0, 2.5, 0.58, 1.62, [0, 0, 0], 2);
    for (const [a, b] of [[1.4, 0.82], [1.4, -0.82], [-1.4, 0.82], [-1.4, -0.82]]) tplBox(t, a, 0.32, b, 0.64, 0.64, 0.24, [0.05, 0.05, 0.05], 0);
  });
  TPL.person = propTemplate(t => {
    tplBox(t, 0, 0.45, 0.1, 0.2, 0.9, 0.16, [0.14, 0.15, 0.20], 0); tplBox(t, 0, 0.45, -0.1, 0.2, 0.9, 0.16, [0.14, 0.15, 0.20], 0);
    tplBox(t, 0, 1.22, 0, 0.28, 0.64, 0.46, [1, 1, 1], 1); tplBox(t, 0, 1.66, 0, 0.22, 0.24, 0.2, [0.86, 0.70, 0.56], 0);
  });
  TPL.bike = propTemplate(t => {
    tplBox(t, 0.55, 0.35, 0, 0.7, 0.7, 0.06, [0.1, 0.1, 0.1], 0); tplBox(t, -0.55, 0.35, 0, 0.7, 0.7, 0.06, [0.1, 0.1, 0.1], 0);
    tplBox(t, 0, 0.75, 0, 1.1, 0.08, 0.08, [1, 1, 1], 1); tplBox(t, -0.1, 1.2, 0, 0.35, 0.6, 0.42, [1, 1, 1], 1);
    tplBox(t, 0.05, 1.62, 0, 0.22, 0.24, 0.2, [0.86, 0.70, 0.56], 0); tplBox(t, 0.1, 0.62, 0, 0.18, 0.5, 0.3, [0.14, 0.15, 0.2], 0);
  });
  TPL.signal = propTemplate(t => {
    const G = [0.30, 0.32, 0.34];
    tplBox(t, 0, 3.2, 0, 0.24, 6.4, 0.24, G, 0); tplBox(t, 2.8, 6.25, 0, 5.6, 0.18, 0.18, G, 0);
    tplBox(t, 5.4, 5.75, 0, 0.36, 1.1, 0.36, [0.07, 0.07, 0.08], 0); tplBox(t, 2.6, 5.75, 0, 0.36, 1.1, 0.36, [0.07, 0.07, 0.08], 0);
    tplBox(t, 0.25, 2.6, 0, 0.3, 0.7, 0.3, [0.07, 0.07, 0.08], 0);
  });
  TPL.busstop = propTemplate(t => {
    tplBox(t, 0, 2.65, 0.15, 6.4, 0.14, 2.1, [0.86, 0.87, 0.89], 0);
    tplBox(t, 0, 1.35, 1.0, 6.2, 2.4, 0.06, [0, 0, 0], 2);
    tplBox(t, -3.0, 1.3, 1.0, 0.12, 2.6, 0.12, [0.5, 0.5, 0.52], 0); tplBox(t, 3.0, 1.3, 1.0, 0.12, 2.6, 0.12, [0.5, 0.5, 0.52], 0);
    tplBox(t, 3.3, 1.35, 0.45, 0.16, 2.2, 1.3, [1, 1, 1], 1);
    tplBox(t, -0.6, 0.48, 0.7, 3.2, 0.1, 0.45, [0.55, 0.38, 0.22], 0);
    tplBox(t, -3.6, 1.6, 0.0, 0.1, 3.2, 0.1, [0.5, 0.5, 0.52], 0); tplBox(t, -3.6, 3.0, 0.0, 0.08, 0.7, 0.9, [0.15, 0.55, 0.35], 0);
  });
  TPL.lamp = propTemplate(t => {
    tplBox(t, 0, 4.75, 0, 0.24, 9.5, 0.24, [0.40, 0.42, 0.44], 0);
    tplBox(t, 1.2, 9.42, 0, 2.6, 0.14, 0.14, [0.40, 0.42, 0.44], 0);
    tplBox(t, 2.35, 9.25, 0, 0.95, 0.22, 0.45, [0.85, 0.85, 0.80], 0);
  });
  const YEL = [0.92, 0.70, 0.10];
  const jib = tplNew();
  tplBox(jib, 18, 1, 0, 74, 1.8, 1.6, YEL, 8); tplBox(jib, -15, -1.5, 0, 6, 3.5, 4, [0.55, 0.55, 0.53], 8);
  tplBox(jib, 0, -2.6, 1.6, 3, 2.6, 2.2, [0.85, 0.85, 0.82], 8); tplFin(jib, 0, 1.9, 8, 4, 0.6, 2, YEL, 8);
  tplBox(jib, 32, -16, 0, 0.12, 32, 0.12, DARK, 8); tplBox(jib, 32, -32.5, 0, 1.4, 1.2, 1.4, [0.80, 0.18, 0.12], 8);
  TPL.jib = jib;
  const ferry = tplNew();
  tplBox(ferry, 0, 1.2, 0, 42, 2.6, 9, [0.12, 0.22, 0.40], 8); tplBox(ferry, 0, 3.2, 0, 41, 1.4, 9, [0.95, 0.95, 0.94], 8);
  tplBox(ferry, -2, 5.2, 0, 28, 2.6, 8, [0.92, 0.93, 0.95], 8); tplBox(ferry, 9, 7.6, 0, 8, 2.2, 7, [0.95, 0.95, 0.96], 8);
  tplCylX(ferry, 21, 24, 4.5, 0.6, 8, [0.12, 0.22, 0.40], 8, 1.2, 0);
  TPL.ferry = ferry;
  const speed = tplNew();
  tplBox(speed, 0, 0.6, 0, 9, 1.2, 2.8, [0.96, 0.96, 0.96], 8); tplCylX(speed, 4.5, 6.5, 1.4, 0.2, 6, [0.96, 0.96, 0.96], 8, 0.6, 0);
  tplBox(speed, -0.5, 1.6, 0, 3, 0.9, 2.2, [0.15, 0.18, 0.22], 8);
  TPL.speed = speed;
  const cargo = tplNew();
  tplBox(cargo, 0, 1.8, 0, 64, 3.6, 12, [0.50, 0.12, 0.10], 8); tplCylX(cargo, 32, 37, 6, 0.8, 8, [0.50, 0.12, 0.10], 8, 1.8, 0);
  const CC = [[0.15, 0.35, 0.65], [0.85, 0.45, 0.10], [0.20, 0.55, 0.30], [0.75, 0.75, 0.75], [0.65, 0.15, 0.12]];
  for (let k = 0; k < 6; k++) for (let lv = 0; lv < 2; lv++) tplBox(cargo, 18 - k * 6.4, 4.9 + lv * 2.6, 0, 6, 2.5, 10.5, CC[(k * 3 + lv) % 5], 8);
  tplBox(cargo, -26, 6.5, 0, 7, 9, 11, [0.95, 0.95, 0.95], 8);
  TPL.cargo = cargo;
  const sail = tplNew();
  tplBox(sail, 0, 0.6, 0, 11, 1.2, 3.2, [0.97, 0.97, 0.97], 8); tplCylX(sail, 5.5, 7.5, 1.6, 0.2, 6, [0.97, 0.97, 0.97], 8, 0.6, 0);
  tplBox(sail, 1, 8.2, 0, 0.18, 15, 0.18, [0.75, 0.75, 0.75], 8); tplFin(sail, -1.6, 1.4, 13.5, 5.2, 0.3, -2.4, [0.98, 0.97, 0.94], 8);
  TPL.sail = sail;
  // lathe helper: profile [[r, h]], axis "y" (balloon) or "x" (airship)
  const lathe = (t, prof, seg, colFn, mat, axis) => {
    const rows = prof.map(([r, hgt]) => { const row = []; for (let j = 0; j <= seg; j++) { const a = j / seg * Math.PI * 2; row.push(axis === "y" ? [Math.cos(a) * r, hgt, Math.sin(a) * r] : [hgt, Math.cos(a) * r, Math.sin(a) * r]); } return row; });
    for (let k = 0; k + 1 < rows.length; k++) for (let j = 0; j < seg; j++) {
      const q = [rows[k][j], rows[k][j + 1], rows[k + 1][j + 1], rows[k + 1][j]], b = t.p.length;
      const c0 = [(q[0][0] + q[2][0]) / 2, (q[0][1] + q[2][1]) / 2, (q[0][2] + q[2][2]) / 2];
      const nn = axis === "y" ? norm3([c0[0], 0.25 * (prof[k][0] - prof[k + 1][0]) / Math.max(1, Math.abs(prof[k + 1][1] - prof[k][1])) + 0.1 * Math.sign(c0[1] - prof[prof.length >> 1][1]), c0[2]]) : norm3([0.15 * Math.sign(c0[0]), c0[1], c0[2]]);
      for (const p of q) { t.p.push(p); t.n.push(nn); t.c.push(colFn(j, k)); t.m.push(mat); }
      t.i.push(b, b + 1, b + 2, b, b + 2, b + 3);
    }
  };
  TPL.lathe = lathe;
  const BAL = [[[0.90, 0.20, 0.15], [0.98, 0.80, 0.15]], [[0.15, 0.45, 0.85], [0.95, 0.95, 0.95]], [[0.20, 0.65, 0.35], [0.98, 0.85, 0.20]], [[0.75, 0.20, 0.55], [0.30, 0.20, 0.70]], [[0.95, 0.50, 0.10], [0.95, 0.95, 0.90]], [[0.10, 0.60, 0.70], [0.90, 0.30, 0.25]]];
  TPL.balloons = BAL.map(([c1, c2]) => {
    const t = tplNew();
    lathe(t, [[0.8, 0], [3.2, 1.5], [7.2, 5], [9.6, 10], [10, 14], [9, 18], [6, 21], [0.6, 22.4]], 14, (j) => (j % 2 ? c1 : c2), 8, "y");
    tplBox(t, 0, -5.2, 0, 1.6, 1.2, 1.6, [0.45, 0.32, 0.20], 8);
    for (const [a, b] of [[0.7, 0.7], [0.7, -0.7], [-0.7, 0.7], [-0.7, -0.7]]) tplBox(t, a, -2.6, b, 0.06, 5.2, 0.06, [0.3, 0.25, 0.2], 8);
    return t;
  });
  const blimp = tplNew();
  lathe(blimp, [[0.4, 38], [6, 34], [10, 25], [11.5, 10], [11.5, -8], [9.5, -24], [5.5, -33], [0.6, -38]], 16, () => [0.88, 0.89, 0.91], 8, "x");
  tplFin(blimp, -29, 6, 9, 9, 4, 3, [0.20, 0.35, 0.75], 8); tplWing(blimp, -29, 0, 26, 9, 4, 3, 0.4, [0.20, 0.35, 0.75], 8);
  tplBox(blimp, 4, -12.5, 0, 12, 3, 4, [0.80, 0.80, 0.82], 8);
  tplBox(blimp, 0, 0, 11.3, 30, 9, 0.5, [1, 1, 1], 18); tplBox(blimp, 0, 0, -11.3, 30, 9, 0.5, [1, 1, 1], 18);
  TPL.blimp = blimp;
})();
