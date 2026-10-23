/* Dataset: data/szbay.json (built by tools/build_data.py) and its decoding into building / road records.
   Ported from the "decode data → building records" section of src/city.src.html. */
import { inIsle, initIsle, ringArea, rectRing } from "./world.js";

export const ZONE_ZH = { cbd: "后海商务区", tech: "科技园", shekou: "蛇口片区", res: "住宅片区", village: "城中村" };

export async function loadData(url = "data/szbay.json") {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  const D = await r.json();
  initIsle(D);
  return D;
}
// real OSM building footprints merged for the island (tools/osm/merge_osm.py); null when absent → generated only
export async function loadOsmBuildings(url = "data/osm-buildings.json") {
  try { const r = await fetch(url); return r.ok ? await r.json() : null; } catch (e) { return null; }
}
export function loadImg(b64) { return new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = rej; im.src = "data:image/png;base64," + b64; }); }

// buildings: landmarks, then real OSM footprints (OB), then the generated ones that OB did not displace
export function decodeData(D, OB = null) {
  const out = { buildings: [], roads: [], landmarkCount: 0, osmCount: 0 };
  const MAJOR = /^(motorway|trunk|primary|secondary)(_link)?$/;
  for (const [ci, br, ow, ni, flat] of D.roads) {
    const hw = D.classes[ci];
    let run = [];
    const flush = () => { if (run.length >= 2) out.roads.push({ pts: run, hw, major: MAJOR.test(hw), bridge: !!br, oneway: !!ow || /motorway/.test(hw), name: D.names[ni] }); run = []; };
    for (let i = 0; i < flat.length; i += 2) { const x = flat[i], z = flat[i + 1]; if (inIsle(x, z, 4)) run.push([x, z]); else flush(); }
    flush();
  }
  // landmarks moved onto their real OSM footprint (merge_osm.py); the island outline (initIsle) keeps the original data
  if (OB && OB.lm_move && !D._moved) {
    for (const [i, [dx, dz]] of Object.entries(OB.lm_move)) { const l = D.landmarks[i]; l.c = [l.c[0] + dx, l.c[1] + dz]; l.r = l.r.map(p => [p[0] + dx, p[1] + dz]); }
    D._moved = true;
  }
  D.landmarks.forEach((l, i) => out.buildings.push({ ring: l.r, area: Math.abs(ringArea(l.r)), h: l.h, landmark: true, L: l, id: 900000 + i * 37, name: l.n, en: l.en }));
  out.landmarkCount = D.landmarks.length;
  if (OB) for (const [dm, h, mh, src, name, kind] of OB.b) {
    const ring = []; for (let i = 0; i < dm.length; i += 2) ring.push([dm[i] / 10, dm[i + 1] / 10]);
    out.buildings.push({ ring, h, minh: mh, osm: true, src, name, kind, area: Math.abs(ringArea(ring)), id: (Math.round(dm[0] * 0.7 + dm[1] * 1.3) & 0xffffff) + 1 });
  }
  out.osmCount = OB ? OB.b.length : 0;
  const drop = new Set(OB ? OB.drop : []);
  for (let i = 0; i < D.buildings.length; i++) {
    if (drop.has(i)) continue;
    const [x, z, w, d, ang, h, zi] = D.buildings[i];
    if (!inIsle(x, z, Math.max(w, d) * 0.6 + 4)) continue;
    const a = ang * Math.PI / 180;
    out.buildings.push({ x, z, w, d, ang: a, h, ring: rectRing(x, z, w, d, a), area: w * d, id: (Math.round(x * 7 + z * 13) & 0xffffff) + 1, name: "", zone: D.zones[zi] });
  }
  return out;
}
