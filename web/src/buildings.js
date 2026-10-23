/* Generated buildings and landmarks → one merged city mesh (landmarks first, so the first lmEnd indices are landmarks).
   Ported verbatim from the "palettes / generated buildings / landmarks" sections of src/city.src.html. */
import { Geo, VS, hash1, rng, lerp, centroid, prism, frustum, boxAt, scaleRing, rectRing, chamferRing, superRing, circleRing, crossRing, lRing, gableRoof, shell } from "./world.js";

// ---- palettes
export const GLASS = [[0.60, 0.74, 0.74], [0.54, 0.70, 0.66], [0.82, 0.80, 0.74], [0.56, 0.66, 0.74], [0.78, 0.66, 0.52], [0.66, 0.76, 0.70]];   // style A: celadon, cream, a terracotta
export const RESI = [[0.93, 0.89, 0.82], [0.96, 0.93, 0.87], [0.90, 0.85, 0.77], [0.94, 0.85, 0.74], [0.86, 0.88, 0.84], [0.92, 0.82, 0.72]];
export const VILL = [[0.86, 0.80, 0.72], [0.82, 0.72, 0.66], [0.78, 0.82, 0.84], [0.90, 0.88, 0.82], [0.76, 0.70, 0.62], [0.84, 0.76, 0.70]];
export const CONC = [0.60, 0.60, 0.58], METAL = [0.66, 0.68, 0.70];

// ---- generated buildings
export function hsv3(hh) { const k = [5, 3, 1].map(n => (n + hh * 6) % 6); return k.map(v => 0.85 - 0.6 * Math.max(0, Math.min(v, 4 - v, 1))); }
export const beacons = [];           // [x,y,z,phase] aircraft warning lights
export const craneCands = [], CONSTRUCT = [], ROOFTREES = [], ROOFTREE_Y = [];
export const roofSpots = [];         // rooftops for delivery drones
function roofUnits(g, cx, cz, w, d, ang, y, bid, rnd, n) {
  for (let k = 0; k < n; k++) {
    const uw = 3 + rnd() * Math.min(9, w * 0.3), ud = 3 + rnd() * Math.min(9, d * 0.3);
    const ou = (rnd() - 0.5) * (w - uw) * 0.6, ov = (rnd() - 0.5) * (d - ud) * 0.6;
    const c = Math.cos(ang), s = Math.sin(ang);
    boxAt(g, cx + c * ou - s * ov, cz + s * ou + c * ov, uw, ud, ang, y, y + 2 + rnd() * 3.5, CONC.map(x => x * (0.9 + rnd() * 0.2)), 3, bid);
  }
}
export function genBuilding(g, b, bid) {
  const rnd = rng(b.id * 2654435761 + bid);
  const { x, z, w, d, h } = b; const ang = b.ang;
  const zone = b.zone;
  if (zone === "village") {
    const col = VILL[Math.floor(rnd() * VILL.length)];
    if (h < 26 && rnd() < 0.18) {
      prism(g, rectRing(x, z, w, d, ang), 0, h - 3, col, 4, bid, { cap: false });
      gableRoof(g, x, z, w + 1, d + 1, ang, h - 3, 3.2, [0.55, 0.36, 0.30], bid);
    } else {
      prism(g, rectRing(x, z, w, d, ang), 0, h, col, 4, bid);
      if (rnd() < 0.45) boxAt(g, x + (rnd() - 0.5) * w * 0.4, z + (rnd() - 0.5) * d * 0.4, 4, 4, ang, h, h + 3, col, 4, bid);
      if (rnd() < 0.35) { const tc = [0.30, 0.40, 0.60]; prism(g, circleRing(x + (rnd() - 0.5) * w * 0.5, z + (rnd() - 0.5) * d * 0.5, 1.2, 8), h, h + 2.2, tc, 5, bid); }
      if (rnd() < 0.4) { const c = Math.cos(ang), s2 = Math.sin(ang), n = 2 + (rnd() * 3 | 0); for (let k = 0; k < n; k++) { const v = (k - (n - 1) / 2) * 2.4; boxAt(g, x - s2 * v + c * w * 0.15, z + c * v + s2 * w * 0.15, w * 0.45, 1.8, ang, h + 0.4, h + 0.9, [0.10, 0.14, 0.26], 5, bid); } }
      if (rnd() < 0.2) prism(g, rectRing(x, z, w * 0.8, d * 0.8, ang), h, h + 0.4, [0.30, 0.45, 0.22], 11, bid);
      prism(g, scaleRing(rectRing(x, z, w, d, ang), 1.0, x, z), h, h + 1.1, col.map(v => v * 0.9), 3, bid, { cap: false, both: true });
      const nc = rnd() * 4 | 0;
      for (let k = 0; k < nc; k++) {
        const u = (rnd() - 0.5) * w * 0.7, v = (rnd() - 0.5) * d * 0.7, c = Math.cos(ang), s2 = Math.sin(ang);
        const px = x + c * u - s2 * v, pz = z + s2 * u + c * v, kind = rnd();
        if (kind < 0.4) prism(g, circleRing(px, pz, 0.9 + rnd() * 0.5, 8), h, h + 1.8, kind < 0.2 ? [0.25, 0.40, 0.65] : [0.85, 0.85, 0.83], 5, bid, { smooth: true });
        else if (kind < 0.7) boxAt(g, px, pz, 2 + rnd() * 2, 0.08, ang + rnd(), h + 1.4, h + 2.4, hsv3(rnd()), 8, bid);
        else boxAt(g, px, pz, 1.4, 1.4, ang, h, h + 1.0 + rnd(), [0.25, 0.42, 0.20], 11, bid);
      }
    }
    return;
  }
  if (zone === "res" || (zone === "shekou" && rnd() < 0.5 && h > 40)) {
    const col = RESI[Math.floor(rnd() * RESI.length)];
    let y0 = 0;
    if (rnd() < 0.25) { prism(g, rectRing(x, z, w, d, ang), 0, 7, [0.70, 0.66, 0.60], 2, bid); y0 = 7; }
    const pointTower = w < 34 && d < 34 && rnd() < 0.6;
    void 0;
    const R = pointTower ? crossRing(x, z, w, d, ang, 0.46 + rnd() * 0.12) : (rnd() < 0.3 ? chamferRing(x, z, w, d, ang, 0.18) : rectRing(x, z, w, d, ang));
    prism(g, R, y0, h, col, 1, bid, { capCol: [0.62, 0.62, 0.60] });
    // stair / lift core housing on top + parapet frame
    boxAt(g, x, z, Math.min(w, d) * 0.35, Math.min(w, d) * 0.28, ang, h, h + 4.5, col, 1, bid);
    if (rnd() < 0.35) { const ax = x + Math.cos(ang) * w * 0.2, az = z + Math.sin(ang) * w * 0.2; frustum(g, circleRing(ax, az, 0.35, 6), circleRing(ax, az, 0.08, 6), h + 4.5, h + 12 + rnd() * 12, METAL, 5, bid, { cap: false }); }
    if (rnd() < 0.25) { const tx2 = x - Math.cos(ang) * w * 0.25, tz2 = z - Math.sin(ang) * w * 0.25; prism(g, circleRing(tx2, tz2, 2.2, 10), h, h + 3.2, [0.72, 0.72, 0.70], 3, bid, { smooth: true }); }
    if (rnd() < 0.5) prism(g, scaleRing(R, 1.02, x, z), h, h + 1.2, col.map(v => v * 0.9), 3, bid, { cap: false, both: true });
    else if (h > 60 && rnd() < 0.6) {      // decorative crown frame (common on Shenzhen residential towers)
      prism(g, scaleRing(R, 1.01, x, z), h, h + 6.5, col.map(v => v * 0.95), 3, bid, { cap: false, both: true });
      prism(g, scaleRing(R, 1.04, x, z), h + 6.5, h + 7.4, col.map(v => v * 0.85), 3, bid, { capCol: col.map(v => v * 0.8) });
    }
    if (h > 90 && rnd() < 0.4) beacons.push([x, h + 5, z, rnd() * 6]);
    if (h > 50) roofSpots.push([x, h + 4.5, z]);
    return;
  }
  if (zone === "shekou" && h < 30) {
    const col = rnd() < 0.5 ? VILL[Math.floor(rnd() * VILL.length)] : RESI[Math.floor(rnd() * RESI.length)];
    if (rnd() < 0.35) { prism(g, rectRing(x, z, w, d, ang), 0, h - 4, col, 4, bid, { cap: false }); gableRoof(g, x, z, w + 1.2, d + 1.2, ang, h - 4, 4, [0.52, 0.32, 0.26], bid); }
    else { prism(g, rnd() < 0.3 ? lRing(x, z, w, d, ang, 0.5) : rectRing(x, z, w, d, ang), 0, h, col, rnd() < 0.5 ? 4 : 2, bid); roofUnits(g, x, z, w, d, ang, h, bid, rnd, 1 + (rnd() * 2 | 0)); }
    return;
  }
  // offices: cbd / tech / taller shekou
  const tint = GLASS[Math.floor(rnd() * GLASS.length)];
  if (h < 45) {
    const R = rnd() < 0.3 ? lRing(x, z, w, d, ang, 0.55) : rnd() < 0.4 ? chamferRing(x, z, w, d, ang, 0.2) : rectRing(x, z, w, d, ang);
    prism(g, R, 0, h, tint, rnd() < 0.5 ? 0 : 2, bid, { capCol: [0.58, 0.58, 0.57] });
    roofUnits(g, x, z, w, d, ang, h, bid, rnd, 1 + (rnd() * 3 | 0));
    return;
  }
  const cA = Math.cos(ang), sA = Math.sin(ang);
  const W2 = (u, v) => [x + cA * u - sA * v, z + sA * u + cA * v];
  if ((zone === "cbd" || zone === "tech") && h > 60 && h < 240 && hash1(b.id * 0.131 + 0.7) < 0.08) {
    // construction site: finished lower floors, open concrete frame with safety nets above, core rising
    const R = rectRing(x, z, w * 0.72, d * 0.72, ang), built = h * 0.6, top = h * 0.84;
    prism(g, rectRing(x, z, w, d, ang), 0, 14, tint.map(v => v * 1.1), 2, bid, { capCol: CONC });
    prism(g, R, 14, built, tint, 0, bid, { cap: false });
    prism(g, R, built, top, [0.62, 0.61, 0.58], 20, bid, { capCol: [0.55, 0.55, 0.52] });
    boxAt(g, x, z, w * 0.24, d * 0.24, ang, top, top + 9, [0.62, 0.62, 0.6], 3, bid);
    CONSTRUCT.push({ x, z, w, d, ang, h: top + 9 });
    return;
  }
  let y0 = 0, tw = w, td = d;
  if (rnd() < 0.62) {
    const ph = 14 + rnd() * 12, green = rnd() < 0.55;
    prism(g, rnd() < 0.5 ? chamferRing(x, z, w, d, ang, 0.12) : rectRing(x, z, w, d, ang), 0, ph, tint.map(v => v * 1.15), 2, bid, { capCol: green ? [0.30, 0.44, 0.24] : [0.55, 0.56, 0.54], capMat: 11 });
    y0 = ph; tw = w * (0.62 + rnd() * 0.12); td = d * (0.64 + rnd() * 0.12);
    if (green) for (let k = 0; k < 12; k++) {      // roof garden trees around the tower
      const u = (rnd() - 0.5) * (w - 6), v = (rnd() - 0.5) * (d - 6);
      if (Math.abs(u) < tw / 2 + 3 && Math.abs(v) < td / 2 + 3) continue;
      const p = W2(u, v); ROOFTREES.push(p[0], p[1]); ROOFTREE_Y.push(ph + 0.4);
    }
    { const p = W2(0, -(d / 2 + 2.2)); boxAt(g, p[0], p[1], Math.min(w * 0.4, 22), 4.4, ang, 5.2, 5.6, METAL, 5, bid); }
  } else {
    const p = W2(0, -(d / 2 + 2.4)); boxAt(g, p[0], p[1], Math.min(w * 0.45, 20), 4.8, ang, 6.4, 6.9, METAL, 5, bid);
    for (const sg of [-1, 1]) { const q = W2(sg * Math.min(w * 0.2, 9), -(d / 2 + 4.3)); prism(g, circleRing(q[0], q[1], 0.25, 6), 0, 6.4, METAL, 5, bid, { cap: false }); }
  }
  const form = rnd();
  const crown = rnd();
  const crownH = h > 150 ? 14 + rnd() * 18 : 6 + rnd() * 8;
  const bodyTop = h - crownH;
  let topR;
  if (form < 0.28) {                                  // plain / chamfered box
    const R = rnd() < 0.5 ? chamferRing(x, z, tw, td, ang, 0.14 + rnd() * 0.12) : rectRing(x, z, tw, td, ang);
    prism(g, R, y0, bodyTop, tint, 0, bid, { cap: false }); topR = R;
  } else if (form < 0.48) {                           // rounded
    const R = superRing(x, z, tw, td, ang, 3 + rnd() * 3, 28);
    prism(g, R, y0, bodyTop, tint, 0, bid, { cap: false, smooth: true }); topR = R;
  } else if (form < 0.72) {                           // tiered setbacks
    const R0 = rnd() < 0.5 ? chamferRing(x, z, tw, td, ang, 0.12) : rectRing(x, z, tw, td, ang);
    const t1 = y0 + (bodyTop - y0) * (0.5 + rnd() * 0.15), t2 = y0 + (bodyTop - y0) * (0.8 + rnd() * 0.08);
    const R1 = scaleRing(R0, 0.84, x, z), R2 = scaleRing(R0, 0.68, x, z);
    prism(g, R0, y0, t1, tint, 0, bid, { capCol: [0.32, 0.45, 0.26], capMat: 11 });
    prism(g, R1, t1, t2, tint, 0, bid, { capCol: [0.32, 0.45, 0.26], capMat: 11 });
    for (const [Ra, Rb, yy] of [[R0, R1, t1], [R1, R2, t2]]) {   // sky-garden trees on each setback terrace
      const nV = Ra.length;
      for (let k = 0; k < nV; k++) {
        const a0 = Ra[k], a1 = Ra[(k + 1) % nV], b0 = Rb[k], b1 = Rb[(k + 1) % nV];
        for (const f of [0.25, 0.5, 0.75]) {
          if (rnd() < 0.35) continue;
          const px = lerp(lerp(a0[0], a1[0], f), lerp(b0[0], b1[0], f), 0.5), pz = lerp(lerp(a0[1], a1[1], f), lerp(b0[1], b1[1], f), 0.5);
          ROOFTREES.push(px, pz); ROOFTREE_Y.push(yy + 0.4);
        }
      }
    }
    prism(g, R2, t2, bodyTop, tint, 0, bid, { cap: false }); topR = R2;
  } else if (form < 0.86) {                           // gently tapering
    const R0 = chamferRing(x, z, tw, td, ang, 0.1 + rnd() * 0.15);
    const R1 = scaleRing(R0, 0.82, x, z);
    frustum(g, R0, R1, y0, bodyTop, tint, 0, bid, { cap: false }); topR = R1;
  } else {                                            // twin slab
    const c = Math.cos(ang), s = Math.sin(ang), off = td * 0.26;
    const A = rectRing(x - s * off, z + c * off, tw, td * 0.46, ang), B = rectRing(x + s * off, z - c * off, tw * 0.8, td * 0.46, ang);
    prism(g, A, y0, bodyTop, tint, 0, bid, { capCol: CONC });
    prism(g, B, y0, bodyTop * 0.88, tint, 0, bid, { capCol: CONC });
    topR = A;
  }
  const [cx, cz] = centroid(topR);
  if (crown < 0.3) {                                  // glass crown taper
    frustum(g, topR, scaleRing(topR, 0.62, cx, cz), bodyTop, h, tint.map(v => v * 1.1), 5, bid, { capCol: CONC });
  } else if (crown < 0.5 && h > 120) {                // crown + spire
    frustum(g, topR, scaleRing(topR, 0.7, cx, cz), bodyTop, h - crownH * 0.3, tint, 5, bid, { capCol: CONC });
    frustum(g, circleRing(cx, cz, 1.8, 6), circleRing(cx, cz, 0.2, 6), h - crownH * 0.3, h + 26 + rnd() * 24, METAL, 5, bid, { cap: false });
  } else if (crown < 0.68) {                          // glass fin parapet + plant
    prism(g, topR, bodyTop, h, tint, 5, bid, { capCol: CONC });
    roofUnits(g, cx, cz, tw * 0.6, td * 0.6, ang, h, bid, rnd, 2);
  } else if (crown < 0.84) {                          // helipad
    prism(g, topR, bodyTop, h, tint, 0, bid, { capCol: CONC });
    prism(g, circleRing(cx, cz, Math.min(tw, td) * 0.36, 16), h, h + 2.5, [0.35, 0.37, 0.38], 3, bid, { capCol: [0.30, 0.42, 0.34] });
  } else {                                            // slanted top
    const sl = topR.map(p => { const du = (p[0] - cx) * Math.cos(ang) + (p[1] - cz) * Math.sin(ang); return du; });
    const maxU = Math.max(...sl);
    const B = topR.map(p => p);
    // emulate a slant with a short taper toward one side
    frustum(g, topR, B.map((p, i) => [p[0] + (cx - p[0]) * (sl[i] > 0 ? 0.0 : 0.45), p[1] + (cz - p[1]) * (sl[i] > 0 ? 0.0 : 0.45)]), bodyTop, h, tint, 5, bid, { capCol: CONC });
    void maxU;
  }
  if (h > 110 && rnd() < 0.35) prism(g, scaleRing(topR, 1.006, cx, cz), bodyTop - 7, bodyTop - 1.5, tint, 7, bid, { cap: false });
  if (h > 140) beacons.push([cx, h + (crown >= 0.3 && crown < 0.5 && h > 120 ? 50 : 3), cz, rnd() * 6]);
  if (zone === "cbd" || zone === "tech") craneCands.push({ x, z, w, d, ang, h });
  roofSpots.push([cx, h + 3, cz]);
}

// ---- landmarks
export const LM_TOPS = [];   // for searchlights: [x, y, z]
export function genLandmark(g, L, bid, all) {
  const [cx, cz] = L.c, h = L.h, rot = L.rot * Math.PI / 180, [w, d] = L.s;
  const glass = L.k === "bamboo" ? [0.90, 0.88, 0.82] : [0.62, 0.74, 0.76];   // style A: the Spring Bamboo cream white, the rest celadon
  switch (L.k) {
    case "bamboo": {   // 华润大厦「春笋」: tapering cylinder, closing to a point
      const r0 = w, seg = 56;
      const prof = [[0, 1], [0.25, 0.985], [0.5, 0.955], [0.7, 0.915], [0.8, 0.88], [0.86, 0.80], [0.91, 0.66], [0.95, 0.47], [0.98, 0.26], [1.0, 0.02]];
      for (let i = 0; i + 1 < prof.length; i++) {
        const [t0, s0] = prof[i], [t1, s1] = prof[i + 1];
        frustum(g, circleRing(cx, cz, r0 * s0, seg), circleRing(cx, cz, r0 * s1, seg), t0 * h, t1 * h, glass, 7, bid, { smooth: true, cap: false, uFix: 2 * Math.PI * r0 });
      }
      const FIN = [0.90, 0.91, 0.92];
      for (let j = 0; j < 56; j++) {
        const a = (j + 0.5) / 56 * Math.PI * 2, ca = Math.cos(a), sa = Math.sin(a), tx = -sa, tz = ca;
        let prev = null;
        for (const [t0, s0] of prof) {
          const r = r0 * s0, y = t0 * h, dep = 1.7 * Math.min(1, s0 * 1.6), wd = 0.38 * Math.min(1, s0 * 2);
          const inner = [cx + ca * r, y, cz + sa * r], outer = [cx + ca * (r + dep), y, cz + sa * (r + dep)];
          if (prev) {
            for (const sg of [1, -1]) {
              const P = [prev[0], prev[1], outer, inner].map((p, k) => { const ww = (k < 2 ? prev[2] : wd) * sg; return [p[0] + tx * ww, p[1], p[2] + tz * ww]; });
              const vs = P.map(p => g.vert(p[0], p[1], p[2], tx * sg, 0, tz * sg, FIN, 0, p[1], bid, 5));
              g.quad(vs[0], vs[1], vs[2], vs[3]);
            }
            const F = [[prev[1], -prev[2]], [prev[1], prev[2]], [outer, wd], [outer, -wd]].map(([p, ww]) => g.vert(p[0] + tx * ww, p[1], p[2] + tz * ww, ca, 0.05, sa, FIN, 0, p[1], bid, 5));
            g.quad(F[0], F[1], F[2], F[3]);
          }
          prev = [inner, outer, wd];
        }
      }
      LM_TOPS.push([cx, h * 0.93, cz]); beacons.push([cx, h + 1, cz, 0]);
      break;
    }
    case "taper": {
      const R0 = chamferRing(cx, cz, w, d, rot, 0.16);
      const R1 = scaleRing(R0, 0.9, cx, cz), R2 = scaleRing(R0, 0.58, cx, cz);
      frustum(g, R0, R1, 0, h * 0.82, glass, 7, bid, { cap: false });
      frustum(g, R1, R2, h * 0.82, h * 0.97, glass, 7, bid, { capCol: CONC });
      frustum(g, circleRing(cx, cz, 2.2, 8), circleRing(cx, cz, 0.3, 8), h * 0.97, h * 1.03, METAL, 5, bid, { cap: false });
      LM_TOPS.push([cx, h * 0.97, cz]); beacons.push([cx, h * 1.03, cz, 1]);
      break;
    }
    case "roundtaper": {
      const R0 = superRing(cx, cz, w, d, rot, 3.2, 36), R1 = scaleRing(R0, 0.86, cx, cz);
      frustum(g, R0, R1, 0, h * 0.86, glass, 7, bid, { cap: false, smooth: true });
      frustum(g, R1, scaleRing(R0, 0.45, cx, cz), h * 0.86, h, glass, 7, bid, { smooth: true, capCol: CONC });
      LM_TOPS.push([cx, h, cz]); beacons.push([cx, h + 1, cz, 2]);
      break;
    }
    case "tiered": {
      const R0 = chamferRing(cx, cz, w, d, rot, 0.1);
      prism(g, rectRing(cx, cz, w * 1.6, d * 1.5, rot), 0, 22, [0.55, 0.60, 0.62], 2, bid, { capCol: [0.45, 0.55, 0.46] });
      prism(g, R0, 22, h * 0.56, glass, 7, bid, { capCol: CONC });
      prism(g, scaleRing(R0, 0.86, cx, cz), h * 0.56, h * 0.82, glass, 7, bid, { capCol: CONC });
      frustum(g, scaleRing(R0, 0.72, cx, cz), scaleRing(R0, 0.62, cx, cz), h * 0.82, h, glass, 7, bid, { capCol: CONC });
      LM_TOPS.push([cx, h, cz]); beacons.push([cx, h + 1, cz, 3]);
      break;
    }
    case "hanking": {  // 汉京: main slab + offset core rising beyond it
      const c = Math.cos(rot), s = Math.sin(rot);
      prism(g, chamferRing(cx - s * 6, cz + c * 6, w, d * 0.72, rot, 0.08), 0, h * 0.93, glass, 7, bid, { capCol: CONC });
      prism(g, rectRing(cx + s * (d * 0.36), cz - c * (d * 0.36), w * 0.42, d * 0.34, rot), 0, h, [0.46, 0.52, 0.58], 5, bid, { capCol: CONC });
      LM_TOPS.push([cx, h, cz]); beacons.push([cx + s * d * 0.36, h + 1, cz - c * d * 0.36, 4]);
      break;
    }
    case "tencentS": case "tencentN": {
      prism(g, chamferRing(cx, cz, w, d, rot, 0.08), 0, h, [0.42, 0.52, 0.58], 7, bid, { capCol: CONC });
      roofUnits(g, cx, cz, w * 0.6, d * 0.6, rot, h, bid, rng(bid + 7), 2);
      if (L.k === "tencentS") {   // three sky links to the north tower
        const N = all.find(o => o.k === "tencentN");
        if (N) {
          const [nx, nz] = N.c, mx = (cx + nx) / 2, mz = (cz + nz) / 2, len = Math.hypot(nx - cx, nz - cz) + 4;
          const la = Math.atan2(nz - cz, nx - cx);
          for (const [y0, y1, wd] of [[30, 58, 36], [118, 132, 26], [176, 190, 22]]) boxAt(g, mx, mz, len, wd, la, y0, y1, [0.48, 0.56, 0.62], 0, bid);
        }
      }
      LM_TOPS.push([cx, h, cz]);
      break;
    }
    case "cocoon": shell(g, cx, cz, w / 2, d / 2, rot, h, [0.95, 0.94, 0.90], 6, bid); break;
    case "pebble": shell(g, cx, cz, w / 2, d / 2, rot, h, [0.90, 0.88, 0.82], 6, bid, 8, 40); break;
    default: prism(g, L.r, 0, h, glass, 7, bid);
  }
}

// ---- real buildings (OpenStreetMap footprints, merged by tools/osm/merge_osm.py): extruded from their outline,
// dressed by building kind and height in the same materials as the generated ones
const KIND_RES = /^(apartments|residential|dormitory|hotel)$/, KIND_LOW = /^(house|detached|terrace|semidetached_house|bungalow|hut|shed|kiosk|cabin)$/;
const KIND_WORKS = /^(industrial|warehouse|garage|garages|service|construction|parking|carport|storage_tank|greenhouse)$/;
const KIND_CIVIC = /^(retail|commercial|supermarket|train_station|transportation|public|civic|government|school|university|college|hospital|kindergarten|sports_centre|stadium|church|temple)$/;
export function genOsmBuilding(g, b, bid) {
  const rnd = rng(b.id * 2654435761 + bid), r = b.ring, k = b.kind, area = b.area;
  const y0 = b.minh || 0, h = Math.max(b.h, y0 + 2.5);
  // the outline's longest edge orients the roof plant
  let ang = 0, best = 0;
  for (let i = 0; i < r.length; i++) { const p = r[i], q = r[(i + 1) % r.length], l = Math.hypot(q[0] - p[0], q[1] - p[1]); if (l > best) { best = l; ang = Math.atan2(q[1] - p[1], q[0] - p[0]); } }
  const [cx, cz] = centroid(r), s = Math.sqrt(area);
  if (k === "roof") { prism(g, r, Math.max(y0, h - 1.2), h, [0.86, 0.85, 0.82], 3, bid); return; }   // canopies
  let mat, col, green = false;
  if (KIND_RES.test(k) || (k === "yes" && h >= 24 && h < 130 && area < 1600 && rnd() < 0.6)) { mat = 1; col = RESI[Math.floor(rnd() * RESI.length)]; }
  else if (KIND_LOW.test(k) || (h < 18 && area < 450)) { mat = 4; col = VILL[Math.floor(rnd() * VILL.length)]; }
  else if (KIND_WORKS.test(k)) { mat = 3; col = CONC.map(v => v * (0.95 + rnd() * 0.15)); }
  else if (KIND_CIVIC.test(k) && h < 45) { mat = 2; col = GLASS[Math.floor(rnd() * GLASS.length)].map(v => v * 1.1); green = rnd() < 0.35; }
  else { mat = 0; col = GLASS[Math.floor(rnd() * GLASS.length)]; }
  const capO = green ? { capCol: [0.32, 0.45, 0.26], capMat: 11 } : { capCol: CONC.map(v => v * 0.95) };
  if (mat === 2 && h > 12 && y0 === 0) {   // civic / retail: shop fronts on the ground floor, offices above
    prism(g, r, 0, 7, col.map(v => v * 1.05), 2, bid, { cap: false }); prism(g, r, 7, h, col, 0, bid, capO);
  } else prism(g, r, y0, h, col, mat, bid, capO);
  if (y0 > 0) return;   // a building:part floating on another part: no roof plant
  if (h > 18 && s > 14) roofUnits(g, cx, cz, s * 0.55, s * 0.55, ang, h, bid, rnd, 1 + (rnd() * 3 | 0));
  if (mat === 1 && h > 60 && rnd() < 0.5) prism(g, scaleRing(r, 1.01, cx, cz), h, h + 1.2, col.map(v => v * 0.9), 3, bid, { cap: false, both: true });
  if (h > 140) beacons.push([cx, h + 3, cz, rnd() * 6]);
  if (h > 50) roofSpots.push([cx, h + 3, cz]);
}

// modelled landmarks (models.js, tools/blender/model_landmarks.py): k → { V, I } in local coordinates, placed on the
// landmark's centre and rotation; the procedural version is still generated into a throwaway Geo for its side effects
// (searchlight tops, aircraft beacons)
export const LANDMARK_MODELS = {};
function appendModel(g, M, cx, cz, ang, bid) {
  const c = Math.cos(ang), s = Math.sin(ang), V = M.V, base = g.n;
  for (let o = 0; o < V.length; o += VS) {
    const x = V[o], z = V[o + 2], nx = V[o + 3], nz = V[o + 5];
    g.v.push(cx + c * x - s * z, V[o + 1], cz + s * x + c * z, c * nx - s * nz, V[o + 4], s * nx + c * nz, V[o + 6], V[o + 7], V[o + 8], V[o + 9], V[o + 10], bid, V[o + 12]);
    g.n++;
  }
  for (let k = 0; k < M.I.length; k++) g.i.push(base + M.I[k]);
}

// landmarks, real buildings, generated buildings — in that order, so a draw range can leave the generated ones out
export function buildCity(osm, D) {
  const g = new Geo();
  let realEnd = 0;
  const nReal = osm.landmarkCount + (osm.osmCount || 0);
  osm.buildings.forEach((b, bid) => {
    if (b.landmark && LANDMARK_MODELS[b.L.k]) { genLandmark(new Geo(), b.L, bid, D.landmarks); appendModel(g, LANDMARK_MODELS[b.L.k], b.L.c[0], b.L.c[1], b.L.rot * Math.PI / 180, bid); }
    else if (b.landmark) genLandmark(g, b.L, bid, D.landmarks); else if (b.osm) genOsmBuilding(g, b, bid); else genBuilding(g, b, bid);
    if (bid === nReal - 1) realEnd = g.i.length;
  });
  return { V: new Float32Array(g.v), I: new Uint32Array(g.i), lmEnd: realEnd };
}
