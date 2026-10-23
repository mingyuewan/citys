/* Modelled assets (phase 3): glb files from tools/blender/, in page coordinates (+Y up, metres, origin as CLAUDE.md).
   A model replaces its procedural counterpart by node name — ISLAND_body, LM_<k> — and is drawn by the same shaders:
   its meshes are turned into the page's vertex layout (world.js Geo: pos nrm col uv bid mat), the material id taken
   from the glTF material name ("M10_rock" → 10), the colour from COLOR_0 (baked strata and occlusion). */
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { VS } from "./world.js";

// resolves to the glTF scene, or null when the file is missing or broken (the page then keeps the procedural version)
export function loadModel(url) {
  // (compressed by gltfpack: EXT_meshopt_compression + KHR_mesh_quantization, see tools/blender/build_island.sh)
  return new Promise(res => new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).load(url, gltf => res(gltf.scene), undefined, e => { console.warn("model", url, e && e.message); res(null); }));
}

// all meshes under the node \`name\` → { V: Float32Array (VS floats per vertex), I: Uint32Array }, or null
export function toPageGeometry(root, name, bid = -1) {
  toPageGeometry.last = null;
  const node = root && root.getObjectByName(name);
  if (!node) return null;
  node.updateMatrixWorld(true);
  const uScale = (node.userData && node.userData.uScale) || 1;   // texcoord u stored as u / uScale (tools/blender/model_island.py)
  const meshes = []; let nv = 0, ni = 0;
  node.traverse(o => { if (o.isMesh) { meshes.push(o); nv += o.geometry.attributes.position.count; ni += o.geometry.index ? o.geometry.index.count : o.geometry.attributes.position.count; } });
  if (!nv) return null;
  const V = new Float32Array(nv * VS), I = new Uint32Array(ni), nm = new THREE.Matrix3();
  let v = 0, i = 0, uMax = 0;
  for (const o of meshes) {
    const g = o.geometry, pos = g.attributes.position, nrm = g.attributes.normal, col = g.attributes.color, uv = g.attributes.uv;
    const mat = +((o.material && o.material.name || "").match(/^M(\d+)_/) || [0, 10])[1];
    const e = o.matrixWorld.elements, q = nm.getNormalMatrix(o.matrixWorld).elements, base = v;
    for (let k = 0; k < pos.count; k++, v++) {
      const x = pos.getX(k), y = pos.getY(k), z = pos.getZ(k), o0 = v * VS;
      V[o0] = e[0] * x + e[4] * y + e[8] * z + e[12]; V[o0 + 1] = e[1] * x + e[5] * y + e[9] * z + e[13]; V[o0 + 2] = e[2] * x + e[6] * y + e[10] * z + e[14];
      let a = 0, b = 1, c = 0;
      if (nrm) { const nx = nrm.getX(k), ny = nrm.getY(k), nz = nrm.getZ(k); a = q[0] * nx + q[3] * ny + q[6] * nz; b = q[1] * nx + q[4] * ny + q[7] * nz; c = q[2] * nx + q[5] * ny + q[8] * nz; const l = Math.hypot(a, b, c) || 1; a /= l; b /= l; c /= l; }
      V[o0 + 3] = a; V[o0 + 4] = b; V[o0 + 5] = c;
      V[o0 + 6] = col ? col.getX(k) : 0.7; V[o0 + 7] = col ? col.getY(k) : 0.7; V[o0 + 8] = col ? col.getZ(k) : 0.7;
      const u = uv ? uv.getX(k) * uScale : 0; V[o0 + 9] = u; if (u > uMax) uMax = u;
      V[o0 + 10] = V[o0 + 1]; V[o0 + 11] = bid; V[o0 + 12] = mat;
    }
    if (g.index) for (let k = 0; k < g.index.count; k++) I[i++] = base + g.index.getX(k);
    else for (let k = 0; k < pos.count; k++) I[i++] = base + k;
  }
  toPageGeometry.last = { verts: nv, tris: ni / 3, uMax };   // (for checks: tools, console)
  return { V, I };
}

// append b to a (both {V, I} in the page layout)
export function concatGeometry(a, b) {
  const V = new Float32Array(a.V.length + b.V.length); V.set(a.V); V.set(b.V, a.V.length);
  const I = new Uint32Array(a.I.length + b.I.length), off = a.V.length / VS; I.set(a.I);
  for (let k = 0; k < b.I.length; k++) I[a.I.length + k] = b.I[k] + off;
  return { V, I };
}
