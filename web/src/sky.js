/* Time of day → lighting, the sky dome and the sea of clouds. Puff clouds come later (phase 1, clouds module). */
import * as THREE from "three";
import { clamp, smooth, norm3 } from "./world.js";
import { makeSkyMaterial, makeSeaMaterial } from "./materials/sky.js";

// time of day → lighting
export function sky(tod) {
  const t = ((tod % 24) + 24) % 24;
  const a = (t - 6) / 12 * Math.PI;
  const sun = norm3([Math.cos(a), Math.sin(a) * 1.15, 0.38 + Math.sin(a) * 0.15]);
  const dayF = smooth(-0.07, 0.10, sun[1]);
  const night = 1 - dayF;
  const gold = dayF * (1 - smooth(0.04, 0.42, sun[1]));
  const moon = norm3([-0.35, 0.62, -0.45]);
  const sunCol = [1.0 * 1.15, (0.95 - 0.33 * gold) * 1.15, (0.88 - 0.5 * gold) * 1.15].map(v => v * clamp(sun[1] * 4 + 0.15, 0, 1));
  const moonCol = [0.030, 0.038, 0.060];
  const lightDir = dayF > 0.15 ? sun : moon;
  const lightCol = dayF > 0.15 ? sunCol : moonCol;
  // lights-on schedule: busiest in the evening, fewer after midnight
  const lit = t >= 17 ? 0.55 + 0.35 * smooth(17, 20, t) : t < 5 ? 0.5 - t * 0.04 : 0.35;
  return { sun, night, gold, lightDir, lightCol, moon, lit, dayF };
}
export function fmtTod(t) { t = ((t % 24) + 24) % 24; const h = Math.floor(t), m = Math.floor((t - h) * 60); return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`; }

// full-screen triangle (the vertex shader uses gl_VertexID; the attribute only sets the draw count)
export function makeSky() {
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(9), 3));
  const m = new THREE.Mesh(g, makeSkyMaterial());
  m.frustumCulled = false; m.renderOrder = -10;
  return m;
}
export const SEA_Y = -1900;
export function makeSea() {
  const G = 90000, g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(new Float32Array([-G, -G, G, -G, G, G, -G, -G, G, G, -G, G]), 2));
  g.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, SEA_Y, 0), G * Math.SQRT2);   // xz-only positions: three.js cannot compute it
  const m = new THREE.Mesh(g, makeSeaMaterial(SEA_Y));
  m.frustumCulled = false; m.renderOrder = -5;
  return m;
}
