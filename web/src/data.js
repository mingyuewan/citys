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
export function loadImg(b64) { return new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = rej; im.src = "data:image/png;base64," + b64; }); }

export function decodeData(D) {
  const out = { buildings: [], roads: [], landmarkCount: 0 };
  const MAJOR = /^(motorway|trunk|primary|secondary)(_link)?$/;
  for (const [ci, br, ow, ni, flat] of D.roads) {
    const hw = D.classes[ci];
    let run = [];
    const flush = () => { if (run.length >= 2) out.roads.push({ pts: run, hw, major: MAJOR.test(hw), bridge: !!br, oneway: !!ow || /motorway/.test(hw), name: D.names[ni] }); run = []; };
    for (let i = 0; i < flat.length; i += 2) { const x = flat[i], z = flat[i + 1]; if (inIsle(x, z, 4)) run.push([x, z]); else flush(); }
    flush();
  }
  D.landmarks.forEach((l, i) => out.buildings.push({ ring: l.r, area: Math.abs(ringArea(l.r)), h: l.h, landmark: true, L: l, id: 900000 + i * 37, name: l.n, en: l.en }));
  out.landmarkCount = D.landmarks.length;
  for (const [x, z, w, d, ang, h, zi] of D.buildings) {
    if (!inIsle(x, z, Math.max(w, d) * 0.6 + 4)) continue;
    const a = ang * Math.PI / 180;
    out.buildings.push({ x, z, w, d, ang: a, h, ring: rectRing(x, z, w, d, a), area: w * d, id: (Math.round(x * 7 + z * 13) & 0xffffff) + 1, name: "", zone: D.zones[zi] });
  }
  return out;
}
