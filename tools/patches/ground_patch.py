"""Ground detail pass. src6.html -> src7.html"""
import sys

s = open(sys.argv[1], encoding="utf-8").read()


def rep(a, b, cnt=1):
    global s
    assert a in s, "MISSING: " + a[:110]
    s = s.replace(a, b, cnt)


# ------------------------------------------------------------------ ground shader: land-use surfaces
rep("""in vec3 vPos; in vec4 vLight; uniform sampler2D uTex; uniform float uR; out vec4 o;""",
    """in vec3 vPos; in vec4 vLight; uniform sampler2D uTex; uniform sampler2D uLU; uniform float uR; out vec4 o;""")
rep("""  // land surfaces
  float n2 = vnoise(vPos.xz * 0.06);
  vec3 land = mix(vec3(0.50, 0.50, 0.48), vec3(0.56, 0.53, 0.49), n2) * (0.9 + 0.14 * n1);
  vec3 green = vec3(0.28, 0.42, 0.22) * (0.80 + 0.30 * n1);
  vec3 c = mix(land, green, g);""", """  // land surfaces by land-use zone
  vec4 lu = texture(uLU, clamp(uv, 0.0, 1.0));
  float zone = floor(lu.r * 255.0 / 30.0 + 0.5);
  float bd = lu.g * 255.0 / 8.0;
  float dcam0 = distance(vPos, uCam);
  float near = 1.0 - smoothstep(150.0, 750.0, dcam0);
  float n2 = vnoise(vPos.xz * 0.06), n3 = vnoise(vPos.xz * 0.9), n4 = vnoise(vPos.xz * 3.1);
  vec3 concrete = mix(vec3(0.50, 0.50, 0.48), vec3(0.56, 0.53, 0.49), n2) * (0.9 + 0.14 * n1);
  vec3 grass = mix(vec3(0.23, 0.39, 0.16), vec3(0.31, 0.46, 0.20), n2) * (0.85 + 0.25 * n1) * (1.0 + (n4 - 0.5) * 0.3 * near);
  vec3 landC = concrete;
  if (zone > 0.5 && zone < 2.5) {                       // CBD / tech park plazas
    vec2 j = abs(fract(vPos.xz / 1.5) - 0.5); float jo = smoothstep(0.455, 0.49, max(j.x, j.y));
    float bandP = step(0.5, fract((vPos.x + vPos.z) / 18.0));
    landC = mix(vec3(0.64, 0.62, 0.58), vec3(0.55, 0.54, 0.52), bandP * 0.55) * (0.94 + 0.08 * n3);
    landC *= 1.0 - jo * 0.14 * near;
    vec2 cellP = floor(vPos.xz / 14.0); vec2 fP = fract(vPos.xz / 14.0) - 0.5;
    float pm = max(abs(fP.x), abs(fP.y));
    float pl = step(h21(cellP), 0.24) * step(9.0, bd) * step(pm, 0.17);
    landC = mix(landC, mix(grass * 0.9, vec3(0.72, 0.71, 0.68), step(0.135, pm)), pl);
  } else if ((zone > 2.5 && zone < 3.5) || (zone > 4.5 && zone < 5.5 && n2 > 0.48)) {   // residential compounds
    vec2 j = abs(fract(vPos.xz / 0.6) - 0.5); float jo = smoothstep(0.44, 0.49, max(j.x, j.y));
    vec3 pave = vec3(0.61, 0.58, 0.54) * (0.93 + 0.1 * n3) * (1.0 - jo * 0.12 * near);
    float lawn = smoothstep(6.5, 7.5, bd);
    float hedge = smoothstep(5.4, 5.8, bd) - smoothstep(6.6, 7.1, bd);
    landC = mix(pave, grass, lawn);
    landC = mix(landC, vec3(0.13, 0.26, 0.10) * (0.8 + 0.4 * n4), hedge * 0.92);
  } else if (zone > 3.5 && zone < 4.5) {                // urban village
    landC = vec3(0.41, 0.40, 0.38) * (0.85 + 0.25 * n3) * (1.0 - 0.16 * smoothstep(0.6, 0.85, vnoise(vPos.xz * 0.2)));
  } else if (zone > 5.5) {
    landC = grass;
  }
  landC *= mix(0.6, 1.0, smoothstep(0.0, 3.5, bd));      // contact shadow at building feet
  vec3 green = grass;
  vec3 c = mix(landC, green, g);
  float fb = smoothstep(0.76, 0.82, vnoise(vPos.xz * 0.028 + 3.0)) * max(g, step(5.5, zone)) * step(0.5, 1.0 - path);
  vec3 flowerC = mix(hsv(vnoise(vPos.xz * 0.012 + 9.0), 0.65, 0.9), vec3(0.95, 0.92, 0.85), step(0.7, n4));
  c = mix(c, mix(grass, flowerC, 0.55 + 0.45 * step(0.45, n3)), fb);""")
rep("""  vec3 deep = mix(vec3(0.05, 0.15, 0.19), vec3(0.08, 0.20, 0.23), n1) * (amb + uLightCol * 0.3 * sh);""",
    """  vec3 deep = mix(vec3(0.05, 0.15, 0.19), vec3(0.08, 0.20, 0.23), n1) * (amb + uLightCol * 0.3 * sh);
  float shallow = smoothstep(0.06, 0.5, 1.0 - textureLod(uTex, clamp(uv, 0.0, 1.0), 2.5).r);
  deep = mix(deep, vec3(0.10, 0.31, 0.31) * (amb + uLightCol * 0.4 * sh), shallow * (1.0 - uNight * 0.7));""")

# ------------------------------------------------------------------ road shader: tyre tracks, patches, manholes, arrows
rep("""    m *= fade * 0.92 * (1.0 - medM);""", """    if (lanes > 0.5) {
      float hm0 = ow < 0.5 ? med * 0.5 * step(0.5, smoothstep(13.0, 15.0, dj)) : 0.0;
      float baseX = ow < 0.5 ? abs(across) - hm0 : across + hw;
      float lwX = ow < 0.5 ? (hw - hm0) / max(lanes, 1.0) : 2.0 * hw / max(lanes, 1.0);
      float lc = fract(baseX / lwX) - 0.5, xo = lc * lwX;
      float tyre = (1.0 - smoothstep(0.3, 0.55, abs(abs(xo) - 0.9))) * fade;
      asph *= 1.0 - 0.09 * tyre;
      float aa = dj - 16.5;
      if (aa > 0.0 && aa < 5.6 && baseX > 0.0) {
        float shaft = step(abs(xo), 0.14) * step(1.6, aa);
        float head = step(aa, 1.6) * step(abs(xo), aa / 1.6 * 0.55);
        float arrow = max(shaft, head) * fade;
        if (arrow > m) mc = vec3(0.9);
        m = max(m, arrow);
      }
    }
    float pt = smoothstep(0.80, 0.83, vnoise(vec2(along * 0.035, across * 0.18 + 7.0)));
    asph *= mix(1.0, 0.86 + 0.28 * n1, pt * 0.7 * fade);
    float mhK = floor(along / 23.0), mh = h21(vec2(mhK, kind));
    vec2 mhc = vec2((mhK + 0.5) * 23.0 + (mh - 0.5) * 9.0, (h21(vec2(kind, mhK)) - 0.5) * hw * 1.3);
    float mhd = length(vec2(along, across) - mhc);
    float hole = step(mh, 0.55) * (1.0 - smoothstep(0.42, 0.42 + fwA, mhd)) * fade;
    asph = mix(asph, vec3(0.12, 0.12, 0.12) + 0.06 * step(0.32, mhd), hole);
    m *= fade * 0.92 * (1.0 - medM);""")
rep("""    vec3 asph = vec3(0.16, 0.165, 0.175) * (0.86 + 0.18 * n1 * fade + 0.12 * n2);""",
    """    vec3 asph = vec3(0.16, 0.165, 0.175) * (0.86 + 0.18 * n1 * fade + 0.12 * n2) * (1.0 + (vnoise(vPos.xz * 2.7) - 0.5) * 0.12 * fade);""")

# ------------------------------------------------------------------ car parks (mat 19)
rep("""  } else if (m >= 12 && m <= 16) {""", """  } else if ((m >= 12 && m <= 16) || m == 19) {""")
rep("""    } else if (m == 13) {
      float ax = abs(q.x), ay = abs(q.y);""", """    } else if (m == 19) {
      float ax = abs(q.x), ay = abs(q.y);
      alb = vec3(0.21, 0.215, 0.225) * (0.88 + 0.16 * vnoise(q * 0.6)) * (1.0 - 0.08 * smoothstep(0.6, 0.8, vnoise(q * 0.25)));
      float row = step(W * 0.5 - 6.0, ay) * step(ay, W * 0.5 - 0.6);
      float stall = (1.0 - smoothstep(lw, lw + fq, abs(fract(q.x / 2.5 + 0.5) - 0.5) * 2.5)) * row * step(ax, L * 0.5 - 0.5);
      float edge = (1.0 - smoothstep(lw, lw + fq, abs(ay - (W * 0.5 - 6.0)))) * step(ax, L * 0.5 - 0.5);
      float border = max((1.0 - smoothstep(lw, lw + fq, abs(ax - (L * 0.5 - 0.5)))) * step(ay, W * 0.5 - 0.6), (1.0 - smoothstep(lw, lw + fq, abs(ay - (W * 0.5 - 0.6)))) * step(ax, L * 0.5 - 0.5));
      ln = clamp(stall + edge * 0.6 + border, 0.0, 1.0);
      emis += vec3(1.0, 0.7, 0.4) * 0.08 * uNight;
    } else if (m == 13) {
      float ax = abs(q.x), ay = abs(q.y);""")
rep("""  const DIM = { 0: [104, 68, 12], 1: [60, 40, 12], 2: [30, 17, 14], 3: [31, 16, 13], 4: [34, 18, 15], 5: [176, 100, 16] };""",
    """  const DIM = { 0: [104, 68, 12], 1: [60, 40, 12], 2: [30, 17, 14], 3: [31, 16, 13], 4: [34, 18, 15], 5: [176, 100, 16], 6: [46, 32, 19] };""")
rep("""    if (k === 0 || k === 1 || k === 5) {   // goals""", """    if (k === 6) {   // cars in the bays
      const PAL = [[0.92, 0.92, 0.92], [0.07, 0.07, 0.08], [0.62, 0.63, 0.65], [0.35, 0.36, 0.38], [0.60, 0.08, 0.06], [0.10, 0.15, 0.30], [0.80, 0.78, 0.72], [0.16, 0.36, 0.78]];
      for (const vr of [-(W / 2 - 3.2), W / 2 - 3.2]) for (let u = -L / 2 + 1.75; u < L / 2 - 1; u += 2.5) {
        const hh = hash1(x * 0.7 + z * 1.3 + u * 3.1 + vr); if (hh > 0.72) continue;
        const col = PAL[Math.floor(hash1(hh * 77.7) * PAL.length)];
        PARKED.push(x + c * u - s2 * vr, 0.15, z + s2 * u + c * vr, a + (vr > 0 ? -Math.PI / 2 : Math.PI / 2), col[0], col[1], col[2], 1);
      }
    }
    if (k === 0 || k === 1 || k === 5) {   // goals""")

# ------------------------------------------------------------------ traffic signals + bus stops (generated with the road mesh)
rep("""const SHRUBS = [], PARKED = [];""", """const SHRUBS = [], PARKED = [], SIGNALS = [], SIGLIGHTS = [], BUSSTOPS = [], BUSLIGHTS = [];""")
rep("""      if (pass === 1) {
        const djAt = (i, f) => Math.min(lerp(pj[i], pj[i + 1], f), lerp(nj[i], nj[i + 1], f));""", """      if (pass === 1 && lanes0 >= 1 && /^(trunk|primary|secondary|tertiary)$/.test(r.hw) && cum[n - 1] > 40 && SIGNALS.length < 900 * 8) {
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
        const djAt = (i, f) => Math.min(lerp(pj[i], pj[i + 1], f), lerp(nj[i], nj[i + 1], f));""")
rep("""  TPL.lamp = propTemplate(t => {""", """  TPL.signal = propTemplate(t => {
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
  TPL.lamp = propTemplate(t => {""")
rep("""  S.lampVAO = instVAO(TPL.lamp, streetLights(osm), false);""", """  S.lampVAO = instVAO(TPL.lamp, streetLights(osm), false);
  S.sigVAO = instVAO(TPL.signal, new Float32Array(SIGNALS), false);
  S.busVAO = instVAO(TPL.busstop, new Float32Array(BUSSTOPS), false);""")
rep("""  gl.uniform1f(P.inst.u.uFar, 1800);
  gl.bindVertexArray(S.lampVAO.vao);""", """  gl.uniform1f(P.inst.u.uFar, 1500);
  gl.bindVertexArray(S.sigVAO.vao); gl.drawElementsInstanced(gl.TRIANGLES, S.sigVAO.count, gl.UNSIGNED_SHORT, 0, S.sigVAO.n);
  gl.bindVertexArray(S.busVAO.vao); gl.drawElementsInstanced(gl.TRIANGLES, S.busVAO.count, gl.UNSIGNED_SHORT, 0, S.busVAO.n);
  gl.uniform1f(P.inst.u.uFar, 1800);
  gl.bindVertexArray(S.lampVAO.vao);""")
rep("""  // street lights
  if (night > 0.3)""", """  // traffic signals (two phase groups) and bus-stop light boxes
  {
    const cyc = t % 34;
    for (const sg of SIGLIGHTS) {
      const ph = sg[3] ? (cyc + 17) % 34 : cyc;
      const col = ph < 14 ? [0.1, 2.6, 0.9] : ph < 17 ? [2.8, 1.6, 0.1] : [2.8, 0.15, 0.1];
      const k = 0.6 + 1.6 * night;
      light(sg[0], sg[1], sg[2], col[0] * k, col[1] * k, col[2] * k, 2.4);
    }
    if (night > 0.3) for (const b of BUSLIGHTS) { light(b[0], b[1], b[2], 2.2 * night, 1.8 * night, 1.3 * night, 5); light(b[3], 1.4, b[4], 1.6 * night, 2.0 * night, 2.6 * night, 3.5); }
  }
  // street lights
  if (night > 0.3)""")
rep("""<b>${fmt(LAMPS.length)}</b> 盏路灯 · <b>${S.featN}</b> 处球场泳池`;""",
    """<b>${fmt(LAMPS.length)}</b> 盏路灯 · <b>${fmt(SIGLIGHTS.length)}</b> 组红绿灯 · <b>${BUSLIGHTS.length}</b> 个公交站 · <b>${S.featN}</b> 处球场、泳池和停车场`;""")

# ------------------------------------------------------------------ land-use texture loading + binding
rep("""function loadMask() { return new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = rej; im.src = "data:image/png;base64," + D.mask; }); }""",
    """function loadImg(b64) { return new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = rej; im.src = "data:image/png;base64," + b64; }); }
function loadMask() { return loadImg(D.mask); }""")
rep("""  try { const mask = await loadMask(); await buildScene(mask); }""", """  try { const mask = await loadMask(); const lu = await loadImg(D.lu); await buildScene(mask, lu); }""")
rep("""async function buildScene(maskImg) {""", """async function buildScene(maskImg, luImg) {""")
rep("""  S.tex = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, S.tex);""", """  S.luTex = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, S.luTex);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, luImg); gl.generateMipmap(gl.TEXTURE_2D);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  S.tex = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, S.tex);""")
rep("""  gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, S.tex); gl.uniform1i(P.ground.u.uTex, 0);""",
    """  gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, S.tex); gl.uniform1i(P.ground.u.uTex, 0);
  gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, S.luTex); gl.uniform1i(P.ground.u.uLU, 2); gl.activeTexture(gl.TEXTURE0);""")

open(sys.argv[2], "w", encoding="utf-8").write(s)
print("ok")
