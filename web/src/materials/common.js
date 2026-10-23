/* Shared GLSL (sky colour, fog, isleR, noise, shadow lookup) and the uniforms every scene material shares.
   Shader text is copied verbatim from src/city.src.html; three.js prepends "#version 300 es" (glslVersion GLSL3). */
import * as THREE from "three";
import { ISLE_GLSL } from "../world.js";

const HEAD = `precision highp float; precision highp int; precision highp sampler2DShadow;
`;

const COMMON = `
uniform vec3 uSunDir; uniform vec3 uLightDir; uniform vec3 uLightCol; uniform float uNight; uniform float uGold;
uniform vec3 uCam; uniform float uFogDen; uniform float uTime; uniform vec2 uWind; uniform vec3 uIsle;
${ISLE_GLSL}
float h21(vec2 p){ p = fract(p*vec2(123.34, 456.21)); p += dot(p, p+45.32); return fract(p.x*p.y); }
float h31(vec3 p){ return h21(p.xy + p.z*17.13); }
float vnoise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
  return mix(mix(h21(i), h21(i+vec2(1,0)), f.x), mix(h21(i+vec2(0,1)), h21(i+vec2(1,1)), f.x), f.y); }
vec3 skyColor(vec3 d){
  d = normalize(d); float h = d.y;
  float sa = max(dot(d, uSunDir), 0.0);
  vec3 hor = mix(vec3(0.72, 0.81, 0.90), vec3(1.0, 0.62, 0.40), uGold * (0.45 + 0.55 * pow(sa, 2.0)));
  vec3 zen = mix(vec3(0.20, 0.40, 0.76), vec3(0.28, 0.32, 0.58), uGold * 0.7);
  vec3 day = mix(hor, zen, pow(clamp(h, 0.0, 1.0), 0.5));
  day += vec3(1.0, 0.78, 0.52) * pow(sa, 10.0) * (0.22 + 0.7 * uGold);
  if (h < 0.0) day = mix(hor * 0.9, vec3(0.42, 0.44, 0.43), clamp(-h * 4.0, 0.0, 1.0));
  vec3 nh = vec3(0.075, 0.062, 0.085), nz = vec3(0.008, 0.013, 0.04);
  vec3 night = mix(nh, nz, pow(clamp(h, 0.0, 1.0), 0.4));
  night += vec3(0.30, 0.15, 0.07) * exp(-abs(h) * 12.0) * 0.42;
  if (h < 0.0) night = mix(nh + vec3(0.06, 0.03, 0.01), vec3(0.03, 0.03, 0.04), clamp(-h * 4.0, 0.0, 1.0));
  return mix(day, night, uNight);
}
vec3 skyAmb(){ vec3 s = skyColor(vec3(0.0, 1.0, 0.0)); float l = dot(s, vec3(0.3, 0.5, 0.2)); return mix(vec3(l), s, 0.45) * 1.05; }
vec3 fogIt(vec3 c, vec3 p){
  vec3 v = p - uCam; float d = length(v);
  float f = 1.0 - exp(-pow(d * uFogDen, 1.5));
  vec3 fc = skyColor(vec3(v.x, abs(v.y) * 0.08 + 0.02 * d, v.z));
  return mix(c, fc, clamp(f, 0.0, 1.0));
}
float cloudShade(vec2 xz){
  vec2 p = (xz - uWind) * 0.00042;
  float n = vnoise(p) * 0.6 + vnoise(p * 2.3 + 7.1) * 0.4;
  return 1.0 - 0.38 * smoothstep(0.55, 0.78, n) * (1.0 - uNight);
}
uniform sampler2DShadow uShadow; uniform float uShadowOn; uniform vec2 uShadowTexel;
float shadowAt(vec4 lp){
  if (uShadowOn < 0.5) return 1.0;
  vec3 c = lp.xyz / lp.w * 0.5 + 0.5;
  if (c.x < 0.001 || c.x > 0.999 || c.y < 0.001 || c.y > 0.999 || c.z > 0.999) return 1.0;
  // 4 taps on top of the hardware 2×2 compare filter (LINEAR) ≈ the old 3×3 footprint at less than half the fetches
  float z = c.z - 0.00025; vec2 o = uShadowTexel * 0.6;
  return 0.25 * (texture(uShadow, vec3(c.xy + vec2(-o.x, -o.y), z)) + texture(uShadow, vec3(c.xy + vec2(o.x, -o.y), z))
               + texture(uShadow, vec3(c.xy + vec2(-o.x, o.y), z)) + texture(uShadow, vec3(c.xy + vec2(o.x, o.y), z)));
}
vec3 hsv(float h, float s, float v){ vec3 k = clamp(abs(mod(h * 6.0 + vec3(0, 4, 2), 6.0) - 3.0) - 1.0, 0.0, 1.0); return v * mix(vec3(1), k, s); }
`;
export { HEAD, COMMON };

// One uniform object per name, shared by reference across materials: set once per frame in main.js.
const white = new THREE.DataTexture(new Uint8Array([255, 255, 255, 255]), 1, 1); white.needsUpdate = true;
export const U = {
  uVP: { value: new THREE.Matrix4() }, uLightVP: { value: new THREE.Matrix4() },
  uSunDir: { value: new THREE.Vector3() }, uLightDir: { value: new THREE.Vector3() }, uLightCol: { value: new THREE.Vector3() },
  uNight: { value: 0 }, uGold: { value: 0 }, uCam: { value: new THREE.Vector3() }, uFogDen: { value: 1e-4 }, uTime: { value: 0 },
  uWind: { value: new THREE.Vector2() }, uIsle: { value: new THREE.Vector3() },
  uShadow: { value: null }, uShadowOn: { value: 0 }, uShadowTexel: { value: new THREE.Vector2(1, 1) }, uNOff: { value: 0 },
  uRise: { value: 0 }, uMaxR: { value: 1 },
  uRock: { value: white }, uFacade: { value: white }, uTexOn: { value: new THREE.Vector2() },
};
export const WHITE_TEX = white;

// The old engine bound attributes by location; three.js binds by name. Rename the declarations and keep the
// shader bodies untouched with a #define per attribute.
const ATTR = { aPos: "position", aNrm: "normal", aCol: "color", aUv: "uv", aBid: "bid", aMat: "mat", aXZ: "position" };
function glsl3(src) {
  return src.replace(/layout\(location=\d+\) in (\w+) (\w+);\s*/g, (m, type, name) => {
    const to = ATTR[name]; if (!to) throw new Error("unmapped attribute " + name);
    return `in ${type} ${to};\n#define ${name} ${to}\n`;
  });
}
// a RawShaderMaterial over the old GLSL; `uniforms` adds per-material entries on top of the shared U
export function rawMat(vs, fs, uniforms = {}, opts = {}) {
  return new THREE.RawShaderMaterial({
    glslVersion: THREE.GLSL3, vertexShader: glsl3(vs), fragmentShader: glsl3(fs),
    uniforms: { ...U, ...uniforms }, side: THREE.DoubleSide, ...opts,
  });
}
