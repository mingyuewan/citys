"""Detail pass 3. src5.html -> src6.html"""
import sys

s = open(sys.argv[1], encoding="utf-8").read()


def rep(a, b, cnt=1):
    global s
    assert a in s, "MISSING: " + a[:110]
    s = s.replace(a, b, cnt)


# =================================================================== facades: floor slabs, balconies, window recess, flicker
rep("""      float rail = mix(0.0, 1.0 - smoothstep(0.08, 0.1, f.y), fade);
      glassAmt = win * 0.85;
      alb = mix(vCol, vCol * 0.72, rail);
      float on = step(h31(vec3(id, vBid)), lit * 0.75);""", """      float slab = (1.0 - smoothstep(0.065, 0.065 + fw.y, f.y)) * fade;
      float under = (smoothstep(0.065, 0.09, f.y) - smoothstep(0.15, 0.2, f.y)) * fade;
      bool balc = mod(id.x + floor(hb * 3.0), 3.0) < 1.0;
      float railM = balc ? (smoothstep(0.08, 0.1, f.y) - smoothstep(0.34, 0.36, f.y)) * lineAA(f.x, 0.04, fw.x) * fade : 0.0;
      float recess = (smoothstep(0.66, 0.70, f.y) - smoothstep(0.76, 0.78, f.y)) * lineAA(f.x, 0.2, fw.x) * lineAA(f.y, 0.22, fw.y) * fade;
      glassAmt = win * 0.85 * (1.0 - recess * 0.6) + railM * 0.3;
      alb = vCol * (1.0 + 0.14 * slab - 0.24 * under);
      alb = mix(alb, vec3(0.55, 0.63, 0.67), railM * 0.55);
      float ep = floor(uTime / 45.0 + h31(vec3(id.yx, vBid + 9.0)) * 9.0);
      float on = step(h31(vec3(id + ep * 0.731, vBid)), lit * 0.75);""")
rep("""      float on = step(h31(vec3(bay, vBid)), lit * 0.5);""", """      float epo = floor(uTime / 55.0 + h31(vec3(bay.yx, vBid + 2.0)) * 9.0);
      float on = step(h31(vec3(bay + epo * 0.573, vBid)), lit * 0.5);""")
# ground-floor shops on residential / podium / village walls
rep("""  if (roof && (m == 0 || m == 1 || m == 2 || m == 4)) alb = vCol;""", """  if (!roof && vUv.x > -0.5 && (m == 1 || m == 2 || m == 4) && vUv.y < 4.6) {
    float sx = vUv.x / 7.5, sid = floor(sx), fx = fract(sx), fws = fwidth(sx);
    float pillar = 1.0 - lineAA(fx, 0.05, fws);
    float signB = step(3.25, vUv.y) * step(vUv.y, 4.35);
    float glassB = step(0.3, vUv.y) * step(vUv.y, 3.05);
    float openS = step(0.22, h31(vec3(sid, 5.0, vBid)));
    vec3 signC = hsv(h31(vec3(sid, 11.0, vBid)), 0.62, 0.92);
    alb = mix(vec3(0.60, 0.58, 0.55), signC, signB * openS);
    glassAmt = glassB * (1.0 - pillar) * 0.9 * openS;
    emis = vec3(0.0);
    emis += (warm * 1.25 * glassAmt + signC * 1.7 * signB * (0.75 + 0.25 * sin(uTime * 2.0 + sid))) * night * openS;
  }
  if (roof && (m == 0 || m == 1 || m == 2 || m == 4)) alb = vCol;""")
# blimp screen / balloon glow material
rep("""  if (m == 9) c = vec3(0.62, 0.61, 0.58) * (amb + direct) + vec3(1.0, 0.62, 0.28) * 0.9 * night;""",
    """  if (m == 9) c = vec3(0.62, 0.61, 0.58) * (amb + direct) + vec3(1.0, 0.62, 0.28) * 0.9 * night;
  if (m == 18) c += hsv(fract(uTime * 0.05 + vPos.x * 0.004), 0.55, 1.0) * (0.35 + 1.8 * night) * (0.7 + 0.3 * sin(vPos.y * 1.5 - uTime * 4.0));""")

# =================================================================== CR HQ: 56 white fins following the profile
rep("""        frustum(g, circleRing(cx, cz, r0 * s0, seg), circleRing(cx, cz, r0 * s1, seg), t0 * h, t1 * h, glass, 7, bid, { smooth: true, cap: false, uFix: 2 * Math.PI * r0 });
      }""", """        frustum(g, circleRing(cx, cz, r0 * s0, seg), circleRing(cx, cz, r0 * s1, seg), t0 * h, t1 * h, glass, 7, bid, { smooth: true, cap: false, uFix: 2 * Math.PI * r0 });
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
      }""")

# =================================================================== road shader: green medians on two-way arterials
rep("""      if (ow < 0.5) {
        float yl = max(band(across, -0.2, 0.15, fwA), band(across, 0.2, 0.15, fwA)) * inJ;
        if (yl > 0.01) mc = vec3(0.95, 0.72, 0.15);
        m = max(m, yl);
        for (int k = 1; k < 3; k++) { if (float(k) >= lanes) break; float p = float(k) * lw; m = max(m, max(band(across, p, 0.15, fwA), band(across, -p, 0.15, fwA)) * dash * inJ); }
      } else {""", """      if (ow < 0.5) {
        float hm = med * 0.5 * step(0.5, inJ);
        lw = (hw - hm) / max(lanes, 1.0);
        float yl = max(band(across, -(hm + 0.2), 0.15, fwA), band(across, hm + 0.2, 0.15, fwA)) * inJ;
        if (yl > 0.01) mc = vec3(0.95, 0.72, 0.15);
        m = max(m, yl);
        for (int k = 1; k < 3; k++) { if (float(k) >= lanes) break; float p = hm + float(k) * lw; m = max(m, max(band(across, p, 0.15, fwA), band(across, -p, 0.15, fwA)) * dash * inJ); }
        medM = step(abs(across), hm) * step(0.1, hm);
      } else {""")
rep("""    float m = 0.0; vec3 mc = vec3(0.88);""", """    float m = 0.0; vec3 mc = vec3(0.88);
    float med = kind > 0.5 ? kind - 1.0 : 0.0, medM = 0.0;""")
rep("""    m *= fade * 0.92;
    c = mix(asph, mc, m) * lightL;""", """    m *= fade * 0.92 * (1.0 - medM);
    c = mix(asph, mc, m) * lightL;
    if (medM > 0.5) {
      float curbE = 1.0 - smoothstep(0.2, 0.2 + fwA, med * 0.5 - abs(across));
      vec3 mg = mix(vec3(0.22, 0.36, 0.15) * (0.8 + 0.4 * n1), vec3(0.72, 0.71, 0.68), curbE);
      c = mg * lightL;
    }""")

# road mesh: median width in kind, shrubs + parked cars
rep("""      const kind = pass === 0 ? -1 : 1;""", """      const med = pass === 1 && !r.oneway && lanes0 >= 2 ? (/^(primary|trunk)$/.test(r.hw) ? 3.2 : 2.2) : 0;
      const kind = pass === 0 ? -1 : 1 + med;
      if (pass === 1) {
        const djAt = (i, f) => Math.min(lerp(pj[i], pj[i + 1], f), lerp(nj[i], nj[i + 1], f));
        const wantPark = /^(residential|unclassified|service|tertiary)$/.test(r.hw);
        for (let i = 0; i + 1 < n; i++) {
          const a = P[i], b = P[i + 1], L = cum[i + 1] - cum[i]; if (L < 0.5) continue;
          const ux = (b[0] - a[0]) / L, uz = (b[1] - a[1]) / L, nx = -uz, nz = ux;
          if (med > 0) for (let t = 3.5; t < L; t += 7) { if (djAt(i, t / L) > 18 && inIsle(a[0] + ux * t, a[1] + uz * t, 10)) SHRUBS.push(a[0] + ux * t, a[1] + uz * t); }
          if (wantPark && PARKED.length < 8000 * 8) for (let t = 3.2; t < L; t += 6.4) {
            if (djAt(i, t / L) < 16) continue;
            for (const sg of (r.hw === "service" ? [1] : [1, -1])) {
              const hh = hash1(a[0] * 3.1 + a[1] * 1.7 + t * 5.3 + sg); if (hh > 0.52) continue;
              const off = hw - (r.hw === "service" ? 1.1 : 1.25), x = a[0] + ux * t + nx * off * sg, z = a[1] + uz * t + nz * off * sg;
              if (!inIsle(x, z, 8)) continue;
              const PAL = [[0.92, 0.92, 0.92], [0.07, 0.07, 0.08], [0.62, 0.63, 0.65], [0.35, 0.36, 0.38], [0.60, 0.08, 0.06], [0.10, 0.15, 0.30], [0.80, 0.78, 0.72], [0.16, 0.36, 0.78]];
              const col = PAL[Math.floor(hash1(hh * 91.7) * PAL.length)];
              PARKED.push(x, 0.02, z, Math.atan2(uz, ux) + (hh < 0.26 ? Math.PI : 0), col[0], col[1], col[2], 1);
            }
          }
        }
      }""")
rep("""/* ---------------- sports grounds, courts, pools ---------------- */""", """const SHRUBS = [], PARKED = [];

/* ---------------- sports grounds, courts, pools ---------------- */""")

# =================================================================== ground: shore foam + coastal boardwalk
rep("""  vec3 col = mix(lc, wc, smoothstep(0.35, 0.75, w));""", """  float sh2 = textureLod(uTex, clamp(uv, 0.0, 1.0), 2.0).r;
  float fd = 1.0 - sh2;
  float dcam = distance(vPos, uCam);
  float foamLine = smoothstep(0.62, 0.9, 0.5 + 0.5 * sin(fd * 24.0 - uTime * 1.25 + n1 * 5.0)) * smoothstep(0.03, 0.28, fd) * (1.0 - smoothstep(0.45, 0.6, fd));
  float foam = max(foamLine * 0.75, smoothstep(0.42, 0.6, fd)) * (1.0 - 0.6 * smoothstep(600.0, 2500.0, dcam));
  wc = mix(wc, vec3(0.90, 0.94, 0.95) * (amb + uLightCol * 0.8 * sh) + vec3(0.25, 0.2, 0.15) * uNight * 0.3, foam * 0.75);
  float e2 = 0.0007;
  vec2 gr = vec2(textureLod(uTex, uv + vec2(e2, 0.0), 2.0).r - textureLod(uTex, uv - vec2(e2, 0.0), 2.0).r, textureLod(uTex, uv + vec2(0.0, e2), 2.0).r - textureLod(uTex, uv - vec2(0.0, e2), 2.0).r);
  vec2 gd = normalize(gr + vec2(1e-5));
  float deck = smoothstep(0.035, 0.09, sh2) * (1.0 - smoothstep(0.3, 0.45, w)) * (1.0 - max(major, minor));
  float seam = abs(fract(dot(vPos.xz, vec2(-gd.y, gd.x)) / 0.3) - 0.5) * 2.0;
  vec3 wood = vec3(0.50, 0.36, 0.23) * (0.85 + 0.25 * vnoise(vPos.xz * 0.9)) * mix(0.75, 1.0, smoothstep(0.0, 0.2, seam) + smoothstep(700.0, 1500.0, dcam));
  lc = mix(lc, wood * lightL + vec3(1.0, 0.65, 0.35) * 0.18 * uNight, deck);
  vec3 col = mix(lc, wc, smoothstep(0.35, 0.75, w));""")

# =================================================================== templates: people, cyclists, balloons, blimp
rep("""  TPL.lamp = propTemplate(t => {""", """  TPL.person = propTemplate(t => {
    tplBox(t, 0, 0.45, 0.1, 0.2, 0.9, 0.16, [0.14, 0.15, 0.20], 0); tplBox(t, 0, 0.45, -0.1, 0.2, 0.9, 0.16, [0.14, 0.15, 0.20], 0);
    tplBox(t, 0, 1.22, 0, 0.28, 0.64, 0.46, [1, 1, 1], 1); tplBox(t, 0, 1.66, 0, 0.22, 0.24, 0.2, [0.86, 0.70, 0.56], 0);
  });
  TPL.bike = propTemplate(t => {
    tplBox(t, 0.55, 0.35, 0, 0.7, 0.7, 0.06, [0.1, 0.1, 0.1], 0); tplBox(t, -0.55, 0.35, 0, 0.7, 0.7, 0.06, [0.1, 0.1, 0.1], 0);
    tplBox(t, 0, 0.75, 0, 1.1, 0.08, 0.08, [1, 1, 1], 1); tplBox(t, -0.1, 1.2, 0, 0.35, 0.6, 0.42, [1, 1, 1], 1);
    tplBox(t, 0.05, 1.62, 0, 0.22, 0.24, 0.2, [0.86, 0.70, 0.56], 0); tplBox(t, 0.1, 0.62, 0, 0.18, 0.5, 0.3, [0.14, 0.15, 0.2], 0);
  });
  TPL.lamp = propTemplate(t => {""")
rep("""  TPL.sail = sail;
})();""", """  TPL.sail = sail;
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
})();""")

# =================================================================== walkers & cyclists
rep("""function streetLights(osm) {""", """function buildWalkers(osm) {
  const side = [], prom = [], cyc = [];
  for (const r of osm.roads) {
    const cum = [0]; for (let i = 1; i < r.pts.length; i++) cum.push(cum[i - 1] + Math.hypot(r.pts[i][0] - r.pts[i - 1][0], r.pts[i][1] - r.pts[i - 1][1]));
    const L = cum[cum.length - 1]; if (L < 30) continue;
    const ln = { r, cum, L };
    if (LANES[r.hw] && !r._ribbon) { ln.off = ROADW[r.hw] / 2 + 1.6; side.push(ln); }
    else if (/^(footway|cycleway|path|pedestrian)$/.test(r.hw)) {
      const m = r.pts[r.pts.length >> 1];
      const nearW = S.waterAt(m[0] + 35, m[1]) || S.waterAt(m[0] - 35, m[1]) || S.waterAt(m[0], m[1] + 35) || S.waterAt(m[0], m[1] - 35);
      ln.off = 0;
      if (r.hw === "cycleway") cyc.push(ln);
      if (nearW || hash1(m[0] + m[1]) < 0.35) prom.push(ln);
    }
  }
  const W = [], R = rng(808);
  const pick = (arr, n, kind) => {
    if (!arr.length) return;
    const tot = arr.reduce((a, l) => a + l.L, 0);
    for (let k = 0; k < n; k++) {
      let t = R() * tot, i = 0; while (i < arr.length - 1 && t > arr[i].L) { t -= arr[i].L; i++; }
      const l = arr[i], bike = kind === 1;
      const CL = [[0.85, 0.20, 0.18], [0.15, 0.30, 0.65], [0.92, 0.92, 0.90], [0.10, 0.10, 0.12], [0.95, 0.75, 0.20], [0.30, 0.55, 0.35], [0.85, 0.50, 0.60], [0.55, 0.55, 0.58]];
      W.push({ l, s: R() * l.L, dir: R() < 0.5 ? 1 : -1, lat: (l.off ? l.off * (R() < 0.5 ? 1 : -1) : (R() - 0.5) * 2.2) + (R() - 0.5) * 0.8, v: bike ? 4 + R() * 2 : 1.0 + R() * 0.6, col: CL[(R() * CL.length) | 0], bike });
    }
  };
  pick(side, 2600, 0); pick(prom, 1400, 0); pick(cyc.length ? cyc : prom, 320, 1);
  const peds = W.filter(w => !w.bike), bikes = W.filter(w => w.bike);
  return { peds, bikes, pInst: new Float32Array(peds.length * 8), bInst: new Float32Array(bikes.length * 8) };
}
function stepWalkers(Wk, dt, t) {
  for (const [list, buf] of [[Wk.peds, Wk.pInst], [Wk.bikes, Wk.bInst]]) {
    for (let i = 0; i < list.length; i++) {
      const w = list[i], l = w.l;
      w.s += w.v * dt * w.dir; if (w.s > l.L) { w.s = l.L; w.dir = -1; } if (w.s < 0) { w.s = 0; w.dir = 1; }
      let k = 1; while (k < l.cum.length - 1 && l.cum[k] < w.s) k++;
      const a = l.r.pts[k - 1], q = l.r.pts[k], seg = (l.cum[k] - l.cum[k - 1]) || 1, f = (w.s - l.cum[k - 1]) / seg;
      const dx = (q[0] - a[0]) / seg, dz = (q[1] - a[1]) / seg;
      const o = i * 8;
      buf[o] = a[0] + (q[0] - a[0]) * f - dz * w.lat; buf[o + 2] = a[1] + (q[1] - a[1]) * f + dx * w.lat;
      buf[o + 1] = w.bike ? 0.05 : 0.04 + Math.abs(Math.sin(t * 7 + i)) * 0.06;
      buf[o + 3] = Math.atan2(dz * w.dir, dx * w.dir); buf[o + 4] = w.col[0]; buf[o + 5] = w.col[1]; buf[o + 6] = w.col[2]; buf[o + 7] = 1;
    }
  }
}
function streetLights(osm) {""")
rep("""  S.carInst = instVAO(TPL.car, S.traffic.inst, true);""", """  S.carInst = instVAO(TPL.car, S.traffic.inst, true);
  S.parked = instVAO(TPL.car, new Float32Array(PARKED), false);
  S.walk = buildWalkers(osm);
  S.pedInst = instVAO(TPL.person, S.walk.pInst, true); S.bikeInst = instVAO(TPL.bike, S.walk.bInst, true);""")
rep("""  S.trees = [treeVAO(roundTpl, treeInstances(D.trees, 0.8, 0.7)),""", """  S.trees = [treeVAO(roundTpl, treeInstances(SHRUBS, 0.34, 0.12)), treeVAO(roundTpl, treeInstances(D.trees, 0.8, 0.7)),""")
rep("""<b>${fmt(S.trees[0].n + S.trees[1].n + S.trees[2].n)}</b> 棵树""", """<b>${fmt(S.trees[1].n + S.trees[2].n + S.trees[3].n)}</b> 棵树 · <b>${fmt(S.trees[0].n)}</b> 丛绿化带灌木""")

# draw parked cars / walkers
rep("""  gl.uniform1f(P.inst.u.uFar, 1800);
  gl.bindVertexArray(S.lampVAO.vao);""", """  gl.uniform1f(P.inst.u.uFar, 1600);
  gl.bindVertexArray(S.parked.vao); gl.drawElementsInstanced(gl.TRIANGLES, S.parked.count, gl.UNSIGNED_SHORT, 0, S.parked.n);
  stepWalkers(S.walk, reduceMotion ? 0 : dt, t);
  gl.uniform1f(P.inst.u.uFar, 750);
  gl.bindBuffer(gl.ARRAY_BUFFER, S.pedInst.ib); gl.bufferSubData(gl.ARRAY_BUFFER, 0, S.walk.pInst);
  gl.bindVertexArray(S.pedInst.vao); gl.drawElementsInstanced(gl.TRIANGLES, S.pedInst.count, gl.UNSIGNED_SHORT, 0, S.pedInst.n);
  gl.bindBuffer(gl.ARRAY_BUFFER, S.bikeInst.ib); gl.bufferSubData(gl.ARRAY_BUFFER, 0, S.walk.bInst);
  gl.bindVertexArray(S.bikeInst.vao); gl.drawElementsInstanced(gl.TRIANGLES, S.bikeInst.count, gl.UNSIGNED_SHORT, 0, S.bikeInst.n);
  gl.uniform1f(P.inst.u.uFar, 1800);
  gl.bindVertexArray(S.lampVAO.vao);""")
rep("""      gl.bindVertexArray(S.carInst.vao); gl.drawElementsInstanced(gl.TRIANGLES, S.carInst.count, gl.UNSIGNED_SHORT, 0, S.carInst.n);
    }""", """      gl.bindVertexArray(S.carInst.vao); gl.drawElementsInstanced(gl.TRIANGLES, S.carInst.count, gl.UNSIGNED_SHORT, 0, S.carInst.n);
      gl.bindVertexArray(S.parked.vao); gl.drawElementsInstanced(gl.TRIANGLES, S.parked.count, gl.UNSIGNED_SHORT, 0, S.parked.n);
    }""")

# =================================================================== balloons, airship, sky lanterns
rep("""  // drone show over the bay
  AIR.show = initShow();""", """  // hot-air balloons, an airship and sky lanterns
  const RBl = rng(2468);
  AIR.balloons = TPL.balloons.map((tp, i) => ({ tp, c: [(RBl() - 0.5) * 7000, (RBl() - 0.5) * 7000], r: 600 + RBl() * 1600, y: 380 + RBl() * 700, w: (RBl() < 0.5 ? -1 : 1) * (0.006 + RBl() * 0.008), ph: RBl() * 6.28, bob: RBl() * 6 }));
  AIR.blimp = { r: 3900, y: 620, w: 0.012, ph: 1.2 };
  const pf = D.palms.length ? D.palms : D.trees;
  AIR.lanterns = Array.from({ length: 220 }, (_, i) => { const k = (Math.floor(RBl() * pf.length / 2)) * 2; return { x0: pf[k], z0: pf[k + 1], t0: RBl() * 600, vy: 1.4 + RBl() * 1.2, dx: (RBl() - 0.3) * 0.8, dz: (RBl() - 0.3) * 0.8, ph: RBl() * 6 }; }).filter(L => inIsle(L.x0, L.z0, 20));
  // drone show over the bay
  AIR.show = initShow();""")
rep("""  // street lights
  if (night > 0.3)""", """  // balloons and the airship
  (AIR.balloons || []).forEach((B, i) => {
    const a = t * B.w + B.ph, x = B.c[0] + Math.cos(a) * B.r, z = B.c[1] + Math.sin(a) * B.r, y = B.y + Math.sin(t * 0.15 + B.bob) * 25;
    B.pos = [x, y, z];
    emit(B.tp, [x, y, z], t * 0.02 + i, 0, 0, 1.6);
    if (night > 0.3 && Math.sin(t * 0.7 + i * 2) > 0.6) light(x, y + 1, z, 5 * night, 2.6 * night, 0.8 * night, 22);
  });
  if (AIR.blimp) {
    const Bm = AIR.blimp, a = t * Bm.w + Bm.ph;
    const x = Math.cos(a) * Bm.r, z = Math.sin(a) * Bm.r, yaw = a + Math.PI / 2;
    Bm.pos = [x, Bm.y, z]; Bm.dir = [Math.cos(yaw), 0, Math.sin(yaw)];
    emit(TPL.blimp, Bm.pos, yaw, 0.02, 0, 1.4);
    if (blink(0.2, 0.9)) light(x - Math.cos(yaw) * 52, Bm.y + 8, z - Math.sin(yaw) * 52, 8, 8, 8, 14);
  }
  // sky lanterns rising from the waterfront at night
  if (night > 0.6) for (const Ln of (AIR.lanterns || [])) {
    const age = (t + Ln.t0) % 600, y = 5 + age * Ln.vy;
    if (y > 950) continue;
    const fl = 0.8 + 0.2 * Math.sin(t * 9 + Ln.ph);
    light(Ln.x0 + age * Ln.dx + Math.sin(t * 0.3 + Ln.ph) * 6, y, Ln.z0 + age * Ln.dz, 3.2 * fl, 1.5 * fl, 0.45 * fl, 3.2);
  }
  // street lights
  if (night > 0.3)""")
rep("""for (const [v, t] of [["plane", "跟随航班"], ["heli", "跟随直升机"], ["quad", "跟随配送无人机"], ["boat", "跟随渡轮"],""", """for (const [v, t] of [["plane", "跟随航班"], ["blimp", "跟随飞艇"], ["balloon", "跟随热气球"], ["heli", "跟随直升机"], ["quad", "跟随配送无人机"], ["boat", "跟随渡轮"],""")
rep("""    else if (f.kind === "boat") {""", """    else if (f.kind === "blimp") { obj = AIR.blimp; back = 160; up = 30; }
    else if (f.kind === "balloon") { const B = AIR.balloons[0]; obj = B; const a = t * B.w + B.ph; B.dir = norm3([-Math.sin(a) * Math.sign(B.w), 0, Math.cos(a) * Math.sign(B.w)]); back = 70; up = 8; }
    else if (f.kind === "boat") {""")
rep("""    const items = [`瀑布 ${FALLS.groups.length} 道`,""", """    const items = [`热气球 ${(AIR.balloons || []).length}`, `飞艇 1`, `瀑布 ${FALLS.groups.length} 道`,""")
rep("""    if (AIR.show.active) items.push(`<b>灯光秀进行中 · ${AIR.show.N} 架</b>`); else items.push("灯光秀 19:00 后开始");""",
    """    if (AIR.show.active) items.push(`<b>灯光秀进行中 · ${AIR.show.N} 架 · 孔明灯升空</b>`); else items.push("灯光秀与孔明灯 19:00 后开始");""")

open(sys.argv[2], "w", encoding="utf-8").write(s)
print("ok")
