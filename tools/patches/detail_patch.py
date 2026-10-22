"""City detail pass 2 + collapsible title card. src4.html -> src5.html"""
import sys

s = open(sys.argv[1], encoding="utf-8").read()


def rep(a, b, cnt=1):
    global s
    assert a in s, "MISSING: " + a[:100]
    s = s.replace(a, b, cnt)


# =================================================================== A. collapsible title card
rep("""#plate .eyebrow { font-family: var(--f-mono); font-size: 11px; letter-spacing: .12em; color: var(--ink-dim); text-transform: uppercase; }""",
    """#plate .eyebrow { font-family: var(--f-mono); font-size: 11px; letter-spacing: .12em; color: var(--ink-dim); text-transform: uppercase; margin-right: 58px; }
#plate .plate-x { position: absolute; top: 8px; right: 8px; pointer-events: auto; padding: 7px 10px; font-size: 12px; border: 1px solid var(--panel-line); }
#plate.collapsed { padding: 8px 12px 8px 14px; }
#plate.collapsed .eyebrow, #plate.collapsed .coords, #plate.collapsed #stats, #plate.collapsed #sky, #plate.collapsed #hint { display: none; }
#plate.collapsed h1 { font-size: 18px; margin: 2px 64px 2px 0; }
#plate.collapsed #credit { font-size: 10.5px; margin-top: 2px; }""")
rep("""<header id="plate" class="panel">""", """<header id="plate" class="panel">
  <button class="btn plate-x" id="bPlate" type="button" aria-expanded="true" aria-controls="plate">收起</button>""")
rep("""$("#tod").addEventListener("input", e => setTod(+e.target.value, false));""", """$("#tod").addEventListener("input", e => setTod(+e.target.value, false));
function setPlate(open) {
  $("#plate").classList.toggle("collapsed", !open);
  $("#bPlate").textContent = open ? "收起" : "展开";
  $("#bPlate").setAttribute("aria-expanded", String(open));
  try { localStorage.setItem("szbay.plate", open ? "1" : "0"); } catch (e) {}
}
$("#bPlate").onclick = () => setPlate($("#plate").classList.contains("collapsed"));
(() => { let v = null; try { v = localStorage.getItem("szbay.plate"); } catch (e) {} setPlate(v === null ? innerWidth > 760 : v === "1"); })();""")

# =================================================================== H. rooftop details
rep("""    boxAt(g, x, z, Math.min(w, d) * 0.35, Math.min(w, d) * 0.28, ang, h, h + 4.5, col, 1, bid);""",
    """    boxAt(g, x, z, Math.min(w, d) * 0.35, Math.min(w, d) * 0.28, ang, h, h + 4.5, col, 1, bid);
    if (rnd() < 0.35) { const ax = x + Math.cos(ang) * w * 0.2, az = z + Math.sin(ang) * w * 0.2; frustum(g, circleRing(ax, az, 0.35, 6), circleRing(ax, az, 0.08, 6), h + 4.5, h + 12 + rnd() * 12, METAL, 5, bid, { cap: false }); }
    if (rnd() < 0.25) { const tx2 = x - Math.cos(ang) * w * 0.25, tz2 = z - Math.sin(ang) * w * 0.25; prism(g, circleRing(tx2, tz2, 2.2, 10), h, h + 3.2, [0.72, 0.72, 0.70], 3, bid, { smooth: true }); }""")
rep("""      if (rnd() < 0.35) { const tc = [0.30, 0.40, 0.60]; prism(g, circleRing(x + (rnd() - 0.5) * w * 0.5, z + (rnd() - 0.5) * d * 0.5, 1.2, 8), h, h + 2.2, tc, 5, bid); }""",
    """      if (rnd() < 0.35) { const tc = [0.30, 0.40, 0.60]; prism(g, circleRing(x + (rnd() - 0.5) * w * 0.5, z + (rnd() - 0.5) * d * 0.5, 1.2, 8), h, h + 2.2, tc, 5, bid); }
      if (rnd() < 0.4) { const c = Math.cos(ang), s2 = Math.sin(ang), n = 2 + (rnd() * 3 | 0); for (let k = 0; k < n; k++) { const v = (k - (n - 1) / 2) * 2.4; boxAt(g, x - s2 * v + c * w * 0.15, z + c * v + s2 * w * 0.15, w * 0.45, 1.8, ang, h + 0.4, h + 0.9, [0.10, 0.14, 0.26], 5, bid); } }
      if (rnd() < 0.2) prism(g, rectRing(x, z, w * 0.8, d * 0.8, ang), h, h + 0.4, [0.30, 0.45, 0.22], 11, bid);""")
rep("""tint.map(v => v * 1.15), 2, bid, { capCol: [0.50, 0.55, 0.50] });""",
    """tint.map(v => v * 1.15), 2, bid, { capCol: rnd() < 0.55 ? [0.30, 0.44, 0.24] : [0.55, 0.56, 0.54], capMat: 11 });""")
rep("""  if (h > 140) beacons.push([cx, h + (crown >= 0.3 && crown < 0.5 && h > 120 ? 50 : 3), cz, rnd() * 6]);""",
    """  if (h > 110 && rnd() < 0.35) prism(g, scaleRing(topR, 1.006, cx, cz), bodyTop - 7, bodyTop - 1.5, tint, 7, bid, { cap: false });
  if (h > 140) beacons.push([cx, h + (crown >= 0.3 && crown < 0.5 && h > 120 ? 50 : 3), cz, rnd() * 6]);
  if (zone === "cbd" || zone === "tech") craneCands.push({ x, z, w, d, ang, h });""")
rep("""const beacons = [];           // [x,y,z,phase] aircraft warning lights""", """const beacons = [];           // [x,y,z,phase] aircraft warning lights
const craneCands = [];""")

# =================================================================== E. sports grounds / pools — mesh shader materials
rep("""  } else if (m == 11) {
    alb = vCol * (0.8 + 0.4 * vnoise(vec2(vUv.x * 0.07, vPos.z * 0.07 + vPos.y * 0.2)));
    glassAmt = 0.0;
  }""", """  } else if (m == 11) {
    alb = vCol * (0.8 + 0.4 * vnoise(vec2(vUv.x * 0.07, vPos.z * 0.07 + vPos.y * 0.2)));
    glassAmt = 0.0;
  } else if (m >= 12 && m <= 16) {
    vec2 q = vUv; float L = vCol.r * 200.0, W = vCol.g * 200.0;
    float fq = max(fwidth(q.x), fwidth(q.y)) + 0.01;
    float lw = 0.07 + fq * 0.6;
    float ln = 0.0;
    vec3 grassA = vec3(0.19, 0.40, 0.15), grassB = vec3(0.23, 0.47, 0.18);
    if (m == 12 || m == 16) {
      float hl = (m == 16 ? 50.0 : L / 2.0 - 2.0), hw = (m == 16 ? 32.0 : W / 2.0 - 2.0), sc = hw / 32.0;
      bool infield = true;
      if (m == 16) {
        float dd = length(vec2(max(abs(q.x) - 42.2, 0.0), q.y)) - 36.5;
        if (dd > 0.0) {
          infield = false;
          if (dd < 9.76) { alb = vec3(0.60, 0.23, 0.17) * (0.9 + 0.15 * vnoise(q * 0.8)); float lane = abs(fract(dd / 1.22 + 0.5) - 0.5) * 1.22; ln = 1.0 - smoothstep(lw * 0.6, lw * 0.6 + fq, lane); }
          else alb = vec3(0.46, 0.47, 0.43);
        }
      }
      if (infield) {
        alb = mix(grassA, grassB, step(0.5, fract(q.x / (hl / 6.0))));
        float ax = abs(q.x), ay = abs(q.y);
        float L1 = 1.0 - smoothstep(lw, lw + fq, abs(ax - hl)) ; L1 *= step(ay, hw + lw);
        float L2 = (1.0 - smoothstep(lw, lw + fq, abs(ay - hw))) * step(ax, hl + lw);
        float L3 = (1.0 - smoothstep(lw, lw + fq, ax)) * step(ay, hw);
        float L4 = 1.0 - smoothstep(lw, lw + fq, abs(length(q) - 9.15 * sc));
        float pd = 16.5 * sc, pw = 20.15 * sc, gd = 5.5 * sc, gw = 9.16 * sc;
        float L5 = (1.0 - smoothstep(lw, lw + fq, abs(ax - (hl - pd)))) * step(ay, pw) + (1.0 - smoothstep(lw, lw + fq, abs(ay - pw))) * step(hl - pd, ax) * step(ax, hl);
        float L6 = (1.0 - smoothstep(lw, lw + fq, abs(ax - (hl - gd)))) * step(ay, gw) + (1.0 - smoothstep(lw, lw + fq, abs(ay - gw))) * step(hl - gd, ax) * step(ax, hl);
        ln = max(ln, clamp(max(max(L1, L2), max(max(L3, L4), max(L5, L6))), 0.0, 1.0));
        if (ax > hl + 1.0 || ay > hw + 1.0) alb = mix(alb, vec3(0.30, 0.45, 0.22), 0.4);
      }
    } else if (m == 14) {
      float hl = 14.0, hw = 7.5, ax = abs(q.x), ay = abs(q.y);
      alb = (ax < hl && ay < hw) ? vec3(0.20, 0.40, 0.56) : vec3(0.26, 0.44, 0.32);
      if (ax > hl - 5.8 && ax < hl && ay < 2.45) alb = vec3(0.66, 0.24, 0.18);
      float B = (1.0 - smoothstep(lw, lw + fq, abs(ax - hl))) * step(ay, hw) + (1.0 - smoothstep(lw, lw + fq, abs(ay - hw))) * step(ax, hl);
      float C = (1.0 - smoothstep(lw, lw + fq, ax)) * step(ay, hw) + (1.0 - smoothstep(lw, lw + fq, abs(length(q) - 1.8)));
      float T3 = (1.0 - smoothstep(lw, lw + fq, abs(length(vec2(ax - (hl - 1.575), q.y)) - 6.75))) * step(ax, hl - 1.575 + 0.01 + 6.75) * step(hl - 7.0, ax);
      float K = (1.0 - smoothstep(lw, lw + fq, abs(ax - (hl - 5.8)))) * step(ay, 2.45) + (1.0 - smoothstep(lw, lw + fq, abs(ay - 2.45))) * step(hl - 5.8, ax) * step(ax, hl);
      ln = clamp(B + C + T3 + K, 0.0, 1.0);
    } else if (m == 15) {
      float hl = 11.885, hw = 5.485, sw = 4.115, ax = abs(q.x), ay = abs(q.y);
      alb = (ax < hl && ay < hw) ? vec3(0.17, 0.38, 0.44) : vec3(0.30, 0.46, 0.38);
      float B = (1.0 - smoothstep(lw, lw + fq, abs(ax - hl))) * step(ay, hw) + (1.0 - smoothstep(lw, lw + fq, abs(ay - hw))) * step(ax, hl) + (1.0 - smoothstep(lw, lw + fq, abs(ay - sw))) * step(ax, hl);
      float Sv = (1.0 - smoothstep(lw, lw + fq, abs(ax - 6.4))) * step(ay, sw) + (1.0 - smoothstep(lw, lw + fq, ay)) * step(ax, 6.4);
      ln = clamp(B + Sv, 0.0, 1.0);
      alb = mix(alb, vec3(0.08), (1.0 - smoothstep(0.08, 0.08 + fq, ax)) * step(ay, hw + 0.9) * 0.8);
    } else if (m == 13) {
      float ax = abs(q.x), ay = abs(q.y);
      bool water = ax < 12.5 && ay < 5.5;
      alb = vec3(0.80, 0.78, 0.72);
      if (water) {
        float lane = abs(fract(q.y / 2.2 + 0.5) - 0.5) * 2.2;
        float caus = vnoise(q * 1.3 + uTime * 0.6) * vnoise(q * 1.9 - uTime * 0.5);
        alb = mix(vec3(0.10, 0.50, 0.66), vec3(0.06, 0.26, 0.48), (1.0 - smoothstep(0.1, 0.1 + fq, lane)) * step(ax, 11.5));
        alb += vec3(0.35, 0.45, 0.45) * smoothstep(0.25, 0.6, caus) * 0.5;
        emis += vec3(0.15, 0.65, 0.85) * 0.9 * uNight;
        vec3 R = reflect(-V, vec3(0.0, 1.0, 0.0)); float F = 0.02 + 0.98 * pow(1.0 - max(V.y, 0.0), 5.0);
        emis += skyColor(R) * F * 0.6 * (1.0 - uNight * 0.7);
      }
    }
    alb = mix(alb, vec3(0.92), ln * (1.0 - smoothstep(700.0, 1600.0, distance(vPos, uCam))));
    glassAmt = 0.0;
  }""")
rep("""  if (roof && (m == 0 || m == 1 || m == 2 || m == 4)) alb = vCol;""", """  if (roof && (m == 0 || m == 1 || m == 2 || m == 4)) alb = vCol;
  if (roof && m == 11) alb = vCol * (0.8 + 0.4 * vnoise(vPos.xz * 0.15));""")

# =================================================================== B/C/D. new shaders: roads, instanced props (cars, street lights)
rep("""/* sea of clouds under the island */""", """/* road surfaces with lane markings */
const roadVS = HEAD + `
layout(location=0) in vec3 aPos; layout(location=1) in vec4 aA; layout(location=2) in vec4 aB;
uniform mat4 uVP; uniform mat4 uLightVP; out vec3 vPos; out vec4 vA; out vec4 vB; out vec4 vLight;
void main(){ vPos = aPos; vA = aA; vB = aB; vLight = uLightVP * vec4(aPos + vec3(0.0, 0.6, 0.0), 1.0); gl_Position = uVP * vec4(aPos, 1.0); }`;
const roadFS = HEAD + COMMON + `
in vec3 vPos; in vec4 vA; in vec4 vB; in vec4 vLight; out vec4 o;
float band(float x, float c, float w, float fw){ return 1.0 - smoothstep(w * 0.5, w * 0.5 + fw, abs(x - c)); }
void main(){
  float rr = length(vPos.xz); if (rr > isleR(atan(vPos.z, vPos.x))) discard;
  float across = vA.x, along = vA.y, dj = min(vA.z, vA.w), hw = vB.x, lanes = vB.y, ow = vB.z, kind = vB.w;
  float fwA = fwidth(across) + 0.02, fwL = fwidth(along) + 0.02;
  float dist = distance(vPos, uCam);
  float fade = 1.0 - smoothstep(450.0, 1500.0, dist);
  float n1 = vnoise(vPos.xz * 0.35), n2 = vnoise(vPos.xz * 0.04);
  float sh = shadowAt(vLight) * cloudShade(vPos.xz);
  vec3 amb = skyColor(vec3(0, 1, 0)) * 0.62 * (1.0 - uNight * 0.8);
  vec3 lightL = amb + uLightCol * max(uLightDir.y, 0.0) * sh;
  vec3 c;
  if (kind < -0.5) {
    float curb = band(abs(across), hw - 3.05, 0.3, fwA);
    vec2 tile = abs(fract(vec2(across, along) / 0.9) - 0.5);
    float grout = (1.0 - smoothstep(0.42, 0.48, max(tile.x, tile.y))) ;
    c = vec3(0.58, 0.56, 0.52) * (0.92 + 0.12 * n2) * mix(1.0, 0.93 + 0.07 * grout, fade);
    c = mix(c, vec3(0.74, 0.73, 0.70), curb);
    c = c * lightL + vec3(1.0, 0.62, 0.3) * 0.08 * uNight;
  } else {
    vec3 asph = vec3(0.16, 0.165, 0.175) * (0.86 + 0.18 * n1 * fade + 0.12 * n2);
    float lw = ow > 0.5 ? (2.0 * hw) / max(lanes, 1.0) : hw / max(lanes, 1.0);
    float m = 0.0; vec3 mc = vec3(0.88);
    if (lanes > 0.5) {
      float dash = step(fract(along / 12.0), 0.5);
      float inJ = smoothstep(13.0, 15.0, dj);
      if (ow < 0.5) {
        float yl = max(band(across, -0.2, 0.15, fwA), band(across, 0.2, 0.15, fwA)) * inJ;
        if (yl > 0.01) mc = vec3(0.95, 0.72, 0.15);
        m = max(m, yl);
        for (int k = 1; k < 3; k++) { if (float(k) >= lanes) break; float p = float(k) * lw; m = max(m, max(band(across, p, 0.15, fwA), band(across, -p, 0.15, fwA)) * dash * inJ); }
      } else {
        for (int k = 1; k < 4; k++) { if (float(k) >= lanes) break; float p = -hw + float(k) * lw; m = max(m, band(across, p, 0.15, fwA) * dash * inJ); }
      }
      float edge = band(abs(across), hw - 0.45, 0.15, fwA) * inJ;
      if (edge > m) mc = vec3(0.88);
      m = max(m, edge);
      float zebra = step(5.0, dj) * step(dj, 10.0) * step(0.5, fract(across / 1.1)) * step(abs(across), hw - 0.6);
      float stop = band(dj, 11.6, 0.45, fwL) * step(abs(across), hw - 0.6);
      if (max(zebra, stop) > m) mc = vec3(0.90);
      m = max(m, max(zebra, stop));
    }
    m *= fade * 0.92;
    c = mix(asph, mc, m) * lightL;
    vec3 V = normalize(uCam - vPos);
    float F = pow(1.0 - max(V.y, 0.0), 5.0);
    c += skyColor(reflect(-V, vec3(0, 1, 0))) * F * 0.12 * (1.0 - uNight);
    float major = step(1.5, lanes);
    c += vec3(1.0, 0.6, 0.25) * uNight * (0.20 + 0.28 * major) * (0.75 + 0.3 * n2);
    c += mc * m * uNight * 0.3;
  }
  o = vec4(fogIt(c, vPos), 1.0);
}`;
/* instanced props: cars, buses, street lights */
const instVS = HEAD + `
layout(location=0) in vec3 aPos; layout(location=1) in vec3 aNrm; layout(location=2) in vec3 aCol; layout(location=3) in float aPart;
layout(location=4) in vec4 aI0; layout(location=5) in vec4 aI1;
uniform mat4 uVP; uniform mat4 uLightVP; uniform vec3 uCam; uniform float uFar; uniform float uNOff; uniform float uRise;
out vec3 vPos; out vec3 vNrm; out vec3 vCol; out vec4 vLight; flat out float vPart;
void main(){
  vec3 p = aPos; p.x *= aI1.w; if (aI1.w > 1.5) p.y *= 1.75;
  float c = cos(aI0.w), s = sin(aI0.w);
  vec3 q = vec3(p.x * c - p.z * s, p.y, p.x * s + p.z * c) + aI0.xyz;
  vec3 n = vec3(aNrm.x * c - aNrm.z * s, aNrm.y, aNrm.x * s + aNrm.z * c);
  float far = step(uFar, distance(aI0.xyz, uCam)) + step(uRise, 0.9);
  vPos = q; vNrm = n; vPart = aPart;
  vCol = aPart > 1.5 ? vec3(0.07, 0.09, 0.11) : (aPart > 0.5 ? aI1.rgb : aCol);
  vLight = uLightVP * vec4(q + n * uNOff, 1.0);
  gl_Position = far > 0.5 ? vec4(2.0, 2.0, 2.0, 1.0) : uVP * vec4(q, 1.0);
}`;
const instFS = HEAD + COMMON + `
in vec3 vPos; in vec3 vNrm; in vec3 vCol; in vec4 vLight; flat in float vPart; out vec4 o;
void main(){
  vec3 n = normalize(vNrm); vec3 V = normalize(uCam - vPos);
  float sh = shadowAt(vLight);
  vec3 amb = mix(vec3(0.24, 0.24, 0.23), skyColor(vec3(0, 1, 0)), n.y * 0.5 + 0.5) * (1.0 - uNight * 0.85);
  vec3 c = vCol * (amb * 0.8 + uLightCol * max(dot(n, uLightDir), 0.0) * sh);
  vec3 R = reflect(-V, n); float F = 0.04 + 0.96 * pow(1.0 - max(dot(n, V), 0.0), 5.0);
  float gloss = vPart > 0.5 ? 1.0 : 0.25;
  c += skyColor(R) * F * 0.55 * gloss * (1.0 - uNight * 0.7) + uLightCol * pow(max(dot(R, uLightDir), 0.0), 80.0) * sh * gloss;
  o = vec4(fogIt(c, vPos), 1.0);
}`;
const instShadowVS = HEAD + `
layout(location=0) in vec3 aPos; layout(location=4) in vec4 aI0; layout(location=5) in vec4 aI1;
uniform mat4 uLightVP;
void main(){ vec3 p = aPos; p.x *= aI1.w; if (aI1.w > 1.5) p.y *= 1.75; float c = cos(aI0.w), s = sin(aI0.w);
  gl_Position = uLightVP * vec4(vec3(p.x * c - p.z * s, p.y, p.x * s + p.z * c) + aI0.xyz, 1.0); }`;

/* sea of clouds under the island */""")
rep("""sea: compile(seaVS, seaFS), fall: compile(fallVS, fallFS),""",
    """sea: compile(seaVS, seaFS), fall: compile(fallVS, fallFS),
  road: compile(roadVS, roadFS), inst: compile(instVS, instFS), instShadow: compile(instShadowVS, emptyFS),""")

# =================================================================== JS builders: roads, features, props
rep("""/* ---------------- bridges + traffic ---------------- */""", """/* ---------------- road surfaces ---------------- */
const ROADW = { motorway: 24, trunk: 22, primary: 18, secondary: 14, tertiary: 10, motorway_link: 8, trunk_link: 8, primary_link: 7, secondary_link: 7, tertiary_link: 6, residential: 7, unclassified: 7, living_street: 6, service: 4.5 };
const LANES = { motorway: 3, trunk: 3, primary: 2, secondary: 2, tertiary: 1, residential: 1, unclassified: 1, motorway_link: 1, trunk_link: 1, primary_link: 1, secondary_link: 1, tertiary_link: 1, living_street: 0, service: 0 };
function buildRoadMesh(osm) {
  const roads = osm.roads.filter(r => ROADW[r.hw] && !r._ribbon);
  const key = p => Math.round(p[0] * 0.5) + "," + Math.round(p[1] * 0.5);
  const deg = new Map();
  for (const r of roads) r.pts.forEach((p, i) => { const k = key(p); deg.set(k, (deg.get(k) || 0) + (i === 0 || i === r.pts.length - 1 ? 1 : 2)); });
  const v = [];
  for (const pass of [0, 1]) {               // 0: sidewalks underneath, 1: carriageways
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
      const kind = pass === 0 ? -1 : 1;
      const V = (i, sd) => { const p = P[i], q = NR[i]; v.push(p[0] + q[0] * hw * sd, 0, p[1] + q[1] * hw * sd, hw * sd, cum[i], pj[i], nj[i], hw, lanes, r.oneway ? 1 : 0, kind); };
      for (let i = 0; i + 1 < n; i++) { V(i, -1); V(i, 1); V(i + 1, 1); V(i, -1); V(i + 1, 1); V(i + 1, -1); }
    }
  }
  return new Float32Array(v);
}

/* ---------------- sports grounds, courts, pools ---------------- */
function buildFeatures() {
  const g = new Geo();
  const DIM = { 0: [104, 68, 12], 1: [60, 40, 12], 2: [30, 17, 14], 3: [31, 16, 13], 4: [34, 18, 15], 5: [176, 100, 16] };
  let n = 0;
  for (const [k, x, z, angD] of (D.features || [])) {
    if (!inIsle(x, z, 60)) continue;
    const [L, W, mat] = DIM[k]; const a = angD * Math.PI / 180, c = Math.cos(a), s2 = Math.sin(a), y = 0.12;
    const col = [L / 200, W / 200, 0];
    const P = [[-L / 2, -W / 2], [L / 2, -W / 2], [L / 2, W / 2], [-L / 2, W / 2]].map(([u, w]) => g.vert(x + c * u - s2 * w, y, z + s2 * u + c * w, 0, 1, 0, col, u, w, -1, mat));
    g.quad(P[0], P[1], P[2], P[3]);
    if (k === 0 || k === 1 || k === 5) {   // goals
      const hl = k === 5 ? 50 : L / 2 - 2, gw = k === 1 ? 2.5 : 3.66;
      for (const sg of [1, -1]) boxAt(g, x + c * (hl + 0.8) * sg, z + s2 * (hl + 0.8) * sg, 1.6, gw * 2, a, 0, 2.44, [0.95, 0.95, 0.95], 8, -1);
    }
    n++;
  }
  return { V: new Float32Array(g.v), I: new Uint32Array(g.i), n };
}

/* ---------------- instanced props ---------------- */
function propTemplate(build) {
  const t = tplNew(); build(t);
  const v = [];
  for (let k = 0; k < t.p.length; k++) v.push(...t.p[k], ...t.n[k], ...t.c[k], t.m[k]);
  return { v: new Float32Array(v), i: new Uint16Array(t.i) };
}
function instVAO(tpl, inst, dynamic) {
  const vao = gl.createVertexArray(); gl.bindVertexArray(vao);
  const vb = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, vb); gl.bufferData(gl.ARRAY_BUFFER, tpl.v, gl.STATIC_DRAW);
  gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 40, 0);
  gl.enableVertexAttribArray(1); gl.vertexAttribPointer(1, 3, gl.FLOAT, false, 40, 12);
  gl.enableVertexAttribArray(2); gl.vertexAttribPointer(2, 3, gl.FLOAT, false, 40, 24);
  gl.enableVertexAttribArray(3); gl.vertexAttribPointer(3, 1, gl.FLOAT, false, 40, 36);
  const ib = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, ib); gl.bufferData(gl.ARRAY_BUFFER, inst, dynamic ? gl.DYNAMIC_DRAW : gl.STATIC_DRAW);
  gl.enableVertexAttribArray(4); gl.vertexAttribPointer(4, 4, gl.FLOAT, false, 32, 0); gl.vertexAttribDivisor(4, 1);
  gl.enableVertexAttribArray(5); gl.vertexAttribPointer(5, 4, gl.FLOAT, false, 32, 16); gl.vertexAttribDivisor(5, 1);
  const eb = gl.createBuffer(); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, eb); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, tpl.i, gl.STATIC_DRAW);
  gl.bindVertexArray(null);
  return { vao, ib, count: tpl.i.length, n: inst.length / 8 };
}
const LAMPS = [];
function streetLights(osm) {
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

/* ---------------- bridges + traffic ---------------- */""")

# traffic: car kinds + instance buffer + two light points per car
rep("""    cars.push({ l, s: Math.random() * l.L, dir, lane, v: (l.r.major ? 14 : 9) * (0.7 + Math.random() * 0.6), hue: Math.random() });""",
    """    const h = Math.random(), bus = l.r.major && h < 0.07;
    const PAL = [[0.92, 0.92, 0.92], [0.92, 0.92, 0.92], [0.07, 0.07, 0.08], [0.62, 0.63, 0.65], [0.35, 0.36, 0.38], [0.60, 0.08, 0.06], [0.10, 0.15, 0.30], [0.80, 0.78, 0.72]];
    const col = bus ? [0.18, 0.55, 0.34] : h < 0.22 ? [0.16, 0.36, 0.78] : PAL[(Math.random() * PAL.length) | 0];
    cars.push({ l, s: Math.random() * l.L, dir, lane, v: (l.r.major ? 14 : 9) * (0.7 + Math.random() * 0.6) * (bus ? 0.75 : 1), hue: h, col, len: bus ? 2.6 : 1 });""")
rep("""  return { cars, buf: new Float32Array(cars.length * 7), hAt: bridges.hAt };""",
    """  return { cars, buf: new Float32Array(cars.length * 14), inst: new Float32Array(cars.length * 8), hAt: bridges.hAt };""")
rep("""    const o = i * 7;
    b[o] = a[0] + (q[0] - a[0]) * f - dz * c.lane * side; b[o + 2] = a[1] + (q[1] - a[1]) * f + dx * c.lane * side;
    b[o + 1] = (l.ribbon ? T.hAt(c.s, l.L) : 0) + 1.6;
    if (night) { if (c.dir > 0) { b[o + 3] = 2.2; b[o + 4] = 2.0; b[o + 5] = 1.6; } else { b[o + 3] = 2.0; b[o + 4] = 0.25; b[o + 5] = 0.12; } b[o + 6] = 5; }
    else { const h = c.hue; b[o + 3] = h < .3 ? 0.95 : h < .55 ? 0.25 : h < .75 ? 0.12 : 0.75; b[o + 4] = h < .3 ? 0.95 : h < .55 ? 0.27 : h < .75 ? 0.35 : 0.2; b[o + 5] = h < .3 ? 0.95 : h < .55 ? 0.3 : h < .75 ? 0.6 : 0.15; b[o + 6] = 4.2; }""",
    """    const x = a[0] + (q[0] - a[0]) * f - dz * c.lane * side, z = a[1] + (q[1] - a[1]) * f + dx * c.lane * side;
    const y = (l.ribbon ? T.hAt(c.s, l.L) : 0);
    const fx = dx * c.dir, fz = dz * c.dir, half = 2.2 * c.len;
    const I = T.inst, j = i * 8;
    I[j] = x; I[j + 1] = y + 0.02; I[j + 2] = z; I[j + 3] = Math.atan2(fz, fx); I[j + 4] = c.col[0]; I[j + 5] = c.col[1]; I[j + 6] = c.col[2]; I[j + 7] = c.len;
    const o = i * 14;
    b[o] = x + fx * half; b[o + 1] = y + 0.8; b[o + 2] = z + fz * half; b[o + 3] = 2.4; b[o + 4] = 2.2; b[o + 5] = 1.8; b[o + 6] = night ? 4.5 : 0;
    b[o + 7] = x - fx * half; b[o + 8] = y + 0.9; b[o + 9] = z - fz * half; b[o + 10] = 2.2; b[o + 11] = 0.2; b[o + 12] = 0.1; b[o + 13] = night ? 3.5 : 0;""")
rep("""    gl.bindVertexArray(S.carVAO); gl.drawArrays(gl.POINTS, 0, S.traffic.cars.length);""",
    """    gl.bindVertexArray(S.carVAO); gl.drawArrays(gl.POINTS, 0, S.traffic.cars.length * 2);""")
rep("""  if (S.traffic.cars.length) {
    gl.bindBuffer(gl.ARRAY_BUFFER, S.carBuf);""", """  if (S.traffic.cars.length && L.night > 0.5) {
    gl.bindBuffer(gl.ARRAY_BUFFER, S.carBuf);""")

# =================================================================== scene build: roads, features, props, water lookup
rep("""  const cv = document.createElement("canvas"); cv.width = cv.height = 1024;
  const c2 = cv.getContext("2d"); c2.drawImage(maskImg, 0, 0, 1024, 1024);
  const md = c2.getImageData(0, 0, 1024, 1024).data;
  const waterAt = (x, z) => { const i = clamp(Math.floor((x + D.R) / (2 * D.R) * 1024), 0, 1023), j = clamp(Math.floor((z + D.R) / (2 * D.R) * 1024), 0, 1023); return md[(j * 1024 + i) * 4] > 127; };""",
    """  const waterAt = makeWater(maskImg); S.waterAt = waterAt;""")
rep("""const ISLETS = [];""", """const ISLETS = [];
function makeWater(maskImg) {
  const cv = document.createElement("canvas"); cv.width = cv.height = 1024;
  const c2 = cv.getContext("2d"); c2.drawImage(maskImg, 0, 0, 1024, 1024);
  const md = c2.getImageData(0, 0, 1024, 1024).data;
  return (x, z) => { const i = clamp(Math.floor((x + D.R) / (2 * D.R) * 1024), 0, 1023), j = clamp(Math.floor((z + D.R) / (2 * D.R) * 1024), 0, 1023); return md[(j * 1024 + i) * 4] > 127; };
}""")
rep("""  loader.show("正在种树、放飞机", "行道树、云层、航班、直升机、白鹭、无人机"); await sleep(30);""",
    """  loader.show("正在铺路", "车道线、斑马线、人行道、路灯与球场"); await sleep(30);
  const rv = buildRoadMesh(osm);
  S.roadVAO = gl.createVertexArray(); gl.bindVertexArray(S.roadVAO);
  const rb = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, rb); gl.bufferData(gl.ARRAY_BUFFER, rv, gl.STATIC_DRAW);
  gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 44, 0);
  gl.enableVertexAttribArray(1); gl.vertexAttribPointer(1, 4, gl.FLOAT, false, 44, 12);
  gl.enableVertexAttribArray(2); gl.vertexAttribPointer(2, 4, gl.FLOAT, false, 44, 28);
  gl.bindVertexArray(null);
  S.roadCount = rv.length / 11;
  const ft = buildFeatures(); S.feat = meshVAO(ft.V, ft.I); S.featN = ft.n;
  S.lampVAO = instVAO(TPL.lamp, streetLights(osm), false);
  loader.show("正在种树、放飞机", "行道树、云层、航班、直升机、白鹭、无人机"); await sleep(30);""")
rep("""  S.traffic = buildTraffic(osm, bridges);""", """  S.traffic = buildTraffic(osm, bridges);
  S.carInst = instVAO(TPL.car, S.traffic.inst, true);""")
rep("""<b>${FALLS.groups.length}</b> 道瀑布 · <b>${ISLETS.length}</b> 座小浮岛`;""",
    """<b>${FALLS.groups.length}</b> 道瀑布 · <b>${ISLETS.length}</b> 座小浮岛 · <b>${fmt(LAMPS.length)}</b> 盏路灯 · <b>${S.featN}</b> 处球场泳池`;""")

# prop templates (cars, lamps, crane, boats)
rep("""  TPL.quad = quad;
})();""", """  TPL.quad = quad;
  TPL.car = propTemplate(t => {
    tplBox(t, 0, 0.72, 0, 4.4, 0.72, 1.8, [1, 1, 1], 1);
    tplBox(t, -0.25, 1.36, 0, 2.5, 0.58, 1.62, [0, 0, 0], 2);
    for (const [a, b] of [[1.4, 0.82], [1.4, -0.82], [-1.4, 0.82], [-1.4, -0.82]]) tplBox(t, a, 0.32, b, 0.64, 0.64, 0.24, [0.05, 0.05, 0.05], 0);
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
})();""")

# cranes + boats setup
rep("""  // drone show over the bay
  AIR.show = initShow();""", """  // tower cranes on CBD / tech-park construction sites
  AIR.cranes = [];
  const RC = rng(321);
  const cand = craneCands.filter(c => c.h > 60 && c.h < 240 && inIsle(c.x, c.z, 80));
  for (let k = 0; k < cand.length && AIR.cranes.length < 12; k++) {
    if (RC() > 0.09) continue;
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
  // drone show over the bay
  AIR.show = initShow();""")
rep("""  // static aircraft warning beacons""", """  // tower cranes
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
  // street lights
  if (night > 0.3) for (const p of LAMPS) light(p[0], p[1], p[2], 2.4 * night, 1.45 * night, 0.62 * night, 4.2);
  // static aircraft warning beacons""")
rep("""for (const [v, t] of [["plane", "跟随航班"], ["heli", "跟随直升机"], ["quad", "跟随配送无人机"], ["birds", "跟随白鹭群"], ["show", "无人机灯光秀（夜间）"]])""",
    """for (const [v, t] of [["plane", "跟随航班"], ["heli", "跟随直升机"], ["quad", "跟随配送无人机"], ["boat", "跟随渡轮"], ["birds", "跟随白鹭群"], ["show", "无人机灯光秀（夜间）"]])""")
rep("""    else if (f.kind === "birds") {""", """    else if (f.kind === "boat") { obj = (AIR.boats || []).find(b => b.type === "ferry") || (AIR.boats || [])[0]; back = 110; up = 30; }
    else if (f.kind === "birds") {""")

# =================================================================== render: shadow + main passes
rep("""    gl.bindVertexArray(S.island.vao); gl.drawElements(gl.TRIANGLES, S.island.count, gl.UNSIGNED_INT, 0);
    if (DYN.ni) {""", """    gl.bindVertexArray(S.island.vao); gl.drawElements(gl.TRIANGLES, S.island.count, gl.UNSIGNED_INT, 0);
    gl.bindVertexArray(S.feat.vao); gl.drawElements(gl.TRIANGLES, S.feat.count, gl.UNSIGNED_INT, 0);
    if (DYN.ni) {""")
rep("""    for (const T of S.trees) { gl.bindVertexArray(T.vao); gl.drawElementsInstanced(gl.TRIANGLES, T.count, gl.UNSIGNED_SHORT, 0, T.n); }
    gl.disable(gl.POLYGON_OFFSET_FILL);""", """    for (const T of S.trees) { gl.bindVertexArray(T.vao); gl.drawElementsInstanced(gl.TRIANGLES, T.count, gl.UNSIGNED_SHORT, 0, T.n); }
    if (S.rise > 0.9) {
      gl.useProgram(P.instShadow.p); gl.uniformMatrix4fv(P.instShadow.u.uLightVP, false, SM.vp);
      gl.bindVertexArray(S.lampVAO.vao); gl.drawElementsInstanced(gl.TRIANGLES, S.lampVAO.count, gl.UNSIGNED_SHORT, 0, S.lampVAO.n);
      gl.bindVertexArray(S.carInst.vao); gl.drawElementsInstanced(gl.TRIANGLES, S.carInst.count, gl.UNSIGNED_SHORT, 0, S.carInst.n);
    }
    gl.disable(gl.POLYGON_OFFSET_FILL);""")
rep("""  gl.enable(gl.POLYGON_OFFSET_FILL); gl.polygonOffset(2, 2);
  gl.bindVertexArray(S.ground.vao); gl.drawArrays(gl.TRIANGLES, 0, S.ground.count);
  gl.disable(gl.POLYGON_OFFSET_FILL);""", """  gl.enable(gl.POLYGON_OFFSET_FILL); gl.polygonOffset(4, 8);
  gl.bindVertexArray(S.ground.vao); gl.drawArrays(gl.TRIANGLES, 0, S.ground.count);
  // road surfaces: sidewalks were written first in the buffer, carriageways after → painter's order on the same plane
  gl.useProgram(P.road.p); setCommon(P.road, L, eye, now); gl.uniformMatrix4fv(P.road.u.uVP, false, vp);
  gl.polygonOffset(2, 4);
  gl.bindVertexArray(S.roadVAO); gl.drawArrays(gl.TRIANGLES, 0, S.roadCount);
  gl.disable(gl.POLYGON_OFFSET_FILL);""")
rep("""  gl.uniform1f(P.mesh.u.uSel, -1); gl.bindVertexArray(S.island.vao); gl.drawElements(gl.TRIANGLES, S.island.count, gl.UNSIGNED_INT, 0);""",
    """  gl.uniform1f(P.mesh.u.uSel, -1); gl.bindVertexArray(S.island.vao); gl.drawElements(gl.TRIANGLES, S.island.count, gl.UNSIGNED_INT, 0);
  gl.enable(gl.POLYGON_OFFSET_FILL); gl.polygonOffset(1, 2);
  gl.bindVertexArray(S.feat.vao); gl.drawElements(gl.TRIANGLES, S.feat.count, gl.UNSIGNED_INT, 0);
  gl.disable(gl.POLYGON_OFFSET_FILL);
  gl.uniform1f(P.mesh.u.uSel, S.sel);""")
rep("""  // waterfalls
  gl.enable(gl.BLEND); gl.depthMask(false); gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);""", """  // cars, buses, street lights
  gl.useProgram(P.inst.p); setCommon(P.inst, L, eye, now);
  gl.uniformMatrix4fv(P.inst.u.uVP, false, vp); gl.uniform1f(P.inst.u.uFar, 2600); gl.uniform1f(P.inst.u.uRise, S.rise);
  gl.bindBuffer(gl.ARRAY_BUFFER, S.carInst.ib); gl.bufferSubData(gl.ARRAY_BUFFER, 0, S.traffic.inst);
  gl.bindVertexArray(S.carInst.vao); gl.drawElementsInstanced(gl.TRIANGLES, S.carInst.count, gl.UNSIGNED_SHORT, 0, S.carInst.n);
  gl.uniform1f(P.inst.u.uFar, 1800);
  gl.bindVertexArray(S.lampVAO.vao); gl.drawElementsInstanced(gl.TRIANGLES, S.lampVAO.count, gl.UNSIGNED_SHORT, 0, S.lampVAO.n);
  // waterfalls
  gl.enable(gl.BLEND); gl.depthMask(false); gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);""")

# status line
rep("""    const items = [`瀑布 ${FALLS.groups.length} 道`,""", """    const items = [`瀑布 ${FALLS.groups.length} 道`, `船 ${(AIR.boats || []).length} 艘`, `塔吊 ${(AIR.cranes || []).length} 台`,""")

open(sys.argv[2], "w", encoding="utf-8").write(s)
print("ok")
