"""One-off: convert the Overpass-fetching page into a page that reads the embedded dataset.
Produces src.html (template with /*__SZDATA__*/ placeholder)."""
import re
import sys

src = open(sys.argv[1], encoding="utf-8").read()


def cut(text, start_marker, end_marker, replacement, include_end=False):
    a = text.index(start_marker)
    b = text.index(end_marker, a)
    if include_end:
        b += len(end_marker)
    return text[:a] + replacement + text[b:]


# ---------- markup ----------
src = src.replace(
    '<div id="credit">地图数据 © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap 贡献者</a></div>',
    '<div id="credit">道路 © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap 贡献者</a> · 地标坐标与高度：维基百科 · 其余楼体按街区生成</div>')

src = cut(src, '<nav id="rail"', '</nav>', '''<nav id="rail" class="panel" aria-label="视图控制">
  <button class="btn" id="bMode" type="button" aria-pressed="false" title="切换白天/夜晚 (N)">夜景 <span class="k">N</span></button>
  <button class="btn" id="bOrbit" type="button" aria-pressed="false" title="自动环绕 (R)">环绕 <span class="k">R</span></button>
  <button class="btn" id="bHome" type="button" title="回到总览 (H)">总览 <span class="k">H</span></button>
  <span class="sep" aria-hidden="true"></span>
  <select id="selLm" aria-label="飞往地标">
    <option value="">飞往地标…</option>
  </select>
  <button class="btn" id="bGen" type="button" aria-pressed="true" title="显示/隐藏生成的楼体 (G)">生成楼体 <span class="k">G</span></button>
''', include_end=False)

src = cut(src, '<div id="loader">', '<script>', '''<div id="loader">
  <div class="box panel" role="status">
    <h3 id="lTitle">正在搭建深圳湾</h3>
    <p id="lText">读取内置的道路、海岸与楼体数据</p>
    <div class="err" id="lErr" hidden></div>
    <div class="bar" id="lBar"><i></i></div>
  </div>
</div>

<script type="application/json" id="szdata">/*__SZDATA__*/</script>
''')

# ---------- script: header + constants ----------
src = cut(src, '   Data: Overpass API', '/* ---------------- UI helpers', '''   Data: embedded. Roads = OpenStreetMap (via ni1o1/pygeo-tutorial extract),
   landmarks = Wikipedia coordinates/heights, other buildings generated per real street block.
   ========================================================================= */

const D = JSON.parse(document.getElementById("szdata").textContent);
const CENTER = { lat: D.center[0], lon: D.center[1] };
const KY = 110574, KX = 111320 * Math.cos(CENTER.lat * Math.PI / 180);
const $ = s => document.querySelector(s);
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

''')
src = src.replace('''    $("#lRow").hidden = !opts.actions;
    $("#lBar").hidden = !!opts.actions;
''', '''    $("#lBar").hidden = !!opts.actions;
''')

# ---------- remove cache/fetch/parse, add decoder ----------
src = cut(src, '/* ---------------- IndexedDB cache', '/* ---------------- Ground texture', '''/* ---------------- Decode embedded data ---------------- */
function ringArea(r) { let a = 0; for (let i = 0, n = r.length; i < n; i++) { const p = r[i], q = r[(i + 1) % n]; a += p[0] * q[1] - q[0] * p[1]; } return a / 2; }
function centroid(r) { let x = 0, z = 0; for (const p of r) { x += p[0]; z += p[1]; } return [x / r.length, z / r.length]; }
const ZONE_ZH = { cbd: "后海商务区", tech: "科技园", shekou: "蛇口片区", res: "住宅片区", village: "城中村" };

function decodeData(D) {
  const out = { buildings: [], roads: [], landmarkCount: 0 };
  const MAJOR = /^(motorway|trunk|primary|secondary)(_link)?$/;
  for (const [ci, br, ow, ni, flat] of D.roads) {
    const hw = D.classes[ci], pts = [];
    for (let i = 0; i < flat.length; i += 2) pts.push([flat[i], flat[i + 1]]);
    if (pts.length < 2) continue;
    out.roads.push({ pts, hw, major: MAJOR.test(hw), bridge: !!br, oneway: !!ow || /motorway/.test(hw), name: D.names[ni] });
  }
  // landmarks first, so their ids are stable and small
  D.landmarks.forEach((l, i) => {
    out.buildings.push({ ring: l.r, area: Math.abs(ringArea(l.r)), h: l.h, minH: 0, known: true, landmark: true, dome: l.dome,
      id: 900000 + i * 37, name: l.n, en: l.en });
  });
  out.landmarkCount = D.landmarks.length;
  for (const [x, z, w, d, ang, h, zi] of D.buildings) {
    const a = ang * Math.PI / 180, ux = Math.cos(a), uz = Math.sin(a);
    const ring = [[-w / 2, -d / 2], [w / 2, -d / 2], [w / 2, d / 2], [-w / 2, d / 2]].map(([p, q]) => [x + ux * p - uz * q, z + uz * p + ux * q]);
    out.buildings.push({ ring, area: w * d, h, minH: 0, known: false, id: Math.round(x * 7 + z * 13) & 0xffffff, name: "", zone: D.zones[zi] });
  }
  return out;
}

''')

# ---------- ground texture from embedded mask ----------
a = src.index('/* ---------------- Ground texture')
b = src.index('  g.globalCompositeOperation = "lighten";', a)
src = src[:a] + '''/* ---------------- Ground texture (class map) ----------------
   R = water, G = vegetation, B = road (≈64 path, ≈140 minor, 255 major) */
function loadMask() {
  return new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = rej; im.src = "data:image/png;base64," + D.mask; });
}
function buildGroundTexture(osm, R, S, maskImg) {
  const cv = document.createElement("canvas"); cv.width = cv.height = S;
  const g = cv.getContext("2d");
  const k = S / (2 * R);
  const X = p => (p[0] + R) * k, Z = p => (p[1] + R) * k;
  g.fillStyle = "#000"; g.fillRect(0, 0, S, S);
  g.imageSmoothingEnabled = true; g.imageSmoothingQuality = "high";
  g.drawImage(maskImg, 0, 0, S, S);
''' + src[b:]
# drop the areas / water polygon fills (not in the embedded data)
src = re.sub(r'  const poly = \(o, inn, color\) => \{.*?\n  for \(const w of osm\.water\) poly\(w\.outers, w\.inners, w\.wet \? "rgb\(200,160,0\)" : "rgb\(255,0,0\)"\);\n',
             '', src, flags=re.S)
src = src.replace('W = { motorway: 24, trunk: 20, primary: 15, secondary: 12, tertiary: 9, motorway_link: 8, trunk_link: 8, primary_link: 7,\n    secondary_link: 7, tertiary_link: 6, residential: 6, unclassified: 6, living_street: 5, pedestrian: 4, footway: 2, cycleway: 2.2, path: 1.8 };',
                  'W = { motorway: 24, trunk: 22, primary: 18, secondary: 14, tertiary: 10, motorway_link: 8, trunk_link: 8, primary_link: 7,\n    secondary_link: 7, tertiary_link: 6, residential: 7, unclassified: 7, living_street: 6, service: 4, pedestrian: 4, footway: 2, cycleway: 2.2, path: 1.8, steps: 1.6, track: 2 };')
src = src.replace('const order = ["path", "footway", "cycleway", "pedestrian", "living_street",',
                  'const order = ["track", "steps", "path", "footway", "cycleway", "pedestrian", "service", "living_street",')
src = src.replace('const isPath = /^(path|footway|cycleway)$/.test(hw)', 'const isPath = /^(path|footway|cycleway|steps|track)$/.test(hw)')

# old helper duplicates (ringArea / centroid lived in Parsing section which is gone) — ok.
open(sys.argv[2], "w", encoding="utf-8").write(src)
print("ok")
