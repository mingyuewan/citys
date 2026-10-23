/* Additive / blended effects: waterfalls, light points (car lights, nav lights, drones), searchlight beams, cloud puffs.
   Verbatim from src/city.src.html (fallVS/FS, pointVS/FS, beamVS/FS, cloudVS/FS). */
import * as THREE from "three";
import { HEAD, COMMON, rawMat } from "./common.js";

export const fallVS = HEAD + `
layout(location=0) in vec3 aPos; layout(location=1) in vec2 aUv; layout(location=2) in float aEdge;
uniform mat4 uVP; out vec3 vPos; out vec2 vUv; out float vEdge;
void main(){ vPos = aPos; vUv = aUv; vEdge = aEdge; gl_Position = uVP * vec4(aPos, 1.0); }`;
export const fallFS = HEAD + COMMON + `
in vec3 vPos; in vec2 vUv; in float vEdge; out vec4 o;
void main(){
  float t = vUv.y;
  vec2 q = vec2(vUv.x * 0.07, t * 10.0 - uTime * 1.7);
  float s1 = vnoise(q), s2 = vnoise(q * vec2(2.7, 1.9) + 3.0), s3 = vnoise(vec2(vUv.x * 0.3, t * 30.0 - uTime * 4.0));
  float streak = s1 * 0.55 + s2 * 0.3 + s3 * 0.15;
  float a = (0.38 + 0.62 * smoothstep(0.3, 0.75, streak)) * (1.0 - smoothstep(0.5, 1.0, t)) * vEdge;
  a *= 0.15 + 0.85 * smoothstep(0.0, 0.01, t);
  vec3 base = mix(vec3(0.52, 0.70, 0.78), vec3(0.98), clamp(streak * 0.7 + t * 0.9, 0.0, 1.0));
  vec3 amb = skyAmb() * 0.85;
  vec3 c = base * (amb * 0.8 + uLightCol * 0.55) * (1.0 - uNight * 0.85);
  c += vec3(0.30, 0.62, 0.72) * uNight * (0.12 + 0.4 * streak) * (1.0 - t * 0.7);
  c = fogIt(c, vPos);
  o = vec4(c * a, a);
}`;
export const pointVS = HEAD + `
layout(location=0) in vec3 aPos; layout(location=1) in vec3 aCol; layout(location=2) in float aSize;
uniform mat4 uVP; uniform vec3 uCam; uniform float uPx; uniform float uRise;
out vec3 vCol;
void main(){ vCol = aCol; gl_Position = uVP * vec4(aPos, 1.0);
  float d = distance(aPos, uCam); gl_PointSize = clamp(aSize * uPx / d, 1.4, 48.0) * step(0.85, uRise) * step(0.01, aSize); }`;
export const pointFS = HEAD + `
in vec3 vCol; uniform float uAdd; out vec4 o;
void main(){ vec2 c = gl_PointCoord - 0.5; float r = length(c);
  float core = smoothstep(0.5, 0.0, r); float a = uAdd > 0.5 ? core * core : smoothstep(0.5, 0.3, r);
  o = vec4(vCol * a, uAdd > 0.5 ? a : a * 0.9); }`;
export const beamVS = HEAD + `
layout(location=0) in vec3 aPos; layout(location=1) in vec2 aT;
uniform mat4 uVP; out vec2 vT;
void main(){ vT = aT; gl_Position = uVP * vec4(aPos, 1.0); }`;
export const beamFS = HEAD + `
in vec2 vT; uniform float uNight; out vec4 o;
void main(){ float across = 1.0 - abs(vT.x); float a = pow(across, 1.5) * pow(1.0 - vT.y, 1.3) * 0.42 * uNight;
  o = vec4(vec3(0.85, 0.92, 1.0) * a, a); }`;
export const cloudVS = HEAD + `
layout(location=0) in vec2 aCorner; layout(location=1) in vec4 aC; layout(location=2) in vec2 aL;
uniform mat4 uVP; uniform vec3 uCamR; uniform vec3 uCamU; uniform vec3 uCam; uniform float uAspect;
out vec2 vUv; out float vLit; out float vA; out vec3 vPos;
void main(){
  vec3 p = aC.xyz + (uCamR * aCorner.x * uAspect + uCamU * aCorner.y) * aC.w;
  vUv = aCorner * 0.5 + 0.5; vLit = aL.x; vA = aL.y; vPos = p;
  gl_Position = uVP * vec4(p, 1.0);
}`;
export const cloudFS = HEAD + COMMON + `
in vec2 vUv; in float vLit; in float vA; in vec3 vPos; uniform sampler2D uPuff; uniform float uPuffA; out vec4 o;
void main(){
  vec4 tx = texture(uPuff, vUv);
  float t = mix(tx.r, tx.a, uPuffA);                                                  // GPT Image cloud: alpha = coverage
  float shade = mix(1.0, 0.5 + 0.55 * dot(tx.rgb, vec3(0.3, 0.5, 0.2)), uPuffA);     // and its own self-shading
  float d = distance(vPos, uCam);
  float a = t * vA * smoothstep(120.0, 750.0, d) * mix(1.0, 1.0 - 0.55 * uNight, uPuffA);   // textured puffs are denser: thin them at night so city light shows through
  vec3 sunC = mix(vec3(1.0, 0.99, 0.97), vec3(1.0, 0.72, 0.50), uGold);
  vec3 dayC = mix(vec3(0.60, 0.64, 0.70), sunC, vLit) * (0.85 + 0.25 * vUv.y);
  vec3 nightC = mix(vec3(0.16, 0.10, 0.07), vec3(0.06, 0.07, 0.10), vLit);
  vec3 c = mix(dayC, nightC, uNight) * shade;
  c = fogIt(c, vPos);
  o = vec4(c * a, a);
}`;

const blend = (src, dst) => ({ transparent: true, depthWrite: false, blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: src, blendDst: dst });
const PREMUL = blend(THREE.OneFactor, THREE.OneMinusSrcAlphaFactor), ADD = blend(THREE.OneFactor, THREE.OneFactor);
export const makeFallMaterial = () => rawMat(fallVS, fallFS, {}, PREMUL);
// uAdd 1: additive glow (night lights); uPx: pixels per metre at distance 1 (set per frame)
export const makePointMaterial = () => rawMat(pointVS, pointFS, { uPx: { value: 1 }, uAdd: { value: 1 } }, ADD);
export const makeBeamMaterial = () => rawMat(beamVS, beamFS, {}, ADD);
export const makeCloudMaterial = tex => rawMat(cloudVS, cloudFS, { uCamR: { value: new THREE.Vector3() }, uCamU: { value: new THREE.Vector3() },
  uPuff: { value: tex }, uPuffA: { value: 0 }, uAspect: { value: 1 } }, PREMUL);
