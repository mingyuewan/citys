/* Building / island / bridge mesh shader (material ids 0–20) and its shadow-depth variant.
   Verbatim from src/city.src.html (meshVS, meshFS, shadowVS, emptyFS). */
import * as THREE from "three";
import { HEAD, COMMON, rawMat } from "./common.js";

export const meshVS = HEAD + `
layout(location=0) in vec3 aPos; layout(location=1) in vec3 aNrm; layout(location=2) in vec3 aCol; layout(location=3) in vec2 aUv; layout(location=4) in float aBid; layout(location=5) in float aMat;
uniform mat4 uVP; uniform mat4 uLightVP; uniform float uRise; uniform float uMaxR; uniform float uNOff;
out vec3 vPos; out vec3 vNrm; out vec3 vCol; out vec2 vUv; out vec4 vLight; flat out float vBid; flat out float vMat;
#ifdef MODEL
uniform mat4 modelMatrix;
#endif
void main(){
  vec3 p = aPos; vec3 nrm = aNrm;
#ifdef MODEL
  p = (modelMatrix * vec4(aPos, 1.0)).xyz; nrm = normalize(mat3(modelMatrix) * aNrm);
#else
  float d = length(p.xz) / uMaxR;
  float g = clamp(uRise * 1.6 - d * 0.6, 0.0, 1.0); g = g*g*(3.0-2.0*g);
  if (aMat < 9.5) p.y *= max(g, 0.002);
#endif
  vPos = p; vNrm = nrm; vCol = aCol; vUv = aUv; vBid = aBid; vMat = aMat;
  vLight = uLightVP * vec4(p + nrm * uNOff, 1.0);
  gl_Position = uVP * vec4(p, 1.0);
}`;
export const meshFS = HEAD + COMMON + `
in vec3 vPos; in vec3 vNrm; in vec3 vCol; in vec2 vUv; in vec4 vLight; flat in float vBid; flat in float vMat;
uniform float uSel; uniform vec3 uAccent; uniform float uLit;
uniform sampler2D uRock; uniform sampler2D uFacade; uniform vec2 uTexOn;   // GPT Image textures (x: rock, y: facade loaded)
out vec4 o;
float lineAA(float f, float w, float fw){ return smoothstep(w - fw, w + fw, f) - smoothstep(1.0 - w - fw, 1.0 - w + fw, f); }
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
}
void main(){
  vec3 n = normalize(vNrm);
  vec3 nO = n;
  vec3 V = normalize(uCam - vPos);
  if (dot(n, V) < 0.0 && vMat != 6.0) n = -n;
  float camD = distance(vPos, uCam);
  float inNear = 1.0 - smoothstep(220.0, 650.0, camD);
  vec3 inDay = vec3(0.0); float inF = 0.0;
  int m = int(vMat + 0.5);
  bool roof = n.y > 0.6;
  float sh = shadowAt(vLight);
  float ndl = max(dot(n, uLightDir), 0.0);
  vec3 skyUp = skyAmb();
  vec3 amb = mix(vec3(0.30, 0.29, 0.27) * (1.0 - uNight * 0.9), skyUp * 0.95, n.y * 0.5 + 0.5) * (1.0 - uNight * 0.55);
  amb += vec3(0.010, 0.012, 0.020) * uNight;
  amb += max(-n.y, 0.0) * (vec3(0.55, 0.57, 0.62) * (1.0 - uNight) + vec3(0.07, 0.04, 0.02) * uNight);
  vec3 direct = uLightCol * ndl * sh;
  float ao = (roof || m >= 10) ? 1.0 : mix(0.55, 1.0, smoothstep(0.0, 14.0, vPos.y));
  vec3 alb = vCol, emis = vec3(0.0);
  float glassAmt = 0.0;
  vec3 facadeK = vec3(1.0);
  float hb = fract(sin(vBid * 0.731 + 0.1) * 43758.5453);
  float lit = uLit * (0.55 + 0.6 * hb);
  float night = uNight;
  vec3 warm = vec3(1.0, 0.72, 0.42), cool = vec3(0.80, 0.88, 1.0);
  if (!roof && vUv.x > -0.5) {
    if (m == 0 || m == 7) {
      vec2 cell = vec2(vUv.x / 1.5, vUv.y / 4.0); vec2 f = fract(cell); vec2 fw = fwidth(cell);
      float fade = 1.0 - smoothstep(0.5, 1.4, max(fw.x, fw.y));
      float mull = mix(0.86, lineAA(f.x, 0.06, fw.x), fade);
      float span = mix(0.82, smoothstep(0.17 - fw.y, 0.17 + fw.y, f.y), fade);
      glassAmt = mull * span;
      alb = mix(vCol * 1.35 + 0.08, vCol, glassAmt);
      if (uTexOn.y > 0.5) {   // curtain-wall texture: one tile = 10×10 bays of the procedural grid; strongest where the grid fades out
        vec3 ft = texture(uFacade, vUv / (m == 7 ? vec2(18.0, 26.0) : vec2(15.0, 40.0))).rgb;
        vec3 fm = textureLod(uFacade, vec2(0.5), 12.0).rgb;
        facadeK = mix(vec3(1.0), ft / max(fm, vec3(0.05)), (m == 7 ? 0.3 : 0.55) * (1.0 - 0.5 * fade));
      }
      vec2 bay = floor(vec2(vUv.x / 6.0, vUv.y / 4.0));
      float epo = floor(uTime / 55.0 + h31(vec3(bay.yx, vBid + 2.0)) * 9.0);
      float on = step(h31(vec3(bay + epo * 0.573, vBid)), lit * 0.5);
      vec3 lc = mix(cool * vec3(0.85, 0.95, 1.0), warm, step(0.55, h31(vec3(bay.yx, vBid + 3.0))));
      float bright = (m == 7 ? 0.35 : 0.8) * (0.6 + 0.6 * h31(vec3(bay.x, bay.y + 7.0, vBid)));
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
        emis = vec3(1.0, 0.82, 0.58) * 0.85 * glassAmt * night; inF *= 0.5;
      }
      if (vUv.y > 30.0 && mod(vUv.y, 52.0) < 4.2) {
        float lv = step(0.5, fract(vUv.y / 0.42));
        alb = vec3(0.46, 0.48, 0.50) * (0.8 + 0.25 * lv); glassAmt = 0.0; emis = vec3(0.0); inF = 0.0;
      }
      if (m == 7) {
        float fin = mix(0.15, 1.0 - lineAA(fract(vUv.x / 2.4), 0.12, fwidth(vUv.x / 2.4)), fade);
        alb = mix(alb, vec3(0.80, 0.84, 0.86), fin * 0.6);
        glassAmt *= 1.0 - fin * 0.5;
        float wave = 0.5 + 0.5 * sin(vUv.y * 0.045 - uTime * 1.3 + sin(vUv.x * 0.03 + uTime * 0.4) * 2.0);
        float hue = fract(uTime * 0.035 + vUv.y * 0.0012 + vBid * 0.17);
        vec3 led = hsv(hue, 0.7, 1.0) * pow(wave, 3.0) * 1.7 + vec3(0.9, 0.95, 1.0) * fin * 0.3;
        emis += led * night * smoothstep(0.0, 6.0, vPos.y);
      }
      alb *= facadeK;
    } else if (m == 1) {
      vec2 cell = vec2(vUv.x / 3.6, vUv.y / 3.0); vec2 f = fract(cell); vec2 fw = fwidth(cell); vec2 id = floor(cell);
      float fade = 1.0 - smoothstep(0.5, 1.4, max(fw.x, fw.y));
      float win = mix(0.33, lineAA(f.x, 0.2, fw.x) * lineAA(f.y, 0.22, fw.y), fade);
      float slab = (1.0 - smoothstep(0.065, 0.065 + fw.y, f.y)) * fade;
      float under = (smoothstep(0.065, 0.09, f.y) - smoothstep(0.15, 0.2, f.y)) * fade;
      bool balc = mod(id.x + floor(hb * 3.0), 3.0) < 1.0;
      float railM = balc ? (smoothstep(0.08, 0.1, f.y) - smoothstep(0.34, 0.36, f.y)) * lineAA(f.x, 0.04, fw.x) * fade : 0.0;
      float recess = (smoothstep(0.66, 0.70, f.y) - smoothstep(0.76, 0.78, f.y)) * lineAA(f.x, 0.2, fw.x) * lineAA(f.y, 0.22, fw.y) * fade;
      glassAmt = win * 0.85 * (1.0 - recess * 0.6) + railM * 0.3;
      alb = vCol * (1.0 + 0.14 * slab - 0.24 * under);
      alb = mix(alb, vec3(0.55, 0.63, 0.67), railM * 0.55);
      float ep = floor(uTime / 45.0 + h31(vec3(id.yx, vBid + 9.0)) * 9.0);
      float on = step(h31(vec3(id + ep * 0.731, vBid)), lit * 0.48);
      float hv = h31(vec3(id.yx, vBid + 5.0));
      vec3 lc = hv > 0.84 ? cool : hv > 0.7 ? vec3(1.0, 0.86, 0.66) : warm;
      float curtain = 0.45 + 0.55 * h31(vec3(id.x + 3.0, id.y, vBid));
      vec3 roomL = vec3(1.0);
      if (inNear > 0.001) {
        float dF, cl; vec3 rc = roomShade(nO, V, vUv, vec3(3.6, 3.0, 4.5), vBid + 7.0, dF, cl);
        roomL = mix(vec3(1.0), rc * (0.4 + 0.8 * dF) * 1.1 + cl * 0.5, inNear);
        inDay = rc * (0.25 + 0.75 * dF); inF = inNear * win * 0.85;
      }
      emis += lc * roomL * on * win * 1.1 * curtain * night;
      float ac = step(h31(vec3(id, vBid + 21.0)), 0.42) * step(0.74, f.x) * step(f.x, 0.95) * step(0.12, f.y) * step(f.y, 0.31) * fade;
      alb = mix(alb, vec3(0.86, 0.86, 0.84) * (0.86 + 0.14 * step(0.5, fract(f.y * 45.0))), ac);
      glassAmt *= 1.0 - ac; inF *= 1.0 - ac;
    } else if (m == 2) {
      vec2 cell = vec2(vUv.x / 3.0, vUv.y / 5.0); vec2 f = fract(cell); vec2 fw = fwidth(cell);
      float fade = 1.0 - smoothstep(0.5, 1.4, max(fw.x, fw.y));
      glassAmt = mix(0.8, lineAA(f.x, 0.04, fw.x) * smoothstep(0.12, 0.14, f.y), fade);
      alb = mix(vec3(0.72, 0.72, 0.70), vCol, glassAmt);
      vec3 lc = mix(warm, cool, step(0.5, h31(vec3(floor(vUv.x / 12.0), 1.0, vBid))));
      emis += lc * glassAmt * 0.85 * night * step(h31(vec3(floor(vUv / vec2(12.0, 5.0)), vBid)), 0.7);
    } else if (m == 4) {
      vec2 cell = vec2(vUv.x / 3.0, vUv.y / 3.0); vec2 f = fract(cell); vec2 fw = fwidth(cell); vec2 id = floor(cell);
      float fade = 1.0 - smoothstep(0.5, 1.4, max(fw.x, fw.y));
      float win = mix(0.2, lineAA(f.x, 0.3, fw.x) * lineAA(f.y, 0.28, fw.y), fade);
      glassAmt = win * 0.6;
      float on = step(h31(vec3(id, vBid)), lit * 0.95);
      vec3 lc = mix(warm, vec3(0.85, 0.95, 1.0), step(0.55, h31(vec3(id.yx, vBid))));
      float grille = max(step(0.82, fract(vUv.x / 0.2)), step(0.85, fract(vUv.y / 0.35))) * win * fade * step(0.35, h31(vec3(id, vBid + 4.0)));
      alb = mix(alb, vec3(0.30, 0.30, 0.32), grille * 0.8);
      glassAmt *= 1.0 - grille * 0.6;
      emis += lc * on * win * 1.3 * night * (1.0 - grille * 0.5);
      float ac = step(h31(vec3(id, vBid + 33.0)), 0.5) * step(0.04, f.x) * step(f.x, 0.26) * step(0.1, f.y) * step(f.y, 0.3) * fade;
      alb = mix(alb, vec3(0.84, 0.84, 0.82), ac); glassAmt *= 1.0 - ac;
      if (vUv.y < 3.4) { float sign = step(0.45, h31(vec3(floor(vUv.x / 5.0), 2.0, vBid))); emis += hsv(h31(vec3(floor(vUv.x / 5.0), 9.0, vBid)), 0.75, 1.0) * sign * 1.4 * night * smoothstep(1.2, 2.6, vUv.y); }
    } else if (m == 20) {
      vec2 cc = vec2(vUv.x / 6.0, vUv.y / 3.6); vec2 f = fract(cc); vec2 fw = fwidth(cc); vec2 id = floor(cc);
      float colm = 1.0 - lineAA(f.x, 0.07, fw.x);
      float slab = 1.0 - smoothstep(0.1, 0.1 + fw.y, f.y);
      float solid = max(colm, slab);
      float net = step(h31(vec3(id, vBid)), 0.78);
      vec3 netC = vec3(0.17, 0.45, 0.24) * (0.85 + 0.2 * step(0.5, fract(vUv.x * 2.0)));
      alb = mix(mix(vec3(0.14, 0.14, 0.15), netC, net), vec3(0.64, 0.63, 0.60), solid);
      emis += vec3(1.0, 0.9, 0.72) * 0.9 * night * (1.0 - solid) * (1.0 - net) * step(h31(vec3(id.yx, vBid)), 0.3);
    } else if (m == 5) {
      glassAmt = 0.6;
    } else if (m == 6) {
      vec2 q = vUv / 8.0;
      float l1 = abs(fract(q.x + q.y) - 0.5), l2 = abs(fract(q.x - q.y) - 0.5);
      float fw = fwidth(q.x + q.y) * 1.5;
      float latt = max(1.0 - smoothstep(0.03, 0.03 + fw, l1), 1.0 - smoothstep(0.03, 0.03 + fw, l2));
      alb = mix(vec3(0.55, 0.62, 0.66), vCol, latt);
      glassAmt = (1.0 - latt) * 0.6;
      emis += (1.0 - latt) * vec3(0.55, 0.78, 1.0) * 1.1 * night;
    }
  }
  if (!roof && vUv.x > -0.5 && (m == 1 || m == 2 || m == 4) && vUv.y < 4.6) {
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
  if (roof && (m == 0 || m == 1 || m == 2 || m == 4)) alb = vCol;
  if (roof && m == 11) alb = vCol * (0.8 + 0.4 * vnoise(vPos.xz * 0.15));
  if (m == 10) {
    float nA = vnoise(vec2(vUv.x * 0.02, vPos.y * 0.02)), nB = vnoise(vec2(vUv.x * 0.11, vPos.y * 0.13));
    float band = 0.5 + 0.5 * sin(vPos.y * 0.09 + nA * 7.0);
    alb = vCol * (0.78 + 0.22 * band) * (0.8 + 0.4 * nB);
    if (uTexOn.x > 0.5) {   // rock strata texture at two scales, normalised by its mean so the page's tones are kept
      vec2 ru = vec2(vUv.x, vPos.y);
      vec3 rm = max(textureLod(uRock, vec2(0.5), 12.0).rgb, vec3(0.05));
      vec3 r1 = texture(uRock, ru / vec2(260.0, 180.0)).rgb / rm, r2 = texture(uRock, ru / vec2(41.0, 29.0)).rgb / rm;
      alb = vCol * (0.86 + 0.14 * band) * r1 * mix(vec3(1.0), r2, 0.5 * (1.0 - smoothstep(600.0, 2600.0, camD)));
    }
    alb = mix(alb, vec3(0.46, 0.34, 0.24), smoothstep(-90.0, -10.0, vPos.y) * 0.6);
    float moss = smoothstep(0.35, 0.8, n.y) * smoothstep(0.4, 0.7, nA);
    alb = mix(alb, vec3(0.24, 0.36, 0.17), moss);
    glassAmt = 0.0;
  } else if (m == 11) {
    alb = vCol * (0.8 + 0.4 * vnoise(vec2(vUv.x * 0.07, vPos.z * 0.07 + vPos.y * 0.2)));
    glassAmt = 0.0;
  } else if ((m >= 12 && m <= 16) || m == 19) {
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
    } else if (m == 19) {
      float ax = abs(q.x), ay = abs(q.y);
      alb = vec3(0.21, 0.215, 0.225) * (0.88 + 0.16 * vnoise(q * 0.6)) * (1.0 - 0.08 * smoothstep(0.6, 0.8, vnoise(q * 0.25)));
      float row = step(W * 0.5 - 6.0, ay) * step(ay, W * 0.5 - 0.6);
      float stall = (1.0 - smoothstep(lw, lw + fq, abs(fract(q.x / 2.5 + 0.5) - 0.5) * 2.5)) * row * step(ax, L * 0.5 - 0.5);
      float edge = (1.0 - smoothstep(lw, lw + fq, abs(ay - (W * 0.5 - 6.0)))) * step(ax, L * 0.5 - 0.5);
      float border = max((1.0 - smoothstep(lw, lw + fq, abs(ax - (L * 0.5 - 0.5)))) * step(ay, W * 0.5 - 0.6), (1.0 - smoothstep(lw, lw + fq, abs(ay - (W * 0.5 - 0.6)))) * step(ax, L * 0.5 - 0.5));
      ln = clamp(stall + edge * 0.6 + border, 0.0, 1.0);
      emis += vec3(1.0, 0.7, 0.4) * 0.08 * uNight;
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
  }
  vec3 c = alb * (amb * 0.72 + direct * 0.95) * ao;
  if (glassAmt > 0.0) {
    vec3 R = reflect(-V, n);
    vec3 refl = skyColor(R);
    float F = 0.04 + 0.96 * pow(1.0 - max(dot(n, V), 0.0), 5.0);
    float spec = pow(max(dot(R, uLightDir), 0.0), 220.0) * sh;
    vec3 base0 = mix(vCol * facadeK * 0.20 * (amb + direct), inDay * (amb * 0.55 + direct * 0.08 + 0.02), clamp(inF / max(glassAmt, 0.01), 0.0, 1.0));
    vec3 gc = base0 + refl * (0.10 + 0.62 * F) * mix(1.0, 0.3, uNight) + uLightCol * spec * 2.0 * (1.0 - uNight * 0.8);
    c = mix(c, gc * ao, glassAmt);
  }
  if (m == 9) c = vec3(0.62, 0.61, 0.58) * (amb + direct) + vec3(1.0, 0.62, 0.28) * 0.9 * night;
  if (m == 18) c += hsv(fract(uTime * 0.05 + vPos.x * 0.004), 0.55, 1.0) * (0.35 + 1.8 * night) * (0.7 + 0.3 * sin(vPos.y * 1.5 - uTime * 4.0));
  c += emis;
  if (uSel >= 0.0 && abs(vBid - uSel) < 0.5) { float rim = pow(1.0 - abs(dot(n, V)), 2.0); c = mix(c, uAccent * (1.1 + 0.3 * sin(uTime * 4.0)), 0.18 + 0.55 * rim); }
  o = vec4(fogIt(c, vPos), 1.0);
}`;
export const shadowVS = HEAD + `
layout(location=0) in vec3 aPos; layout(location=5) in float aMat;
uniform mat4 uLightVP; uniform float uRise; uniform float uMaxR;
#ifdef MODEL
uniform mat4 modelMatrix;
#endif
void main(){ vec3 p = aPos;
#ifdef MODEL
  p = (modelMatrix * vec4(aPos, 1.0)).xyz;
#else
  float d = length(p.xz) / uMaxR; float g = clamp(uRise * 1.6 - d * 0.6, 0.0, 1.0); g = g*g*(3.0-2.0*g); if (aMat < 9.5) p.y *= max(g, 0.002);
#endif
  gl_Position = uLightVP * vec4(p, 1.0); }`;
export const emptyFS = HEAD + `out vec4 o; void main(){ o = vec4(1.0); }`;

// front faces only: the meshes are oriented by world.js orient()
export const makeMeshMaterial = () => rawMat(meshVS, meshFS, { uSel: { value: -1 }, uAccent: { value: [0.85, 0.45, 0.12] }, uLit: { value: 0.35 } }, { side: THREE.FrontSide });
export const makeShadowMaterial = () => rawMat(shadowVS, emptyFS, {}, { polygonOffset: true, polygonOffsetFactor: 1.5, polygonOffsetUnits: 2.0, colorWrite: false });
// aerial models (air.js): placed by their object transform, not lifted by the rise, both sides drawn
export const makeModelMaterial = () => rawMat(meshVS, meshFS, { uSel: { value: -1 }, uAccent: { value: [0.85, 0.45, 0.12] }, uLit: { value: 0.35 } }, { defines: { MODEL: "" } });
export const makeModelShadowMaterial = () => rawMat(shadowVS, emptyFS, {}, { defines: { MODEL: "" }, polygonOffset: true, polygonOffsetFactor: 1.5, polygonOffsetUnits: 2.0, colorWrite: false });
