/* Sky dome (full-screen triangle) and the sea of clouds under the island. Verbatim from src/city.src.html. */
import * as THREE from "three";
import { HEAD, COMMON, rawMat } from "./common.js";

export const fsTriVS = HEAD + `
const vec2 P[3] = vec2[3](vec2(-1,-1), vec2(3,-1), vec2(-1,3));
out vec2 vNdc; out vec2 vUv;
void main(){ vNdc = P[gl_VertexID]; vUv = vNdc * 0.5 + 0.5; gl_Position = vec4(P[gl_VertexID], 0.9999, 1.0); }`;
export const skyFS = HEAD + COMMON + `
in vec2 vNdc; uniform mat4 uInvVP; uniform vec3 uMoonDir; out vec4 o;
void main(){
  vec4 a = uInvVP * vec4(vNdc, -1.0, 1.0), b = uInvVP * vec4(vNdc, 1.0, 1.0);
  vec3 d = normalize(b.xyz / b.w - a.xyz / a.w);
  vec3 c = skyColor(d);
  float sd = dot(d, uSunDir);
  c += vec3(1.0, 0.9, 0.72) * smoothstep(0.99955, 0.99975, sd) * 8.0 * (1.0 - uNight);
  vec2 sp = floor(d.xz / max(d.y, 0.05) * 160.0);
  float st = step(0.9972, h21(sp)) * smoothstep(0.1, 0.45, d.y);
  c += vec3(0.9) * st * uNight * (0.6 + 0.4 * sin(uTime * 3.0 + sp.x));
  float md = dot(d, uMoonDir);
  c += vec3(0.95, 0.95, 0.88) * smoothstep(0.99935, 0.9996, md) * 2.2 * uNight;
  c += vec3(0.25, 0.27, 0.32) * pow(max(md, 0.0), 120.0) * uNight;
  o = vec4(c, 1.0);
}`;
export const seaVS = HEAD + `
layout(location=0) in vec2 aXZ; uniform mat4 uVP; uniform float uY; out vec3 vPos;
void main(){ vPos = vec3(aXZ.x, uY, aXZ.y); gl_Position = uVP * vec4(vPos, 1.0); }`;
export const seaFS = HEAD + COMMON + `
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
  vec3 col = fogIt(mix(day, night, uNight), vPos);
  vec3 dv = vPos - uCam; float dd = length(dv.xz);
  col = mix(col, skyColor(vec3(dv.x, 0.015 * dd, dv.z)), smoothstep(14000.0, 55000.0, dd));
  o = vec4(col, 1.0);
}`;

export const makeSkyMaterial = () => rawMat(fsTriVS, skyFS, { uInvVP: { value: new THREE.Matrix4() }, uMoonDir: { value: new THREE.Vector3() } }, { depthWrite: false });
export const makeSeaMaterial = y => rawMat(seaVS, seaFS, { uY: { value: y } });
