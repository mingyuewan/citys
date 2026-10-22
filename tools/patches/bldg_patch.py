"""Building detail pass. src7.html -> src8.html"""
import sys

s = open(sys.argv[1], encoding="utf-8").read()


def rep(a, b, cnt=1):
    global s
    assert a in s, "MISSING: " + a[:110]
    s = s.replace(a, b, cnt)


# =================================================================== shader: interior mapping helper
rep("""float lineAA(float f, float w, float fw){ return smoothstep(w - fw, w + fw, f) - smoothstep(1.0 - w - fw, 1.0 - w + fw, f); }""",
    """float lineAA(float f, float w, float fw){ return smoothstep(w - fw, w + fw, f) - smoothstep(1.0 - w - fw, 1.0 - w + fw, f); }
// fake rooms behind the glass ("interior mapping"): returns the surface colour hit inside the room
vec3 roomShade(vec3 nO, vec3 V, vec2 uv, vec3 dim, float seed, out float depthF, out float ceil){
  vec3 t = normalize(vec3(-nO.z, 0.0, nO.x));
  vec3 rd = -V;
  vec3 r = vec3(dot(rd, t), rd.y, max(dot(rd, -nO), 0.06));
  vec2 cid = floor(uv / dim.xy);
  vec3 P = vec3(fract(uv.x / dim.x) * dim.x, fract(uv.y / dim.y) * dim.y, 0.0);
  float tx = r.x > 0.0 ? (dim.x - P.x) / max(r.x, 1e-4) : P.x / max(-r.x, 1e-4);
  float ty = r.y > 0.0 ? (dim.y - P.y) / max(r.y, 1e-4) : P.y / max(-r.y, 1e-4);
  float tz = dim.z / r.z;
  float tm = min(tx, min(ty, tz));
  vec3 H = P + r * tm;
  float hs = h31(vec3(cid, seed));
  vec3 wallC = mix(vec3(0.84, 0.81, 0.74), vec3(0.62, 0.68, 0.72), step(0.62, hs));
  vec3 c; ceil = 0.0;
  if (tm == tz) {
    c = wallC;
    float furn = step(H.y, 0.85 + 0.5 * h31(vec3(cid, seed + 1.0))) * step(0.12 * dim.x, H.x) * step(H.x, (0.5 + 0.38 * hs) * dim.x);
    c = mix(c, vec3(0.24, 0.19, 0.16), furn);
    float art = step(abs(H.x - dim.x * 0.5), 0.45) * step(abs(H.y - dim.y * 0.58), 0.32) * step(0.55, hs);
    c = mix(c, hsv(fract(hs * 3.7), 0.5, 0.8), art);
  } else if (tm == ty) {
    if (r.y > 0.0) { c = vec3(0.92, 0.92, 0.90); ceil = 1.0 - smoothstep(0.3, 0.9, length(H.xz - vec2(dim.x * 0.5, dim.z * 0.45)) / dim.x); }
    else c = mix(vec3(0.44, 0.33, 0.24), vec3(0.36, 0.37, 0.39), step(0.5, hs));
  } else {
    c = wallC * 0.82;
  }
  depthF = exp(-tm * 0.11);
  return c;
}""")
rep("""  vec3 n = normalize(vNrm);
  vec3 V = normalize(uCam - vPos);
  if (dot(n, V) < 0.0 && vMat != 6.0) n = -n;""", """  vec3 n = normalize(vNrm);
  vec3 nO = n;
  vec3 V = normalize(uCam - vPos);
  if (dot(n, V) < 0.0 && vMat != 6.0) n = -n;
  float camD = distance(vPos, uCam);
  float inNear = 1.0 - smoothstep(220.0, 650.0, camD);
  vec3 inDay = vec3(0.0); float inF = 0.0;""")

# office / landmark glass: rooms, lobby, refuge floors, uplight
rep("""      float bright = (m == 7 ? 0.35 : 0.8) * (0.6 + 0.6 * h31(vec3(bay.x, bay.y + 7.0, vBid)));
      emis += lc * on * glassAmt * bright * night * mix(0.5, 1.0, span);""", """      float bright = (m == 7 ? 0.35 : 0.8) * (0.6 + 0.6 * h31(vec3(bay.x, bay.y + 7.0, vBid)));
      vec3 roomL = vec3(1.0);
      if (inNear > 0.001) {
        float dF, cl; vec3 rc = roomShade(nO, V, vUv, vec3(3.0, 4.0, 6.5), vBid, dF, cl);
        roomL = mix(vec3(1.0), rc * (0.35 + 0.9 * dF) * 1.15 + cl * 0.6, inNear);
        inDay = rc * (0.25 + 0.75 * dF); inF = inNear * glassAmt;
      }
      emis += lc * roomL * on * glassAmt * bright * night * mix(0.5, 1.0, span);
      if (m == 0 && hb > 0.72) emis += vec3(1.0, 0.86, 0.62) * 0.55 * exp(-vPos.y / 26.0) * night * (1.0 - glassAmt * 0.4);
      if (m == 0 && vUv.y < 7.5) {
        float lm = lineAA(fract(vUv.x / 3.0), 0.03, fwidth(vUv.x / 3.0));
        glassAmt = 0.92 * lm; alb = mix(vec3(0.78, 0.78, 0.76), vCol, glassAmt);
        emis = vec3(1.0, 0.82, 0.58) * 1.5 * glassAmt * night; inF *= 0.5;
      }
      if (vUv.y > 30.0 && mod(vUv.y, 52.0) < 4.2) {
        float lv = step(0.5, fract(vUv.y / 0.42));
        alb = vec3(0.33, 0.35, 0.38) * (0.78 + 0.28 * lv); glassAmt = 0.0; emis = vec3(0.0); inF = 0.0;
      }""")

# residential: rooms + AC units
rep("""      float curtain = 0.45 + 0.55 * h31(vec3(id.x + 3.0, id.y, vBid));
      emis += lc * on * win * 1.1 * curtain * night;""", """      float curtain = 0.45 + 0.55 * h31(vec3(id.x + 3.0, id.y, vBid));
      vec3 roomL = vec3(1.0);
      if (inNear > 0.001) {
        float dF, cl; vec3 rc = roomShade(nO, V, vUv, vec3(3.6, 3.0, 4.5), vBid + 7.0, dF, cl);
        roomL = mix(vec3(1.0), rc * (0.4 + 0.8 * dF) * 1.1 + cl * 0.5, inNear);
        inDay = rc * (0.25 + 0.75 * dF); inF = inNear * win * 0.85;
      }
      emis += lc * roomL * on * win * 1.1 * curtain * night;
      float ac = step(h31(vec3(id, vBid + 21.0)), 0.42) * step(0.74, f.x) * step(f.x, 0.95) * step(0.12, f.y) * step(f.y, 0.31) * fade;
      alb = mix(alb, vec3(0.86, 0.86, 0.84) * (0.86 + 0.14 * step(0.5, fract(f.y * 45.0))), ac);
      glassAmt *= 1.0 - ac; inF *= 1.0 - ac;""")
# village: security grilles + AC units
rep("""      float on = step(h31(vec3(id, vBid)), lit * 0.95);
      vec3 lc = mix(warm, vec3(0.85, 0.95, 1.0), step(0.55, h31(vec3(id.yx, vBid))));
      emis += lc * on * win * 1.3 * night;""", """      float on = step(h31(vec3(id, vBid)), lit * 0.95);
      vec3 lc = mix(warm, vec3(0.85, 0.95, 1.0), step(0.55, h31(vec3(id.yx, vBid))));
      float grille = max(step(0.82, fract(vUv.x / 0.2)), step(0.85, fract(vUv.y / 0.35))) * win * fade * step(0.35, h31(vec3(id, vBid + 4.0)));
      alb = mix(alb, vec3(0.30, 0.30, 0.32), grille * 0.8);
      glassAmt *= 1.0 - grille * 0.6;
      emis += lc * on * win * 1.3 * night * (1.0 - grille * 0.5);
      float ac = step(h31(vec3(id, vBid + 33.0)), 0.5) * step(0.04, f.x) * step(f.x, 0.26) * step(0.1, f.y) * step(f.y, 0.3) * fade;
      alb = mix(alb, vec3(0.84, 0.84, 0.82), ac); glassAmt *= 1.0 - ac;""")
# construction frame material
rep("""    } else if (m == 5) {
      glassAmt = 0.6;""", """    } else if (m == 20) {
      vec2 cc = vec2(vUv.x / 6.0, vUv.y / 3.6); vec2 f = fract(cc); vec2 fw = fwidth(cc); vec2 id = floor(cc);
      float colm = 1.0 - lineAA(f.x, 0.07, fw.x);
      float slab = 1.0 - smoothstep(0.1, 0.1 + fw.y, f.y);
      float solid = max(colm, slab);
      float net = step(h31(vec3(id, vBid)), 0.5);
      vec3 netC = vec3(0.17, 0.45, 0.24) * (0.85 + 0.2 * step(0.5, fract(vUv.x * 2.0)));
      alb = mix(mix(vec3(0.07, 0.07, 0.08), netC, net), vec3(0.64, 0.63, 0.60), solid);
      emis += vec3(1.0, 0.9, 0.72) * 0.9 * night * (1.0 - solid) * (1.0 - net) * step(h31(vec3(id.yx, vBid)), 0.3);
    } else if (m == 5) {
      glassAmt = 0.6;""")
# glass composite uses the room colour by day
rep("""    vec3 gc = vCol * 0.20 * (amb + direct) + refl * (0.12 + 0.62 * F)""",
    """    vec3 base0 = mix(vCol * 0.20 * (amb + direct), inDay * (amb * 0.55 + direct * 0.08 + 0.02), clamp(inF / max(glassAmt, 0.01), 0.0, 1.0));
    vec3 gc = base0 + refl * (0.10 + 0.62 * F)""")

# =================================================================== geometry: construction sites, canopies, terraces with trees, crown frames, rooftop clutter
rep("""const craneCands = [];""", """const craneCands = [], CONSTRUCT = [], ROOFTREES = [], ROOFTREE_Y = [];""")
rep("""  let y0 = 0, tw = w, td = d;
  if (rnd() < 0.62) {
    const ph = 14 + rnd() * 12;
    prism(g, rnd() < 0.5 ? chamferRing(x, z, w, d, ang, 0.12) : rectRing(x, z, w, d, ang), 0, ph, tint.map(v => v * 1.15), 2, bid, { capCol: rnd() < 0.55 ? [0.30, 0.44, 0.24] : [0.55, 0.56, 0.54], capMat: 11 });
    y0 = ph; tw = w * (0.62 + rnd() * 0.12); td = d * (0.64 + rnd() * 0.12);
  }""", """  const cA = Math.cos(ang), sA = Math.sin(ang);
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
  }""")
rep("""    prism(g, R0, y0, t1, tint, 0, bid, { capCol: CONC });
    prism(g, R1, t1, t2, tint, 0, bid, { capCol: CONC });""", """    prism(g, R0, y0, t1, tint, 0, bid, { capCol: [0.32, 0.45, 0.26], capMat: 11 });
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
    }""")
# residential decorative crown frame
rep("""    if (rnd() < 0.5) prism(g, scaleRing(R, 1.02, x, z), h, h + 1.2, col.map(v => v * 0.9), 3, bid, { cap: false });""",
    """    if (rnd() < 0.5) prism(g, scaleRing(R, 1.02, x, z), h, h + 1.2, col.map(v => v * 0.9), 3, bid, { cap: false });
    else if (h > 60 && rnd() < 0.6) {      // decorative crown frame (common on Shenzhen residential towers)
      prism(g, scaleRing(R, 1.01, x, z), h, h + 6.5, col.map(v => v * 0.95), 3, bid, { cap: false });
      prism(g, scaleRing(R, 1.04, x, z), h + 6.5, h + 7.4, col.map(v => v * 0.85), 3, bid, { capCol: col.map(v => v * 0.8) });
    }""")
# village rooftop clutter
rep("""      if (rnd() < 0.2) prism(g, rectRing(x, z, w * 0.8, d * 0.8, ang), h, h + 0.4, [0.30, 0.45, 0.22], 11, bid);""",
    """      if (rnd() < 0.2) prism(g, rectRing(x, z, w * 0.8, d * 0.8, ang), h, h + 0.4, [0.30, 0.45, 0.22], 11, bid);
      prism(g, scaleRing(rectRing(x, z, w, d, ang), 1.0, x, z), h, h + 1.1, col.map(v => v * 0.9), 3, bid, { cap: false });
      const nc = rnd() * 4 | 0;
      for (let k = 0; k < nc; k++) {
        const u = (rnd() - 0.5) * w * 0.7, v = (rnd() - 0.5) * d * 0.7, c = Math.cos(ang), s2 = Math.sin(ang);
        const px = x + c * u - s2 * v, pz = z + s2 * u + c * v, kind = rnd();
        if (kind < 0.4) prism(g, circleRing(px, pz, 0.9 + rnd() * 0.5, 8), h, h + 1.8, kind < 0.2 ? [0.25, 0.40, 0.65] : [0.85, 0.85, 0.83], 5, bid, { smooth: true });
        else if (kind < 0.7) boxAt(g, px, pz, 2 + rnd() * 2, 0.08, ang + rnd(), h + 1.4, h + 2.4, hsv3(rnd()), 8, bid);
        else boxAt(g, px, pz, 1.4, 1.4, ang, h, h + 1.0 + rnd(), [0.25, 0.42, 0.20], 11, bid);
      }""")
rep("""/* ---------------- generated buildings ---------------- */""", """/* ---------------- generated buildings ---------------- */
function hsv3(hh) { const k = [5, 3, 1].map(n => (n + hh * 6) % 6); return k.map(v => 0.85 - 0.6 * Math.max(0, Math.min(v, 4 - v, 1))); }""")

# cranes now stand next to the construction sites
rep("""  const cand = craneCands.filter(c => c.h > 60 && c.h < 240 && inIsle(c.x, c.z, 80));
  for (let k = 0; k < cand.length && AIR.cranes.length < 12; k++) {
    if (RC() > 0.09) continue;""", """  const cand = CONSTRUCT.filter(c => inIsle(c.x, c.z, 80));
  for (let k = 0; k < cand.length && AIR.cranes.length < 16; k++) {""")

# roof trees use the islet tree VAO path (base height per instance)
rep("""  for (const I of ISLETS) { itx.push(...I.tx); ity.push(...I.ty); }""", """  for (const I of ISLETS) { itx.push(...I.tx); ity.push(...I.ty); }
  itx.push(...ROOFTREES); ity.push(...ROOFTREE_Y);""")
rep("""const pointTower = w < 34 && d < 34 && rnd() < 0.6;""", """const pointTower = w < 34 && d < 34 && rnd() < 0.6;
    void 0;""")
rep("""<b>${fmt(osm.buildings.length - osm.landmarkCount)}</b> 栋生成楼体""", """<b>${fmt(osm.buildings.length - osm.landmarkCount)}</b> 栋生成楼体（${CONSTRUCT.length} 处在建）""")

open(sys.argv[2], "w", encoding="utf-8").write(s)
print("ok")
