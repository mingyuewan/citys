/* Instanced drawing for trees and street props.
   The old engine sent every instance to the GPU and dropped the far ones in the vertex shader (and drew all of
   them again into the shadow map). Here static instances are split into square cells, each a mesh with its own
   bounding sphere, so three.js frustum-culls them (main and shadow camera alike) and cells beyond the draw distance
   are skipped whole; a cell can switch to a cheaper far template. Moving instances (cars, people) are packed each
   frame into one buffer holding only those within the draw distance. */
import * as THREE from "three";

// template layouts: [attribute, size, offset] over an interleaved Float32 array of the given stride
export const PROP_LAYOUT = { stride: 10, attrs: [["position", 3, 0], ["normal", 3, 3], ["color", 3, 6], ["part", 1, 9]] };
export const TREE_LAYOUT = { stride: 7, attrs: [["position", 3, 0], ["normal", 3, 3], ["part", 1, 6]] };
// instance layouts
export const PROP_INST = { stride: 8, attrs: [["i0", 4, 0], ["i1", 4, 4]] };       // x y z yaw · r g b scaleX
export const TREE_INST = { stride: 5, attrs: [["inst", 4, 0], ["iy", 1, 4]] };      // x z scale hue · y
export const LATE_SHADOW = 1;   // layer of prop shadows drawn only after the rise (main.js)

// {v, i} template → shared attributes + index, and the template's bounding radius
export function templateAttrs(tpl, layout) {
  const ib = new THREE.InterleavedBuffer(tpl.v, layout.stride), attrs = {};
  for (const [n, s, o] of layout.attrs) attrs[n] = new THREE.InterleavedBufferAttribute(ib, s, o);
  let r = 0; for (let k = 0; k < tpl.v.length; k += layout.stride) r = Math.max(r, Math.hypot(tpl.v[k], tpl.v[k + 1], tpl.v[k + 2]));
  return { attrs, index: new THREE.BufferAttribute(tpl.i, 1), radius: r };
}
function instGeometry(T, buf, layout, count) {
  const g = new THREE.InstancedBufferGeometry();
  g.index = T.index; for (const n in T.attrs) g.setAttribute(n, T.attrs[n]);
  const ib = new THREE.InstancedInterleavedBuffer(buf, layout.stride);
  for (const [n, s, o] of layout.attrs) g.setAttribute(n, new THREE.InterleavedBufferAttribute(ib, s, o));
  g.instanceCount = count;
  return g;
}

/* Static instances in cells.
   pos(buf, k) → [x, y, z] of instance k; pad: how far an instance reaches from its position (template radius × scale) */
export class InstCells {
  constructor({ T, Tfar = null, inst, layout, pos, pad, material, shadowMaterial = null, shadowLayer = 0, far = Infinity, lodDist = Infinity, cell = 400, order = 0 }) {
    this.far = far; this.lodDist = lodDist; this.cells = []; this.meshes = []; this.shadowMeshes = [];
    const n = inst.length / layout.stride, bins = new Map();
    for (let k = 0; k < n; k++) {
      const [x, , z] = pos(inst, k), key = Math.floor(x / cell) + "," + Math.floor(z / cell);
      (bins.get(key) || bins.set(key, []).get(key)).push(k);
    }
    for (const ks of bins.values()) {
      const buf = new Float32Array(ks.length * layout.stride);
      ks.forEach((k, j) => buf.set(inst.subarray(k * layout.stride, (k + 1) * layout.stride), j * layout.stride));
      const box = new THREE.Box3();
      for (let j = 0; j < ks.length; j++) { const p = pos(buf, j); box.expandByPoint(new THREE.Vector3(p[0], p[1], p[2])); }
      box.expandByScalar(pad);
      const sphere = box.getBoundingSphere(new THREE.Sphere());
      const mk = (TT, mat, list) => {
        const g = instGeometry(TT, buf, layout, ks.length); g.boundingSphere = sphere;
        const m = new THREE.Mesh(g, mat); m.renderOrder = order; m.matrixAutoUpdate = false; list.push(m); return m;
      };
      const c = { sphere, near: mk(T, material, this.meshes), far: Tfar ? mk(Tfar, material, this.meshes) : null };
      if (shadowMaterial) { c.sNear = mk(T, shadowMaterial, this.shadowMeshes); c.sFar = Tfar ? mk(Tfar, shadowMaterial, this.shadowMeshes) : null; }
      for (const m of this.shadowMeshes) m.layers.set(shadowLayer);
      this.cells.push(c);
    }
    this.count = n;
  }
  add(scene, shadowScene) { for (const m of this.meshes) scene.add(m); if (shadowScene) for (const m of this.shadowMeshes) shadowScene.add(m); return this; }
  // per frame: distance cull and level of detail from the eye
  update(eye) {
    for (const c of this.cells) {
      const s = c.sphere, d = Math.hypot(s.center.x - eye[0], s.center.y - eye[1], s.center.z - eye[2]) - s.radius;
      const on = d < this.far, near = !c.far || d < this.lodDist;
      c.near.visible = on && near; if (c.far) c.far.visible = on && !near;
      if (c.sNear) { c.sNear.visible = c.near.visible; if (c.sFar) c.sFar.visible = !!(c.far && c.far.visible); }
    }
  }
}

/* Moving instances: write all into `src` (as the old step functions do), then pack() copies those within `far` of
   the eye into the GPU buffer. */
export class InstDynamic {
  constructor({ T, src, layout, material, shadowMaterial = null, shadowLayer = 0, far = Infinity, order = 0 }) {
    this.src = src; this.layout = layout; this.far = far;
    this.buf = new Float32Array(src.length);
    this.geo = instGeometry(T, this.buf, layout, 0);
    this.geo.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1e5);
    this.ib = this.geo.attributes[layout.attrs[0][0]].data;
    this.mesh = new THREE.Mesh(this.geo, material); this.mesh.frustumCulled = false; this.mesh.renderOrder = order; this.mesh.matrixAutoUpdate = false;
    this.shadow = shadowMaterial ? new THREE.Mesh(this.geo, shadowMaterial) : null;
    if (this.shadow) { this.shadow.frustumCulled = false; this.shadow.matrixAutoUpdate = false; this.shadow.layers.set(shadowLayer); }
  }
  add(scene, shadowScene) { scene.add(this.mesh); if (this.shadow && shadowScene) shadowScene.add(this.shadow); return this; }
  pack(eye) {
    const st = this.layout.stride, src = this.src, buf = this.buf, f2 = this.far * this.far, n = src.length / st;
    let m = 0;
    for (let k = 0; k < n; k++) {
      const o = k * st, dx = src[o] - eye[0], dy = src[o + 1] - eye[1], dz = src[o + 2] - eye[2];
      if (dx * dx + dy * dy + dz * dz > f2) continue;
      for (let j = 0; j < st; j++) buf[m * st + j] = src[o + j];
      m++;
    }
    this.geo.instanceCount = m; this.mesh.visible = m > 0; if (this.shadow) this.shadow.visible = m > 0;
    this.ib.needsUpdate = true;
    return m;
  }
}
