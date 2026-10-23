/* Bloom (bright pass → 2× down chain → tent up chain; verbatim from src/city.src.html) and the style A composite:
   tilt-shift depth of field from the depth buffer, ACES, a warm diorama grade. */
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
uniform sampler2D uDepth; uniform sampler2D uD0; uniform sampler2D uD1; uniform sampler2D uD2; uniform vec2 uTexD1; uniform vec2 uTexD2;
uniform float uNear; uniform float uFar; uniform float uFocus;
uniform vec4 uTilt;      // x: strength, y–z: |log(depth / focus)| from sharp to fully blurred, w: screen band (|y − 0.5| where blur starts)
uniform vec3 uWarm; uniform vec3 uLift; uniform float uSat; uniform float uVig;
uniform vec2 uTexel; uniform vec3 uCav;   // cavity: x ridge highlight, y valley shade, z sample radius (px)
vec3 aces(vec3 x){ return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0); }
float linZ(vec2 uv){ float z = texture(uDepth, uv).r * 2.0 - 1.0; return 2.0 * uNear * uFar / (uFar + uNear - z * (uFar - uNear)); }
vec3 tent(sampler2D t, vec2 uv, vec2 e){
  vec3 c = texture(t, uv + e * vec2(-1, -1)).rgb + texture(t, uv + e * vec2(1, -1)).rgb + texture(t, uv + e * vec2(-1, 1)).rgb + texture(t, uv + e * vec2(1, 1)).rgb;
  c += 2.0 * (texture(t, uv + e * vec2(-1, 0)).rgb + texture(t, uv + e * vec2(1, 0)).rgb + texture(t, uv + e * vec2(0, -1)).rgb + texture(t, uv + e * vec2(0, 1)).rgb);
  return (c + 4.0 * texture(t, uv).rgb) / 16.0;
}
void main(){
  // tilt-shift: blur grows with the distance (in log depth) from the focus, and toward the top and bottom of the frame
  float z = texture(uDepth, vUv).r * 2.0 - 1.0;
  float vz = 2.0 * uNear * uFar / (uFar + uNear - z * (uFar - uNear));
  float coc = smoothstep(uTilt.y, uTilt.z, abs(log(vz / uFocus)));
  coc = clamp(max(coc, 0.8 * smoothstep(uTilt.w, 0.5, abs(vUv.y - 0.5))) * uTilt.x, 0.0, 1.0);
  vec3 s0 = texture(uScene, vUv).rgb, s1 = texture(uD0, vUv).rgb;
  vec3 c = coc < 0.34 ? mix(s0, s1, coc / 0.34) : coc < 0.67 ? mix(s1, tent(uD1, vUv, uTexD1), (coc - 0.34) / 0.33) : mix(tent(uD1, vUv, uTexD1), tent(uD2, vUv, uTexD2), (coc - 0.67) / 0.33);
  // style A cavity: convex edges (nearer than their surroundings) catch a thin warm highlight, creases and building
  // feet (farther than their surroundings) darken a little — the bevelled, hand-made look of a model
  if (uCav.x + uCav.y > 0.0 && vz < uFar * 0.5) {
    vec2 e = uTexel * uCav.z;
    float nb = (linZ(vUv + vec2(e.x, 0.0)) + linZ(vUv - vec2(e.x, 0.0)) + linZ(vUv + vec2(0.0, e.y)) + linZ(vUv - vec2(0.0, e.y))) * 0.25;
    float rel = (nb - vz) / vz, sharp = 1.0 - coc;
    float ridge = smoothstep(0.003, 0.04, rel) * (1.0 - smoothstep(0.5, 3.0, rel)), valley = smoothstep(0.0015, 0.02, -rel);
    c = c * (1.0 - uCav.y * valley * sharp) + vec3(1.0, 0.86, 0.66) * uCav.x * ridge * sharp * (1.0 - uNight * 0.8) * (0.4 + 0.6 * dot(c, vec3(0.33)));
  }
  c += texture(uBloom, vUv).rgb * uBloomK;
  c = aces(c * uExpo);
  // diorama grade: warm white balance, richer colour, shadows lifted toward lavender, soft vignette
  c *= uWarm;
  float l = dot(c, vec3(0.299, 0.587, 0.114)); c = mix(vec3(l), c, uSat);
  c = c + uLift * (1.0 - c) * (1.0 - smoothstep(0.0, 0.6, l));
  vec2 q = vUv - 0.5; c *= 1.0 - dot(q, q) * mix(uVig, 0.6, uNight);
  c += (fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453) - 0.5) / 255.0;
  o = vec4(clamp(c, 0.0, 1.0), 1.0);
}`;

const fs = (f, u, o) => rawMat(fsTriVS, f, u, { depthTest: false, depthWrite: false, ...o });
export const makeBright = () => fs(brightFS, { uTex: { value: null }, uThr: { value: 1 } });
export const makeDown = () => fs(downFS, { uTex: { value: null }, uTexel: { value: [1, 1] } });
export const makeUp = () => fs(upFS, { uTex: { value: null }, uTexel: { value: [1, 1] } });
export const makeComp = () => fs(compFS, { uScene: { value: null }, uBloom: { value: null }, uBloomK: { value: 0 }, uExpo: { value: 1 }, uNight: { value: 0 },
  uDepth: { value: null }, uD0: { value: null }, uD1: { value: null }, uD2: { value: null }, uTexD1: { value: [1, 1] }, uTexD2: { value: [1, 1] },
  uNear: { value: 1 }, uFar: { value: 1e5 }, uFocus: { value: 1000 }, uTilt: { value: [1, 0.12, 0.95, 0.3] },
  uWarm: { value: [1, 1, 1] }, uLift: { value: [0, 0, 0] }, uSat: { value: 1.12 }, uVig: { value: 0.35 }, uTexel: { value: [1, 1] }, uCav: { value: [0, 0, 1.5] } });
