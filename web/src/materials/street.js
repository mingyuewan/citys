/* Road surfaces, trees and instanced props (cars, people, bikes, lamps, signals, bus stops) with their shadow-depth
   variants. Verbatim from src/city.src.html (roadVS/FS, treeVS/FS, treeShadowVS, instVS/FS, instShadowVS). */
import * as THREE from "three";
import { HEAD, COMMON, rawMat } from "./common.js";
import { emptyFS } from "./building.js";

export const roadVS = HEAD + `
layout(location=0) in vec3 aPos; layout(location=1) in vec4 aA; layout(location=2) in vec4 aB;
uniform mat4 uVP; uniform mat4 uLightVP; out vec3 vPos; out vec4 vA; out vec4 vB; out vec4 vLight;
void main(){ vPos = aPos; vA = aA; vB = aB; vLight = uLightVP * vec4(aPos + vec3(0.0, 0.6, 0.0), 1.0); gl_Position = uVP * vec4(aPos, 1.0); }`;
export const roadFS = HEAD + COMMON + `
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
  vec3 amb = skyAmb() * 0.62 * (1.0 - uNight * 0.8);
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
    vec3 asph = vec3(0.16, 0.165, 0.175) * (0.86 + 0.18 * n1 * fade + 0.12 * n2) * (1.0 + (vnoise(vPos.xz * 2.7) - 0.5) * 0.12 * fade);
    float lw = ow > 0.5 ? (2.0 * hw) / max(lanes, 1.0) : hw / max(lanes, 1.0);
    float m = 0.0; vec3 mc = vec3(0.88);
    float med = kind > 0.5 ? kind - 1.0 : 0.0, medM = 0.0;
    if (lanes > 0.5) {
      float dash = step(fract(along / 12.0), 0.5);
      float inJ = smoothstep(13.0, 15.0, dj);
      if (ow < 0.5) {
        float hm = med * 0.5 * step(0.5, inJ);
        lw = (hw - hm) / max(lanes, 1.0);
        float yl = max(band(across, -(hm + 0.2), 0.15, fwA), band(across, hm + 0.2, 0.15, fwA)) * inJ;
        if (yl > 0.01) mc = vec3(0.95, 0.72, 0.15);
        m = max(m, yl);
        for (int k = 1; k < 3; k++) { if (float(k) >= lanes) break; float p = hm + float(k) * lw; m = max(m, max(band(across, p, 0.15, fwA), band(across, -p, 0.15, fwA)) * dash * inJ); }
        medM = step(abs(across), hm) * step(0.1, hm);
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
    if (lanes > 0.5) {
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
    m *= fade * 0.92 * (1.0 - medM);
    c = mix(asph, mc, m) * lightL;
    if (medM > 0.5) {
      float curbE = 1.0 - smoothstep(0.2, 0.2 + fwA, med * 0.5 - abs(across));
      vec3 mg = mix(vec3(0.22, 0.36, 0.15) * (0.8 + 0.4 * n1), vec3(0.72, 0.71, 0.68), curbE);
      c = mg * lightL;
    }
    vec3 V = normalize(uCam - vPos);
    float F = pow(1.0 - max(V.y, 0.0), 5.0);
    c += skyColor(reflect(-V, vec3(0, 1, 0))) * F * 0.12 * (1.0 - uNight);
    float major = step(1.5, lanes);
    c += vec3(1.0, 0.6, 0.25) * uNight * (0.09 + 0.13 * major) * (0.7 + 0.4 * n2);
    c += mc * m * uNight * 0.3;
  }
  o = vec4(fogIt(c, vPos), 1.0);
}`;
export const treeVS = HEAD + `
layout(location=0) in vec3 aPos; layout(location=1) in vec3 aNrm; layout(location=2) in float aPart; layout(location=3) in vec4 aInst; layout(location=4) in float aY;
uniform mat4 uVP; uniform mat4 uLightVP; uniform float uRise; uniform float uMaxR; uniform float uNOff; uniform float uTime;
out vec3 vPos; out vec3 vNrm; out vec4 vLight; out float vPart; out float vHue;
void main(){
  float s = aInst.z;
  vec3 p = aPos * vec3(s, s * (0.85 + aInst.w * 0.35), s);
  float ang = aInst.w * 40.0; float c = cos(ang), si = sin(ang);
  p.xz = mat2(c, -si, si, c) * p.xz;
  float sway = sin(uTime * 1.3 + aInst.x * 0.05) * 0.02 * p.y;
  p.x += sway * aPart;
  float d = length(aInst.xy) / uMaxR; float g = clamp(uRise * 1.6 - d * 0.6, 0.0, 1.0); g = g*g*(3.0-2.0*g);
  p.y *= max(g, 0.002);
  p += vec3(aInst.x, aY, aInst.y);
  vec2 rn = mat2(c, -si, si, c) * aNrm.xz;
  vPos = p; vNrm = normalize(vec3(rn.x, aNrm.y, rn.y));
  vLight = uLightVP * vec4(p + vNrm * uNOff, 1.0); vPart = aPart; vHue = aInst.w;
  gl_Position = uVP * vec4(p, 1.0);
}`;
export const treeFS = HEAD + COMMON + `
in vec3 vPos; in vec3 vNrm; in vec4 vLight; in float vPart; in float vHue; out vec4 o;
void main(){
  vec3 n = normalize(vNrm);
  float sh = shadowAt(vLight);
  vec3 alb = vPart > 0.5 ? mix(vec3(0.20, 0.36, 0.16), vec3(0.34, 0.46, 0.20), vHue) : vec3(0.32, 0.24, 0.18);
  float wrap = max(dot(n, uLightDir) * 0.7 + 0.3, 0.0);
  vec3 amb = mix(vec3(0.20, 0.22, 0.18), skyAmb(), n.y * 0.5 + 0.5) * (1.0 - uNight * 0.85);
  vec3 c = alb * (amb * 0.8 + uLightCol * wrap * sh) * mix(0.75, 1.0, smoothstep(0.0, 8.0, vPos.y));
  c += vec3(0.05, 0.04, 0.02) * uNight * smoothstep(9.0, 2.0, vPos.y) * step(-1.0, vPos.y) * step(vPos.y, 30.0);
  o = vec4(fogIt(c, vPos), 1.0);
}`;
export const treeShadowVS = HEAD + `
layout(location=0) in vec3 aPos; layout(location=3) in vec4 aInst; layout(location=4) in float aY;
uniform mat4 uLightVP; uniform float uRise; uniform float uMaxR;
void main(){ float s = aInst.z; vec3 p = aPos * vec3(s, s * (0.85 + aInst.w * 0.35), s);
  float d = length(aInst.xy) / uMaxR; float g = clamp(uRise * 1.6 - d * 0.6, 0.0, 1.0); p.y *= max(g*g*(3.0-2.0*g), 0.002);
  p += vec3(aInst.x, aY, aInst.y);
  gl_Position = uLightVP * vec4(p, 1.0); }`;
export const instVS = HEAD + `
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
export const instFS = HEAD + COMMON + `
in vec3 vPos; in vec3 vNrm; in vec3 vCol; in vec4 vLight; flat in float vPart; out vec4 o;
void main(){
  vec3 n = normalize(vNrm); vec3 V = normalize(uCam - vPos);
  float sh = shadowAt(vLight);
  vec3 amb = mix(vec3(0.24, 0.24, 0.23), skyAmb(), n.y * 0.5 + 0.5) * (1.0 - uNight * 0.85);
  vec3 c = vCol * (amb * 0.8 + uLightCol * max(dot(n, uLightDir), 0.0) * sh);
  vec3 R = reflect(-V, n); float F = 0.04 + 0.96 * pow(1.0 - max(dot(n, V), 0.0), 5.0);
  float gloss = vPart > 0.5 ? 1.0 : 0.25;
  c += skyColor(R) * F * 0.55 * gloss * (1.0 - uNight * 0.7) + uLightCol * pow(max(dot(R, uLightDir), 0.0), 80.0) * sh * gloss;
  o = vec4(fogIt(c, vPos), 1.0);
}`;
export const instShadowVS = HEAD + `
layout(location=0) in vec3 aPos; layout(location=4) in vec4 aI0; layout(location=5) in vec4 aI1;
uniform mat4 uLightVP;
void main(){ vec3 p = aPos; p.x *= aI1.w; if (aI1.w > 1.5) p.y *= 1.75; float c = cos(aI0.w), s = sin(aI0.w);
  gl_Position = uLightVP * vec4(vec3(p.x * c - p.z * s, p.y, p.x * s + p.z * c) + aI0.xyz, 1.0); }`;

// sidewalks are drawn first, carriageways over them on the same plane: painter's order through polygon offset
export const makeRoadMaterials = () => [
  rawMat(roadVS, roadFS, {}, { polygonOffset: true, polygonOffsetFactor: 3, polygonOffsetUnits: 6 }),
  rawMat(roadVS, roadFS, {}, { polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 2 }),
];
export const makeTreeMaterial = () => rawMat(treeVS, treeFS);
export const makeTreeShadowMaterial = () => rawMat(treeShadowVS, emptyFS, {}, { polygonOffset: true, polygonOffsetFactor: 1.5, polygonOffsetUnits: 2.0, colorWrite: false });
// uFar: instances farther than this from the camera are dropped in the vertex shader (cells beyond it are not drawn at all)
export const makeInstMaterial = far => rawMat(instVS, instFS, { uFar: { value: far } });
export const makeInstShadowMaterial = () => rawMat(instShadowVS, emptyFS, {}, { polygonOffset: true, polygonOffsetFactor: 1.5, polygonOffsetUnits: 2.0, colorWrite: false });
