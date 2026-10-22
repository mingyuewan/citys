"""Turn the city into a floating sky island. src3.html -> src4.html"""
import sys

s = open(sys.argv[1], encoding="utf-8").read()


def rep(a, b, cnt=1):
    global s
    assert s.count(a) >= 1, "MISSING: " + a[:90]
    s = s.replace(a, b, cnt)


# ------------------------------------------------------------------ copy
rep('<div class="eyebrow">Shenzhen Bay · 南山后海 · Aerial 3D</div>', '<div class="eyebrow">Floating Island · 南山后海 · Aerial 3D</div>')
rep('<h1>深圳湾<span>·</span>空中城市</h1>', '<h1>深圳湾<span>·</span>空中之岛</h1>')

# ------------------------------------------------------------------ GLSL common: island outline
rep("uniform vec3 uCam; uniform float uFogDen; uniform float uTime; uniform vec2 uWind;",
    """uniform vec3 uCam; uniform float uFogDen; uniform float uTime; uniform vec2 uWind; uniform vec3 uIsle;
float isleR(float th){
  float b = uIsle.x * (1.0 + 0.05 * sin(3.0 * th + 1.0) + 0.035 * sin(5.0 * th + 2.0) + 0.02 * sin(9.0 * th + 0.5) + 0.012 * sin(17.0 * th + 3.1));
  float d = mod(th - uIsle.y + 3.14159265, 6.28318531) - 3.14159265;
  float l = uIsle.z * exp(-(d / 0.16) * (d / 0.16));
  float m = max(b, l); return m + 60.0 * log(exp((b - m) / 60.0) + exp((l - m) / 60.0));
}""")

# rise animation must not squash the island rock (mat >= 10)
rep("""  p.y *= max(g, 0.002);
  vPos = p; vNrm = aNrm; vCol = aCol; vUv = aUv; vBid = aBid; vMat = aMat;""",
    """  if (aMat < 9.5) p.y *= max(g, 0.002);
  vPos = p; vNrm = aNrm; vCol = aCol; vUv = aUv; vBid = aBid; vMat = aMat;""")
rep("""const shadowVS = HEAD + `
layout(location=0) in vec3 aPos;
uniform mat4 uLightVP; uniform float uRise; uniform float uMaxR;
void main(){ vec3 p = aPos; float d = length(p.xz) / uMaxR; float g = clamp(uRise * 1.6 - d * 0.6, 0.0, 1.0); g = g*g*(3.0-2.0*g); p.y *= max(g, 0.002); gl_Position = uLightVP * vec4(p, 1.0); }`;""",
    """const shadowVS = HEAD + `
layout(location=0) in vec3 aPos; layout(location=5) in float aMat;
uniform mat4 uLightVP; uniform float uRise; uniform float uMaxR;
void main(){ vec3 p = aPos; float d = length(p.xz) / uMaxR; float g = clamp(uRise * 1.6 - d * 0.6, 0.0, 1.0); g = g*g*(3.0-2.0*g); if (aMat < 9.5) p.y *= max(g, 0.002); gl_Position = uLightVP * vec4(p, 1.0); }`;""")

# rock / grass materials + cloud-sea bounce light from below
rep("""  amb += vec3(0.010, 0.012, 0.020) * uNight;""",
    """  amb += vec3(0.010, 0.012, 0.020) * uNight;
  amb += max(-n.y, 0.0) * (vec3(0.30, 0.32, 0.36) * (1.0 - uNight) + vec3(0.05, 0.03, 0.02) * uNight);""")
rep("""  if (roof && (m == 0 || m == 1 || m == 2 || m == 4)) alb = vCol;""",
    """  if (roof && (m == 0 || m == 1 || m == 2 || m == 4)) alb = vCol;
  if (m == 10) {
    float nA = vnoise(vec2(vUv.x * 0.02, vPos.y * 0.02)), nB = vnoise(vec2(vUv.x * 0.11, vPos.y * 0.13));
    float band = 0.5 + 0.5 * sin(vPos.y * 0.09 + nA * 7.0);
    alb = vCol * (0.78 + 0.22 * band) * (0.8 + 0.4 * nB);
    alb = mix(alb, vec3(0.46, 0.34, 0.24), smoothstep(-90.0, -10.0, vPos.y) * 0.6);
    float moss = smoothstep(0.35, 0.8, n.y) * smoothstep(0.4, 0.7, nA);
    alb = mix(alb, vec3(0.24, 0.36, 0.17), moss);
    glassAmt = 0.0;
  } else if (m == 11) {
    alb = vCol * (0.8 + 0.4 * vnoise(vec2(vUv.x * 0.07, vPos.z * 0.07 + vPos.y * 0.2)));
    glassAmt = 0.0;
  }""")

# trees: optional base height (islets), rise applies to the tree only
rep("""layout(location=0) in vec3 aPos; layout(location=1) in vec3 aNrm; layout(location=2) in float aPart; layout(location=3) in vec4 aInst;
uniform mat4 uVP;""", """layout(location=0) in vec3 aPos; layout(location=1) in vec3 aNrm; layout(location=2) in float aPart; layout(location=3) in vec4 aInst; layout(location=4) in float aY;
uniform mat4 uVP;""")
rep("""  p += vec3(aInst.x, 0.0, aInst.y);
  float d = length(p.xz) / uMaxR; float g = clamp(uRise * 1.6 - d * 0.6, 0.0, 1.0); g = g*g*(3.0-2.0*g);
  p.y *= max(g, 0.002);""", """  float d = length(aInst.xy) / uMaxR; float g = clamp(uRise * 1.6 - d * 0.6, 0.0, 1.0); g = g*g*(3.0-2.0*g);
  p.y *= max(g, 0.002);
  p += vec3(aInst.x, aY, aInst.y);""")
rep("""c += vec3(0.05, 0.04, 0.02) * uNight * smoothstep(9.0, 2.0, vPos.y);""", """c += vec3(0.05, 0.04, 0.02) * uNight * smoothstep(9.0, 2.0, vPos.y) * step(-1.0, vPos.y) * step(vPos.y, 30.0);""")
rep("""const treeShadowVS = HEAD + `
layout(location=0) in vec3 aPos; layout(location=3) in vec4 aInst;
uniform mat4 uLightVP; uniform float uRise; uniform float uMaxR;
void main(){ float s = aInst.z; vec3 p = aPos * vec3(s, s * (0.85 + aInst.w * 0.35), s); p += vec3(aInst.x, 0.0, aInst.y);
  float d = length(p.xz) / uMaxR; float g = clamp(uRise * 1.6 - d * 0.6, 0.0, 1.0); p.y *= max(g*g*(3.0-2.0*g), 0.002);
  gl_Position = uLightVP * vec4(p, 1.0); }`;""", """const treeShadowVS = HEAD + `
layout(location=0) in vec3 aPos; layout(location=3) in vec4 aInst; layout(location=4) in float aY;
uniform mat4 uLightVP; uniform float uRise; uniform float uMaxR;
void main(){ float s = aInst.z; vec3 p = aPos * vec3(s, s * (0.85 + aInst.w * 0.35), s);
  float d = length(aInst.xy) / uMaxR; float g = clamp(uRise * 1.6 - d * 0.6, 0.0, 1.0); p.y *= max(g*g*(3.0-2.0*g), 0.002);
  p += vec3(aInst.x, aY, aInst.y);
  gl_Position = uLightVP * vec4(p, 1.0); }`;""")

# ground: clip to the island outline, grassy lip at the rim
rep("""  vec2 uv = (vPos.xz + uR) / (2.0 * uR);""", """  float rr = length(vPos.xz), ir = isleR(atan(vPos.z, vPos.x));
  if (rr > ir) discard;
  vec2 uv = (vPos.xz + uR) / (2.0 * uR);""")
rep("""  float edge = smoothstep(uR, uR - 350.0, max(abs(vPos.x), abs(vPos.z)));""", """  float edge = 1.0;
  float lip = smoothstep(ir - 26.0, ir - 3.0, rr);""")
rep("""  vec3 lc = c * lightL;""", """  c = mix(c, vec3(0.26, 0.40, 0.19), lip * (1.0 - smoothstep(0.35, 0.75, w)));
  vec3 lc = c * lightL;""")

# ------------------------------------------------------------------ new shaders: cloud sea + waterfalls
rep("""/* searchlight beams */""", """/* sea of clouds under the island */
const seaVS = HEAD + `
layout(location=0) in vec2 aXZ; uniform mat4 uVP; uniform float uY; out vec3 vPos;
void main(){ vPos = vec3(aXZ.x, uY, aXZ.y); gl_Position = uVP * vec4(vPos, 1.0); }`;
const seaFS = HEAD + COMMON + `
in vec3 vPos; out vec4 o;
float fbm(vec2 p){ float a = 0.5, s = 0.0; for (int i = 0; i < 5; i++) { s += a * vnoise(p); p = p * 2.03 + vec2(17.1, 9.2); a *= 0.5; } return s; }
void main(){
  vec2 p = vPos.xz * 0.00017 + uWind * 0.00005;
  float f = fbm(p), f2 = fbm(p + uSunDir.xz * 0.006);
  float cov = smoothstep(0.36, 0.60, f);
  float shade = clamp(0.62 + (f - f2) * 7.0, 0.3, 1.25);
  vec3 sunC = mix(vec3(1.0, 0.98, 0.95), vec3(1.0, 0.66, 0.46), uGold);
  vec3 dayTop = mix(vec3(0.66, 0.70, 0.78), sunC, 0.55) * shade * (0.5 + 0.6 * clamp(uSunDir.y * 2.0 + 0.2, 0.0, 1.0));
  vec3 dayGap = mix(vec3(0.34, 0.46, 0.62), vec3(0.40, 0.36, 0.48), uGold);
  vec2 sh = vPos.xz + uSunDir.xz * (-vPos.y / max(uSunDir.y, 0.12));
  float inS = 1.0 - smoothstep(-350.0, 350.0, length(sh) - isleR(atan(sh.y, sh.x)) * 0.78);
  vec3 day = mix(dayGap, dayTop, cov) * mix(1.0, 0.55, inS);
  vec3 glow = vec3(0.36, 0.18, 0.08) * exp(-length(vPos.xz) / 3800.0);
  vec3 night = mix(vec3(0.008, 0.011, 0.024), vec3(0.04, 0.045, 0.065) * shade + glow, cov);
  o = vec4(fogIt(mix(day, night, uNight), vPos), 1.0);
}`;
const fallVS = HEAD + `
layout(location=0) in vec3 aPos; layout(location=1) in vec2 aUv; layout(location=2) in float aEdge;
uniform mat4 uVP; out vec3 vPos; out vec2 vUv; out float vEdge;
void main(){ vPos = aPos; vUv = aUv; vEdge = aEdge; gl_Position = uVP * vec4(aPos, 1.0); }`;
const fallFS = HEAD + COMMON + `
in vec3 vPos; in vec2 vUv; in float vEdge; out vec4 o;
void main(){
  float t = vUv.y;
  vec2 q = vec2(vUv.x * 0.07, t * 10.0 - uTime * 1.7);
  float s1 = vnoise(q), s2 = vnoise(q * vec2(2.7, 1.9) + 3.0), s3 = vnoise(vec2(vUv.x * 0.3, t * 30.0 - uTime * 4.0));
  float streak = s1 * 0.55 + s2 * 0.3 + s3 * 0.15;
  float a = (0.38 + 0.62 * smoothstep(0.3, 0.75, streak)) * (1.0 - smoothstep(0.5, 1.0, t)) * vEdge;
  a *= 0.15 + 0.85 * smoothstep(0.0, 0.01, t);
  vec3 base = mix(vec3(0.52, 0.70, 0.78), vec3(0.98), clamp(streak * 0.7 + t * 0.9, 0.0, 1.0));
  vec3 amb = skyColor(vec3(0.0, 1.0, 0.0)) * 0.85;
  vec3 c = base * (amb * 0.8 + uLightCol * 0.55) * (1.0 - uNight * 0.85);
  c += vec3(0.20, 0.70, 0.85) * uNight * (0.2 + 0.6 * streak) * (1.0 - t * 0.7);
  c = fogIt(c, vPos);
  o = vec4(c * a, a);
}`;

/* searchlight beams */""")
rep("""  cloud: compile(cloudVS, cloudFS), beam: compile(beamVS, beamFS),""",
    """  cloud: compile(cloudVS, cloudFS), beam: compile(beamVS, beamFS), sea: compile(seaVS, seaFS), fall: compile(fallVS, fallFS),""")

# ------------------------------------------------------------------ JS: island outline helpers (after math helpers)
rep("""const norm3 = v => { const l = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; };""",
    """const norm3 = v => { const l = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; };

/* ---------------- floating island outline ---------------- */
const ISLE = { R0: 2850, thH: 0, lobe: 3390 };
(() => { const hk = D.landmarks.find(l => l.k === "hanking"); if (hk) { ISLE.thH = Math.atan2(hk.c[1], hk.c[0]); ISLE.lobe = Math.hypot(hk.c[0], hk.c[1]) + 75; } })();
function wrapA(a) { while (a > Math.PI) a -= 2 * Math.PI; while (a < -Math.PI) a += 2 * Math.PI; return a; }
function isleR(th) {
  const b = ISLE.R0 * (1 + 0.05 * Math.sin(3 * th + 1) + 0.035 * Math.sin(5 * th + 2) + 0.02 * Math.sin(9 * th + 0.5) + 0.012 * Math.sin(17 * th + 3.1));
  const d = wrapA(th - ISLE.thH), l = ISLE.lobe * Math.exp(-((d / 0.16) ** 2));
  const m = Math.max(b, l); return m + 60 * Math.log(Math.exp((b - m) / 60) + Math.exp((l - m) / 60));
}
function inIsle(x, z, margin = 0) { return Math.hypot(x, z) < isleR(Math.atan2(z, x)) - margin; }
function vn1(x) { const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f); return lerp(hash1(i), hash1(i + 1), u); }
function vn2(x, y) { const i = Math.floor(x), j = Math.floor(y), f = x - i, g = y - j, u = f * f * (3 - 2 * f), v = g * g * (3 - 2 * g);
  const h = (a, b) => hash1(a * 127.1 + b * 311.7); return lerp(lerp(h(i, j), h(i + 1, j), u), lerp(h(i, j + 1), h(i + 1, j + 1), u), v); }""")

# ------------------------------------------------------------------ decode: clip roads / buildings to the island
rep("""  for (const [ci, br, ow, ni, flat] of D.roads) {
    const hw = D.classes[ci], pts = [];
    for (let i = 0; i < flat.length; i += 2) pts.push([flat[i], flat[i + 1]]);
    if (pts.length < 2) continue;
    out.roads.push({ pts, hw, major: MAJOR.test(hw), bridge: !!br, oneway: !!ow || /motorway/.test(hw), name: D.names[ni] });
  }""", """  for (const [ci, br, ow, ni, flat] of D.roads) {
    const hw = D.classes[ci];
    let run = [];
    const flush = () => { if (run.length >= 2) out.roads.push({ pts: run, hw, major: MAJOR.test(hw), bridge: !!br, oneway: !!ow || /motorway/.test(hw), name: D.names[ni] }); run = []; };
    for (let i = 0; i < flat.length; i += 2) { const x = flat[i], z = flat[i + 1]; if (inIsle(x, z, 4)) run.push([x, z]); else flush(); }
    flush();
  }""")
rep("""  for (const [x, z, w, d, ang, h, zi] of D.buildings) {
    const a = ang * Math.PI / 180;""", """  for (const [x, z, w, d, ang, h, zi] of D.buildings) {
    if (!inIsle(x, z, Math.max(w, d) * 0.6 + 4)) continue;
    const a = ang * Math.PI / 180;""")

# ------------------------------------------------------------------ trees: 5 floats per instance (x, z, scale, hue, y)
rep("""  const ib2 = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, ib2); gl.bufferData(gl.ARRAY_BUFFER, inst, gl.STATIC_DRAW);
  gl.enableVertexAttribArray(3); gl.vertexAttribPointer(3, 4, gl.FLOAT, false, 16, 0); gl.vertexAttribDivisor(3, 1);""",
    """  const ib2 = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, ib2); gl.bufferData(gl.ARRAY_BUFFER, inst, gl.STATIC_DRAW);
  gl.enableVertexAttribArray(3); gl.vertexAttribPointer(3, 4, gl.FLOAT, false, 20, 0); gl.vertexAttribDivisor(3, 1);
  gl.enableVertexAttribArray(4); gl.vertexAttribPointer(4, 1, gl.FLOAT, false, 20, 16); gl.vertexAttribDivisor(4, 1);""")
rep("""  return { vao, count: tpl.i.length, n: inst.length / 4 };""", """  return { vao, count: tpl.i.length, n: inst.length / 5 };""")
rep("""function treeInstances(flat, base, jitter) {
  const n = flat.length / 2, a = new Float32Array(n * 4);
  for (let i = 0; i < n; i++) { const x = flat[2 * i], z = flat[2 * i + 1], h = hash1(x * 0.37 + z * 1.13); a[4 * i] = x; a[4 * i + 1] = z; a[4 * i + 2] = base + h * jitter; a[4 * i + 3] = hash1(x * 1.7 - z * 0.3); }
  return a;
}""", """function treeInstances(flat, base, jitter, ys) {
  const out = [];
  for (let i = 0; i < flat.length / 2; i++) {
    const x = flat[2 * i], z = flat[2 * i + 1], y = ys ? ys[i] : 0;
    if (!ys && !inIsle(x, z, 6)) continue;
    const h = hash1(x * 0.37 + z * 1.13);
    out.push(x, z, base + h * jitter, hash1(x * 1.7 - z * 0.3), y);
  }
  return new Float32Array(out);
}""")

# ------------------------------------------------------------------ island geometry, islets, waterfalls (insert before aerial actors)
rep("""/* ---------------- aerial actors ---------------- */""", """/* ---------------- floating island body ---------------- */
// profile rows: [y, radial scale, kind]  kind: 0 grass lip · 1 soil · 2 rock
const ISLE_PROF = [[0.6, 1.0, 0], [-6, 1.014, 0], [-24, 1.004, 1], [-62, 0.99, 1], [-140, 0.955, 2], [-290, 0.905, 2], [-500, 0.83, 2], [-760, 0.73, 2],
  [-1040, 0.61, 2], [-1340, 0.48, 2], [-1640, 0.35, 2], [-1940, 0.23, 2], [-2230, 0.13, 2], [-2480, 0.055, 2], [-2640, 0.0, 2]];
function isleScaleAt(y) { // horizontal scale of the underside at height y (for camera collision)
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
const FALLS = { v: [], groups: [] };   // waterfall sheets: pos3 uv2 edge1
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
const ISLETS = [];
function buildIsland(maskImg) {
  const g = new Geo();
  // water lookup from the mask
  const cv = document.createElement("canvas"); cv.width = cv.height = 1024;
  const c2 = cv.getContext("2d"); c2.drawImage(maskImg, 0, 0, 1024, 1024);
  const md = c2.getImageData(0, 0, 1024, 1024).data;
  const waterAt = (x, z) => { const i = clamp(Math.floor((x + D.R) / (2 * D.R) * 1024), 0, 1023), j = clamp(Math.floor((z + D.R) / (2 * D.R) * 1024), 0, 1023); return md[(j * 1024 + i) * 4] > 127; };
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
  return { V: new Float32Array(g.v), I: new Uint32Array(g.i) };
}

/* ---------------- aerial actors ---------------- */""")

# ------------------------------------------------------------------ clouds: around and below the island + waterfall mist
rep("""  for (let c = 0; c < 60; c++) {
    const cx = (R() - 0.5) * 15000, cz = (R() - 0.5) * 15000, cy = 700 + R() * 380;""",
    """  for (let c = 0; c < 78; c++) {
    const below = c % 2 === 1;
    const cx = (R() - 0.5) * 15000, cz = (R() - 0.5) * 15000, cy = below ? -1500 + R() * 900 : 650 + R() * 450;""")
rep("""      puffs.push({ x: cx + dx, y: cy + dy, z: cz + dz, s: size * (0.7 + R() * 0.7), lit: clamp(0.35 + dy / (size * 0.5) * 0.6 + R() * 0.15, 0, 1), a: 0.55 + R() * 0.35 });
    }
  }""", """      puffs.push({ x: cx + dx, y: cy + dy, z: cz + dz, s: size * (0.7 + R() * 0.7), lit: clamp(0.35 + dy / (size * 0.5) * 0.6 + R() * 0.15, 0, 1), a: 0.55 + R() * 0.35 });
    }
  }
  // spray and mist at the foot of every waterfall (anchored, no drift)
  for (const G of FALLS.groups) {
    const n = Math.min(14, 3 + Math.floor(G.w / 160));
    for (let k = 0; k < n; k++) {
      const t = (k + 0.5) / n, along = (t - 0.5) * G.w * 0.9, tx = -G.oz, tz = G.ox;
      const out = 140 * (G.H / 1400);
      puffs.push({ x: G.x + tx * along + G.ox * out, y: G.y - G.H * (0.55 + R() * 0.25), z: G.z + tz * along + G.oz * out, s: 120 + R() * 160 * (G.H / 1400), lit: 0.85, a: 0.55, fixed: true });
      if (R() < 0.5) puffs.push({ x: G.x + tx * along + G.ox * 10, y: G.y - 40 - R() * 60, z: G.z + tz * along + G.oz * 10, s: 40 + R() * 40, lit: 1, a: 0.35, fixed: true });
    }
  }""")
rep("""      let x = ((p.x + wx + 7500) % 15000 + 15000) % 15000 - 7500, z = ((p.z + wz + 7500) % 15000 + 15000) % 15000 - 7500;""",
    """      let x = p.fixed ? p.x : ((p.x + wx + 7500) % 15000 + 15000) % 15000 - 7500, z = p.fixed ? p.z : ((p.z + wz + 7500) % 15000 + 15000) % 15000 - 7500;""")

# ------------------------------------------------------------------ build scene: ground without skirt, island, falls, sea, islet trees
rep("""  for (const [x0, z0, x1, z1] of [[-G, -G, G, -R], [-G, R, G, G], [-G, -R, -R, R], [R, -R, G, R]]) pts.push(x0, z0, x1, z0, x1, z1, x0, z0, x1, z1, x0, z1);
""", "")
rep("""  const pts = []; const n = 32, R = S.R;""", """  const pts = []; const n = 40, R = S.R + 220;""")
rep("""  loader.show("正在种树、放飞机", "行道树、云层、航班、直升机、白鹭、无人机"); await sleep(30);""",
    """  loader.show("正在升起岛屿", "岩层、垂岩、瀑布、云海与小浮岛"); await sleep(30);
  const isle = buildIsland(maskImg);
  S.island = meshVAO(isle.V, isle.I);
  S.fallVAO = gl.createVertexArray(); gl.bindVertexArray(S.fallVAO);
  const fb = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, fb); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(FALLS.v), gl.STATIC_DRAW);
  gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 24, 0);
  gl.enableVertexAttribArray(1); gl.vertexAttribPointer(1, 2, gl.FLOAT, false, 24, 12);
  gl.enableVertexAttribArray(2); gl.vertexAttribPointer(2, 1, gl.FLOAT, false, 24, 20);
  S.fallCount = FALLS.v.length / 6;
  S.seaVAO = gl.createVertexArray(); gl.bindVertexArray(S.seaVAO);
  const sb = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, sb);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-G, -G, G, -G, G, G, -G, -G, G, G, -G, G]), gl.STATIC_DRAW);
  gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
  gl.bindVertexArray(null);
  loader.show("正在种树、放飞机", "行道树、云层、航班、直升机、白鹭、无人机"); await sleep(30);""")
rep("""  S.trees = [treeVAO(treeTemplate(false), treeInstances(D.trees, 0.8, 0.7)), treeVAO(treeTemplate(true), treeInstances(D.palms, 0.85, 0.4))];""",
    """  const itx = [], ity = [];
  for (const I of ISLETS) { itx.push(...I.tx); ity.push(...I.ty); }
  const roundTpl = treeTemplate(false);
  S.trees = [treeVAO(roundTpl, treeInstances(D.trees, 0.8, 0.7)), treeVAO(treeTemplate(true), treeInstances(D.palms, 0.85, 0.4)), treeVAO(roundTpl, treeInstances(itx, 1.0, 0.9, ity))];""")
rep("""<b>${fmt(S.trees[0].n + S.trees[1].n)}</b> 棵树`;""",
    """<b>${fmt(S.trees[0].n + S.trees[1].n + S.trees[2].n)}</b> 棵树 · <b>${FALLS.groups.length}</b> 道瀑布 · <b>${ISLETS.length}</b> 座小浮岛`;""")
rep("""  const og2 = document.createElement("optgroup"); og2.label = "空中"; sel.appendChild(og2);""",
    """  const og0 = document.createElement("optgroup"); og0.label = "视角"; sel.insertBefore(og0, og1);
  for (const [v, t] of [["v-isle", "岛屿全景"], ["v-city", "城市俯瞰"], ["v-falls", "深圳湾瀑布"], ["v-under", "岛底仰望"]]) { const o = document.createElement("option"); o.value = v; o.textContent = t; og0.appendChild(o); }
  const og2 = document.createElement("optgroup"); og2.label = "空中"; sel.appendChild(og2);""")
rep("""  S.cam = { tx: 300, tz: 300, yaw: -0.6, pitch: 1.3, dist: 6200 };
  flyTo(HOME(), reduceMotion ? 0 : 6500);""", """  S.cam = { tx: 0, tz: 0, ty: -400, yaw: -0.3, pitch: 0.75, dist: 21000 };
  flyTo(HOME(), reduceMotion ? 0 : 7000);""")

# view presets
rep("""  if (v[0] === "b") { flyToBuilding(+v.slice(1)); return; }""", """  if (v[0] === "b") { flyToBuilding(+v.slice(1)); return; }
  if (v.startsWith("v-")) { flyTo(VIEWS[v](), reduceMotion ? 0 : 3000); return; }""")
rep("""const HOME = () => ({ tx: 250, tz: 250, yaw: -0.82, pitch: 0.5, dist: 2500 });""",
    """const HOME = () => ({ tx: 0, tz: 0, ty: -250, yaw: -0.85, pitch: 0.27, dist: 10500 });
const VIEWS = {
  "v-isle": HOME,
  "v-city": () => ({ tx: 250, tz: 250, ty: 0, yaw: -0.82, pitch: 0.5, dist: 2500 }),
  "v-falls": () => {
    const G = FALLS.groups.slice().sort((a, b) => b.w - a.w)[0] || { x: 2000, z: 2000, ox: 0.7, oz: 0.7 };
    return { tx: G.x + G.ox * 200, tz: G.z + G.oz * 200, ty: -620, yaw: Math.atan2(G.ox, G.oz) + 0.35, pitch: 0.1, dist: 3400 };
  },
  "v-under": () => ({ tx: 0, tz: 0, ty: -1500, yaw: S.cam.yaw, pitch: -0.38, dist: 7600 })
};""")

# camera limits
rep("""  c.pitch = Math.min(1.52, Math.max(0.06, c.pitch));
  c.dist = Math.min(S.R * 4, Math.max(45, c.dist));""", """  c.dist = Math.min(24000, Math.max(45, c.dist));
  c.pitch = Math.min(1.52, Math.max(c.dist > 4200 ? -0.6 : ((c.ty || 0) < -50 ? -0.3 : 0.06), c.pitch));""")
rep("""  if (eye[1] < 8) eye[1] = 8;""", """  { // keep the camera out of the island
    const rr = Math.hypot(eye[0], eye[2]), R0 = isleR(Math.atan2(eye[2], eye[0]));
    if (eye[1] > -5 && eye[1] < 8 && rr < R0) eye[1] = 8;
    else if (eye[1] <= -5) { const lim = R0 * isleScaleAt(eye[1]) * 1.06 + 40; if (rr < lim) { const k = lim / Math.max(rr, 1); eye[0] *= k; eye[2] *= k; } }
  }""")
rep("""  const near = clamp(Math.min(dist, eye[1]) * 0.02, 0.8, 40), far = 60000;""", """  const near = clamp(Math.min(dist, Math.abs(eye[1]) + 60) * 0.02, 0.8, 60), far = 90000;""")
rep("""  if (u.uFogDen) gl.uniform1f(u.uFogDen, 1 / (S.R * (2.6 + 1.6 * (1 - L.night))));""",
    """  if (u.uFogDen) gl.uniform1f(u.uFogDen, 1 / (S.R * (6.5 + 3.5 * (1 - L.night))));
  if (u.uIsle) gl.uniform3f(u.uIsle, ISLE.R0, ISLE.thH, ISLE.lobe);""")
rep("""  const hs = clamp((S.tour || S.follow ? Math.max(500, eye[1] * 2.2) : dist * 0.95), 350, 4200);""",
    """  const hs = clamp((S.tour || S.follow ? Math.max(500, Math.abs(eye[1]) * 2.2) : dist * 0.75), 350, 4300);""")

# shadow pass: island
rep("""    if (S.bridge) { gl.bindVertexArray(S.bridge.vao); gl.drawElements(gl.TRIANGLES, S.bridge.count, gl.UNSIGNED_INT, 0); }
    if (DYN.ni) {""", """    if (S.bridge) { gl.bindVertexArray(S.bridge.vao); gl.drawElements(gl.TRIANGLES, S.bridge.count, gl.UNSIGNED_INT, 0); }
    gl.bindVertexArray(S.island.vao); gl.drawElements(gl.TRIANGLES, S.island.count, gl.UNSIGNED_INT, 0);
    if (DYN.ni) {""")
# main pass: sea of clouds after sky, island after ground
rep("""  gl.enable(gl.DEPTH_TEST); gl.depthFunc(gl.LEQUAL); gl.depthMask(true);
  // ground""", """  gl.enable(gl.DEPTH_TEST); gl.depthFunc(gl.LEQUAL); gl.depthMask(true);
  gl.useProgram(P.sea.p); setCommon(P.sea, L, eye, now); gl.uniformMatrix4fv(P.sea.u.uVP, false, vp); gl.uniform1f(P.sea.u.uY, -1900);
  gl.bindVertexArray(S.seaVAO); gl.drawArrays(gl.TRIANGLES, 0, 6);
  // ground""")
rep("""  if (S.bridge) { gl.bindVertexArray(S.bridge.vao); gl.drawElements(gl.TRIANGLES, S.bridge.count, gl.UNSIGNED_INT, 0); }
  if (DYN.ni) { gl.uniform1f(P.mesh.u.uRise, 1);""", """  if (S.bridge) { gl.bindVertexArray(S.bridge.vao); gl.drawElements(gl.TRIANGLES, S.bridge.count, gl.UNSIGNED_INT, 0); }
  gl.uniform1f(P.mesh.u.uSel, -1); gl.bindVertexArray(S.island.vao); gl.drawElements(gl.TRIANGLES, S.island.count, gl.UNSIGNED_INT, 0);
  if (DYN.ni) { gl.uniform1f(P.mesh.u.uRise, 1);""")
# waterfalls after opaque, before points
rep("""  // points (cars, lights, drones)
  gl.useProgram(P.point.p);""", """  // waterfalls
  gl.enable(gl.BLEND); gl.depthMask(false); gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
  gl.useProgram(P.fall.p); setCommon(P.fall, L, eye, now); gl.uniformMatrix4fv(P.fall.u.uVP, false, vp);
  gl.bindVertexArray(S.fallVAO); gl.drawArrays(gl.TRIANGLES, 0, S.fallCount);
  // points (cars, lights, drones)
  gl.useProgram(P.point.p);""")

# tour: start far out, swoop past the falls, over the rim, through the city, dive under the island
rep("""  return [
    [3600, 3800, 4200], [2600, 1500, 2600], [1700, 420, 1500], [900, 160, 700],""", """  const G = FALLS.groups.slice().sort((a, b) => b.w - a.w)[0] || { x: 2200, z: 1800, ox: 0.7, oz: 0.6 };
  const fx = G.x, fz = G.z, ox = G.ox, oz = G.oz;
  return [
    [9500, 2600, 9000], [fx + ox * 2600, 300, fz + oz * 2600], [fx + ox * 1100 + oz * 600, -350, fz + oz * 1100 - ox * 600], [fx + ox * 500 - oz * 500, 120, fz + oz * 500 + ox * 500],
    [fx * 0.75, 220, fz * 0.75], [900, 160, 700],""")
rep("""    [one[0] - 200, 260, one[1] - 260], [one[0] + 250, 200, one[1] + 300], [400, 90, 1700], [1600, 140, 2400], [3000, 900, 3000], [3600, 2600, 3600]
  ];""", """    [one[0] - 200, 260, one[1] - 260], [one[0] + 250, 200, one[1] + 300], [400, 90, 1700],
    [-2400, 150, 2600], [-4300, -500, 3300], [-3500, -1500, 900], [-1000, -2150, -3800], [3200, -1300, -4800], [6800, 400, -2600], [9500, 1800, 3500]
  ];""")
rep("""  S.tour = { P, u: 0.0, speed: 0.06 };""", """  S.tour = { P, u: 0.0, speed: 0.055 };""")

# status line
rep("""    const items = [`✈ 航班 ${AIR.planes.length}`,""", """    const items = [`瀑布 ${FALLS.groups.length} 道`, `✈ 航班 ${AIR.planes.length}`,""")

# planes fly around/under the island too
rep("""    { a: [9500, 1500, 7000], b: [-9500, 700, -6500], T: 230, ph: 0.0, name: "进港航班" },
    { a: [-9000, 600, -1500], b: [9000, 2100, 5500], T: 210, ph: 0.45, name: "出港航班" },
    { a: [8000, 1650, -7000], b: [-9000, 1050, 2500], T: 250, ph: 0.75, name: "过境航班" }""", """    { a: [11000, 1500, 8000], b: [-11000, 700, -7500], T: 260, ph: 0.0, name: "进港航班" },
    { a: [-11000, -700, -1500], b: [11000, 1300, 5500], T: 240, ph: 0.45, name: "出港航班" },
    { a: [9000, 2100, -8000], b: [-10000, 1500, 3000], T: 280, ph: 0.75, name: "过境航班" }""")

open(sys.argv[2], "w", encoding="utf-8").write(s)
print("ok")
