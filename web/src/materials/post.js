/* Bloom (bright pass → 2× down chain → tent up chain) and the ACES composite. Verbatim from src/city.src.html. */
import { rawMat } from "./common.js";
const HEAD = `precision highp float; precision highp int;
`;

const fsTriVS = HEAD + `
const vec2 P[3] = vec2[3](vec2(-1,-1), vec2(3,-1), vec2(-1,3));
out vec2 vNdc; out vec2 vUv;
void main(){ vNdc = P[gl_VertexID]; vUv = vNdc * 0.5 + 0.5; gl_Position = vec4(P[gl_VertexID], 0.9999, 1.0); }`;
export const brightFS = HEAD + `
in vec2 vUv; uniform sampler2D uTex; uniform float uThr; out vec4 o;
void main(){ vec3 c = texture(uTex, vUv).rgb; float l = max(c.r, max(c.g, c.b)); float k = max(l - uThr, 0.0); k = k * k / (k + 0.25); o = vec4(c * (k / max(l, 1e-4)), 1.0); }`;
export const downFS = HEAD + `
in vec2 vUv; uniform sampler2D uTex; uniform vec2 uTexel; out vec4 o;
void main(){ vec3 c = texture(uTex, vUv + uTexel * vec2(-1, -1)).rgb + texture(uTex, vUv + uTexel * vec2(1, -1)).rgb + texture(uTex, vUv + uTexel * vec2(-1, 1)).rgb + texture(uTex, vUv + uTexel * vec2(1, 1)).rgb;
  o = vec4(c * 0.25, 1.0); }`;
export const upFS = HEAD + `
in vec2 vUv; uniform sampler2D uTex; uniform vec2 uTexel; out vec4 o;
void main(){ vec3 c = vec3(0.0);
  c += texture(uTex, vUv + uTexel * vec2(-1, -1)).rgb + texture(uTex, vUv + uTexel * vec2(1, -1)).rgb + texture(uTex, vUv + uTexel * vec2(-1, 1)).rgb + texture(uTex, vUv + uTexel * vec2(1, 1)).rgb;
  c += 2.0 * (texture(uTex, vUv + uTexel * vec2(-1, 0)).rgb + texture(uTex, vUv + uTexel * vec2(1, 0)).rgb + texture(uTex, vUv + uTexel * vec2(0, -1)).rgb + texture(uTex, vUv + uTexel * vec2(0, 1)).rgb);
  c += 4.0 * texture(uTex, vUv).rgb; o = vec4(c / 16.0, 1.0); }`;
export const compFS = HEAD + `
in vec2 vUv; uniform sampler2D uScene; uniform sampler2D uBloom; uniform float uBloomK; uniform float uExpo; uniform float uNight; out vec4 o;
vec3 aces(vec3 x){ return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0); }
void main(){
  vec3 c = texture(uScene, vUv).rgb + texture(uBloom, vUv).rgb * uBloomK;
  c = aces(c * uExpo);
  float l = dot(c, vec3(0.299, 0.587, 0.114)); c = mix(vec3(l), c, 1.12); c = pow(c, vec3(1.06));
  vec2 q = vUv - 0.5; c *= 1.0 - dot(q, q) * mix(0.35, 0.6, uNight);
  c += (fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453) - 0.5) / 255.0;
  o = vec4(c, 1.0);
}`;

const fs = (f, u, o) => rawMat(fsTriVS, f, u, { depthTest: false, depthWrite: false, ...o });
export const makeBright = () => fs(brightFS, { uTex: { value: null }, uThr: { value: 1 } });
export const makeDown = () => fs(downFS, { uTex: { value: null }, uTexel: { value: [1, 1] } });
export const makeUp = () => fs(upFS, { uTex: { value: null }, uTexel: { value: [1, 1] } });
export const makeComp = () => fs(compFS, { uScene: { value: null }, uBloom: { value: null }, uBloomK: { value: 0 }, uExpo: { value: 1 }, uNight: { value: 0 } });
