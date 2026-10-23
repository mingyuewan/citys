/* Ground: land-use surfaces, road paint from the class map, the bay water. Verbatim from src/city.src.html (groundVS, groundFS). */
import { HEAD, COMMON, rawMat } from "./common.js";

export const groundVS = HEAD + `
layout(location=0) in vec2 aXZ; uniform mat4 uVP; uniform mat4 uLightVP; out vec3 vPos; out vec4 vLight;
void main(){ vPos = vec3(aXZ.x, 0.0, aXZ.y); vLight = uLightVP * vec4(vPos + vec3(0.0, 0.5, 0.0), 1.0); gl_Position = uVP * vec4(vPos, 1.0); }`;
export const groundFS = HEAD + COMMON + `
in vec3 vPos; in vec4 vLight; uniform sampler2D uTex; uniform sampler2D uLU; uniform float uR; out vec4 o;
void main(){
  float rr = length(vPos.xz), ir = isleR(atan(vPos.z, vPos.x));
  if (rr > ir) discard;
  vec2 uv = (vPos.xz + uR) / (2.0 * uR);
  vec4 t = texture(uTex, clamp(uv, 0.0, 1.0));
  float blurW = textureLod(uTex, clamp(uv, 0.0, 1.0), 6.0).r;
  float edge = 1.0;
  float lip = smoothstep(ir - 26.0, ir - 3.0, rr);
  float w = mix(smoothstep(0.3, 0.8, blurW), t.r, edge), g = t.g * edge, r = t.b * edge;
  float major = smoothstep(0.72, 0.92, r);
  float minor = smoothstep(0.42, 0.55, r) * (1.0 - major);
  float path = smoothstep(0.12, 0.24, r) * (1.0 - major) * (1.0 - minor);
  float n1 = vnoise(vPos.xz * 0.004) * 0.5 + vnoise(vPos.xz * 0.02) * 0.5;
  float sh = shadowAt(vLight) * cloudShade(vPos.xz);
  vec3 V = normalize(uCam - vPos);
  vec3 L = uLightDir;
  vec3 amb = skyAmb() * 0.62 * (1.0 - uNight * 0.8);
  vec3 lightL = amb + uLightCol * max(L.y, 0.0) * sh;
  // land surfaces by land-use zone
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
  float fb = smoothstep(0.79, 0.84, vnoise(vPos.xz * 0.028 + 3.0)) * max(g, step(5.5, zone)) * step(0.5, 1.0 - path);
  vec3 flowerC = mix(hsv(fract(0.80 + 0.36 * vnoise(vPos.xz * 0.012 + 9.0)), 0.62, 0.9), vec3(0.95, 0.92, 0.85), step(0.72, n4));
  c = mix(c, mix(grass, flowerC, 0.55 + 0.45 * step(0.45, n3)), fb);
  c = mix(c, vec3(0.62, 0.58, 0.52), path);
  c = mix(c, vec3(0.34, 0.35, 0.36), minor);
  c = mix(c, vec3(0.27, 0.28, 0.30), major);
  c = mix(c, vec3(0.26, 0.40, 0.19), lip * (1.0 - smoothstep(0.35, 0.75, w)));
  vec3 lc = c * lightL;
  // road light at night
  vec3 nightRoad = vec3(1.0, 0.58, 0.22) * (major * 1.25 + minor * 0.55 + path * 0.12) + vec3(0.10, 0.055, 0.02) * smoothstep(0.1, 0.6, r);
  lc += nightRoad * uNight;
  // water
  vec2 q = vPos.xz * 0.11 + uWind * 0.03;
  float e = 0.5;
  float nx = (vnoise(q + vec2(e, 0) + uTime * 0.25) - vnoise(q - vec2(e, 0) + uTime * 0.25)) + 0.5 * (vnoise(q * 2.7 + vec2(e, 0) - uTime * 0.3) - vnoise(q * 2.7 - vec2(e, 0) - uTime * 0.3));
  float nz = (vnoise(q.yx + vec2(0, e) - uTime * 0.2) - vnoise(q.yx - vec2(0, e) - uTime * 0.2)) + 0.5 * (vnoise(q.yx * 2.3 + vec2(0, e) + uTime * 0.27) - vnoise(q.yx * 2.3 - vec2(0, e) + uTime * 0.27));
  float wfade = 1.0 - smoothstep(250.0, 1600.0, distance(vPos, uCam));
  vec3 wn = normalize(vec3(nx * 0.16 * wfade, 1.0, nz * 0.16 * wfade));
  vec3 R = reflect(-V, wn);
  float F = 0.02 + 0.98 * pow(1.0 - max(dot(wn, V), 0.0), 5.0);
  vec3 deep = mix(vec3(0.05, 0.15, 0.19), vec3(0.08, 0.20, 0.23), n1) * (amb + uLightCol * 0.3 * sh);
  float shallow = smoothstep(0.06, 0.5, 1.0 - textureLod(uTex, clamp(uv, 0.0, 1.0), 2.5).r);
  deep = mix(deep, vec3(0.10, 0.31, 0.31) * (amb + uLightCol * 0.4 * sh), shallow * (1.0 - uNight * 0.7));
  vec3 wc = mix(deep, skyColor(R) * 0.85, clamp(F * 1.1 + 0.05, 0.0, 1.0));
  wc += uLightCol * pow(max(dot(R, L), 0.0), 300.0) * 6.0 * sh * (1.0 - uNight);
  float shore = 1.0 - blurW;
  wc += vec3(1.0, 0.55, 0.22) * shore * shore * 0.35 * uNight * (0.7 + 0.6 * abs(nx) * wfade);
  wc = mix(wc, wc * 1.08 + 0.02, smoothstep(0.98, 0.6, w) * (1.0 - uNight));
  float sh2 = textureLod(uTex, clamp(uv, 0.0, 1.0), 2.0).r;
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
  vec3 col = mix(lc, wc, smoothstep(0.35, 0.75, w));
  o = vec4(fogIt(col, vPos), 1.0);
}`;

export const makeGroundMaterial = (tex, lu, R) => rawMat(groundVS, groundFS, { uTex: { value: tex }, uLU: { value: lu }, uR: { value: R } },
  { polygonOffset: true, polygonOffsetFactor: 4, polygonOffsetUnits: 8 });
