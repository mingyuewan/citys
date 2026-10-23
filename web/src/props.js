/* Trees (street, park, palms, median shrubs, islet and roof-garden trees), sports grounds / pools / car parks,
   parked cars. Tree templates and instance placement are verbatim from src/city.src.html ("tree meshes");
   the far tree template and the cell drawing (instancing.js) are new. */
import * as THREE from "three";
import { hash1, inIsle, norm3, meshGeometry, orient } from "./world.js";
import { InstCells, templateAttrs, TREE_LAYOUT, TREE_INST, PROP_LAYOUT, PROP_INST, LATE_SHADOW } from "./instancing.js";
import { makeTreeMaterial, makeTreeShadowMaterial, makeInstMaterial, makeInstShadowMaterial } from "./materials/street.js";
import { TPL } from "./templates.js";
import { buildFeatures, SHRUBS, PARKED } from "./roads.js";

function treeTemplate(palm) {
  const v = [], idx = [];
  const add = (x, y, z, nx, ny, nz, part) => { v.push(x, y, z, nx, ny, nz, part); return v.length / 7 - 1; };
  // trunk: hexagonal
  const th = palm ? 9 : 3.2, tr = palm ? 0.32 : 0.35;
  for (let i = 0; i < 6; i++) {
    const a0 = i / 6 * Math.PI * 2, a1 = (i + 1) / 6 * Math.PI * 2;
    const p = [add(Math.cos(a0) * tr, 0, Math.sin(a0) * tr, Math.cos(a0), 0, Math.sin(a0), 0), add(Math.cos(a1) * tr, 0, Math.sin(a1) * tr, Math.cos(a1), 0, Math.sin(a1), 0),
      add(Math.cos(a1) * tr * 0.7 + (palm ? 0.6 : 0), th, Math.sin(a1) * tr * 0.7, Math.cos(a1), 0, Math.sin(a1), 0), add(Math.cos(a0) * tr * 0.7 + (palm ? 0.6 : 0), th, Math.sin(a0) * tr * 0.7, Math.cos(a0), 0, Math.sin(a0), 0)];
    idx.push(p[0], p[1], p[2], p[0], p[2], p[3]);
  }
  if (!palm) {
    // crown: icosahedron
    const t = (1 + Math.sqrt(5)) / 2;
    const ico = [[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t], [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]].map(norm3);
    const F = [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]];
    const rad = 2.9, cy = 5.4;
    for (const f of F) {
      const a = f.map(k => ico[k]);
      const n = norm3([a[0][0] + a[1][0] + a[2][0], a[0][1] + a[1][1] + a[2][1], a[0][2] + a[1][2] + a[2][2]]);
      for (const p of a) idx.push(add(p[0] * rad, cy + p[1] * rad * 0.85, p[2] * rad, (p[0] + n[0]) / 2, (p[1] + n[1]) / 2, (p[2] + n[2]) / 2, 1));
    }
  } else {
    const top = [0.6, th, 0];
    for (let i = 0; i < 7; i++) {
      const a = i / 7 * Math.PI * 2, ca = Math.cos(a), sa = Math.sin(a);
      const tip = [top[0] + ca * 4.2, th - 1.8, sa * 4.2], mid = [top[0] + ca * 2.2, th + 0.7, sa * 2.2];
      const side = [-sa * 0.9, 0, ca * 0.9];
      const p0 = add(top[0], top[1], top[2], 0, 1, 0, 1);
      const p1 = add(mid[0] + side[0], mid[1], mid[2] + side[2], ca * 0.3, 0.95, sa * 0.3, 1);
      const p2 = add(tip[0], tip[1], tip[2], ca * 0.5, 0.8, sa * 0.5, 1);
      const p3 = add(mid[0] - side[0], mid[1], mid[2] - side[2], ca * 0.3, 0.95, sa * 0.3, 1);
      idx.push(p0, p1, p2, p0, p2, p3);
    }
  }
  return { v: new Float32Array(v), i: new Uint16Array(idx) };
}
function treeInstances(flat, base, jitter, ys) {
  const out = [];
  for (let i = 0; i < flat.length / 2; i++) {
    const x = flat[2 * i], z = flat[2 * i + 1], y = ys ? ys[i] : 0;
    if (!ys && !inIsle(x, z, 6)) continue;
    const h = hash1(x * 0.37 + z * 1.13);
    out.push(x, z, base + h * jitter, hash1(x * 1.7 - z * 0.3), y);
  }
  return new Float32Array(out);
}
// far trees (past LOD_TREE): the crown as an octahedron, no trunk; palms keep only their fronds
function treeTemplateFar(palm) {
  const v = [], idx = [];
  const add = (x, y, z, nx, ny, nz, part) => { v.push(x, y, z, nx, ny, nz, part); return v.length / 7 - 1; };
  if (!palm) {
    const rad = 2.9, cy = 5.4, P = [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]];
    for (const [a, b, c] of [[0, 2, 4], [4, 2, 1], [1, 2, 5], [5, 2, 0], [4, 3, 0], [1, 3, 4], [5, 3, 1], [0, 3, 5]]) {
      const f = [P[a], P[b], P[c]], n = norm3([f[0][0] + f[1][0] + f[2][0], f[0][1] + f[1][1] + f[2][1], f[0][2] + f[1][2] + f[2][2]]);
      for (const p of f) idx.push(add(p[0] * rad, cy + p[1] * rad * 0.85, p[2] * rad, (p[0] + n[0]) / 2, (p[1] + n[1]) / 2, (p[2] + n[2]) / 2, 1));
    }
  } else {
    const th = 9, top = [0.6, th, 0];
    for (let i = 0; i < 7; i++) {
      const a = i / 7 * Math.PI * 2, ca = Math.cos(a), sa = Math.sin(a);
      const p0 = add(top[0], top[1], top[2], 0, 1, 0, 1), p1 = add(top[0] + ca * 2.2 - sa * 0.9, th + 0.7, sa * 2.2 + ca * 0.9, ca * 0.3, 0.95, sa * 0.3, 1);
      const p2 = add(top[0] + ca * 4.2, th - 1.8, sa * 4.2, ca * 0.5, 0.8, sa * 0.5, 1);
      idx.push(p0, p1, p2);
    }
  }
  return { v: new Float32Array(v), i: new Uint16Array(idx) };
}

const LOD_TREE = 1100, TREE_POS = (b, k) => [b[k * 5], b[k * 5 + 4], b[k * 5 + 1]], PROP_POS = (b, k) => [b[k * 8], b[k * 8 + 1], b[k * 8 + 2]];
export const PROPS = { trees: [], parked: null, features: null };
export function makeProps(D, extraTrees, meshMat, scene, shadowScene) {
  const round = { near: templateAttrs(treeTemplate(false), TREE_LAYOUT), far: templateAttrs(treeTemplateFar(false), TREE_LAYOUT) };
  const palm = { near: templateAttrs(treeTemplate(true), TREE_LAYOUT), far: templateAttrs(treeTemplateFar(true), TREE_LAYOUT) };
  const tm = makeTreeMaterial(), tsm = makeTreeShadowMaterial();
  const sets = [[round, treeInstances(SHRUBS, 0.34, 0.12)], [round, treeInstances(D.trees, 0.8, 0.7)], [palm, treeInstances(D.palms, 0.85, 0.4)],
    [round, treeInstances(extraTrees.x, 1.0, 0.9, extraTrees.y)]];
  PROPS.trees = sets.map(([T, inst]) => new InstCells({ T: T.near, Tfar: T.far, inst, layout: TREE_INST, pos: TREE_POS, pad: 14, material: tm, shadowMaterial: tsm, lodDist: LOD_TREE, order: 2 }).add(scene, shadowScene));
  // sports grounds, courts, pools, car parks: flat quads drawn by the building shader (materials 12–19)
  const ft = buildFeatures(D); orient(ft.V, ft.I);
  const fm = new THREE.Mesh(meshGeometry(ft.V, ft.I), meshMat); fm.frustumCulled = false; fm.renderOrder = 1;
  scene.add(fm); const fs = new THREE.Mesh(fm.geometry, shadowScene.userData.shadowMat); fs.frustumCulled = false; shadowScene.add(fs);
  PROPS.features = { mesh: fm, n: ft.n };
  PROPS.parked = new InstCells({ T: templateAttrs(TPL.car, PROP_LAYOUT), inst: new Float32Array(PARKED), layout: PROP_INST, pos: PROP_POS, pad: 6,
    material: makeInstMaterial(1600), shadowMaterial: makeInstShadowMaterial(), shadowLayer: LATE_SHADOW, far: 1600, order: 3 }).add(scene, shadowScene);
  return PROPS;
}
export function updateProps(eye) { for (const t of PROPS.trees) t.update(eye); PROPS.parked.update(eye); }
