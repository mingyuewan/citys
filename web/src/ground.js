/* Ground plane: class map (water mask + road strokes) and land-use texture, drawn by materials/ground.js. */
import * as THREE from "three";
import { makeGroundMaterial } from "./materials/ground.js";

// ground texture (class map): r = water, g = green, b = road class
export function buildGroundTexture(osm, R, S, maskImg) {
  const cv = document.createElement("canvas"); cv.width = cv.height = S;
  const g = cv.getContext("2d");
  const k = S / (2 * R);
  const X = p => (p[0] + R) * k, Z = p => (p[1] + R) * k;
  g.fillStyle = "#000"; g.fillRect(0, 0, S, S);
  g.imageSmoothingEnabled = true; g.imageSmoothingQuality = "high";
  g.drawImage(maskImg, 0, 0, S, S);
  g.globalCompositeOperation = "lighten";
  const W = { motorway: 24, trunk: 22, primary: 18, secondary: 14, tertiary: 10, motorway_link: 8, trunk_link: 8, primary_link: 7,
    secondary_link: 7, tertiary_link: 6, residential: 7, unclassified: 7, living_street: 6, service: 4, pedestrian: 4, footway: 2, cycleway: 2.2, path: 1.8, steps: 1.6, track: 2 };
  const order = ["track", "steps", "path", "footway", "cycleway", "pedestrian", "service", "living_street", "residential", "unclassified", "tertiary_link", "tertiary",
    "secondary_link", "primary_link", "trunk_link", "motorway_link", "secondary", "primary", "trunk", "motorway"];
  g.lineJoin = "round"; g.lineCap = "round";
  for (const hw of order) {
    const lines = osm.roads.filter(r => r.hw === hw && !r._ribbon);
    if (!lines.length) continue;
    const isPath = /^(path|footway|cycleway|steps|track)$/.test(hw), isMajor = /^(motorway|trunk|primary|secondary)/.test(hw);
    g.strokeStyle = isMajor ? "rgb(0,0,255)" : isPath ? "rgb(0,0,64)" : "rgb(0,0,140)";
    g.lineWidth = Math.max(isPath ? 0.9 : 1.2, W[hw] * k);
    g.beginPath();
    for (const r of lines) r.pts.forEach((p, i) => i ? g.lineTo(X(p), Z(p)) : g.moveTo(X(p), Z(p)));
    g.stroke();
  }
  g.globalCompositeOperation = "source-over";
  return cv;
}

// textures are uploaded as in the old engine: no y-flip, no colour-space conversion, trilinear mipmaps
function groundTex(src, aniso) {
  const t = src instanceof HTMLCanvasElement ? new THREE.CanvasTexture(src) : new THREE.Texture(src);
  t.flipY = false; t.anisotropy = aniso; t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping;
  t.minFilter = THREE.LinearMipmapLinearFilter; t.magFilter = THREE.LinearFilter; t.generateMipmaps = true;
  t.needsUpdate = true;
  return t;
}
export function makeGround(osm, D, maskImg, luImg, renderer) {
  const TS = Math.min(renderer.capabilities.maxTextureSize, 4096);
  const tex = groundTex(buildGroundTexture(osm, D.R, TS, maskImg), Math.min(16, renderer.capabilities.getMaxAnisotropy()));
  const lu = groundTex(luImg, 1);
  // dense near the city so per-vertex shadow coords stay accurate
  const pts = []; const n = 40, R = D.R + 220;
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
    const x0 = -R + 2 * R * i / n, x1 = -R + 2 * R * (i + 1) / n, z0 = -R + 2 * R * j / n, z1 = -R + 2 * R * (j + 1) / n;
    pts.push(x0, z0, x1, z0, x1, z1, x0, z0, x1, z1, x0, z1);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(pts), 2));
  g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), R * Math.SQRT2);   // xz-only positions: three.js cannot compute it
  const m = new THREE.Mesh(g, makeGroundMaterial(tex, lu, D.R));
  m.frustumCulled = false; m.renderOrder = -4;
  return m;
}
