/* Post: HDR + MSAA scene target → bloom (bright, 2× down chain, tent up chain) → ACES composite to the canvas.
   Same passes and constants as the old "resolve + bloom + composite" block, on three.js render targets. */
import * as THREE from "three";
import { lerp } from "./world.js";
import { makeBright, makeDown, makeUp, makeComp } from "./materials/post.js";

export class Post {
  constructor(renderer) {
    this.r = renderer;
    this.hdr = renderer.capabilities.isWebGL2 && renderer.extensions.has("EXT_color_buffer_float");
    this.type = this.hdr ? THREE.HalfFloatType : THREE.UnsignedByteType;
    this.w = this.h = 0; this.scene = null; this.bloom = [];
    this.quad = new THREE.Mesh(new THREE.BufferGeometry(), null);
    this.quad.geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(9), 3));
    this.quad.frustumCulled = false;
    this.qs = new THREE.Scene(); this.qs.add(this.quad);
    this.qc = new THREE.Camera();
    this.m = { bright: makeBright(), down: makeDown(), up: makeUp(), comp: makeComp() };
    this.m.up.blending = THREE.CustomBlending; this.m.up.blendSrc = this.m.up.blendDst = THREE.OneFactor; this.m.up.blendEquation = THREE.AddEquation;
  }
  get mode() { return (this.hdr ? "RGBA16F" : "RGBA8") + (this.scene && this.scene.samples ? ` MSAA×${this.scene.samples}` : " 无 MSAA"); }
  setSize(w, h) {
    if (w === this.w && h === this.h) return;
    this.w = w; this.h = h;
    if (this.scene) this.scene.dispose();
    for (const b of this.bloom) b.dispose();
    const opt = { type: this.type, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, depthBuffer: false };
    this.scene = new THREE.WebGLRenderTarget(w, h, { ...opt, depthBuffer: true, samples: 4 });
    this.bloom = [];
    let bw = w >> 1, bh = h >> 1;
    for (let i = 0; i < 5 && bw > 8 && bh > 8; i++) { this.bloom.push(new THREE.WebGLRenderTarget(bw, bh, opt)); bw >>= 1; bh >>= 1; }
  }
  pass(mat, target) { this.quad.material = mat; this.r.setRenderTarget(target); this.r.render(this.qs, this.qc); }
  // draw `scene` into the HDR target, then bloom + composite onto the canvas
  render(scene, camera, L) {
    const r = this.r, B = this.bloom, m = this.m;
    r.setRenderTarget(this.scene); r.setClearColor(0x000000, 1); r.clear(true, true, false);
    r.render(scene, camera);
    if (B.length) {
      m.bright.uniforms.uTex.value = this.scene.texture; m.bright.uniforms.uThr.value = this.hdr ? lerp(1.15, 0.85, L.night) : 0.8;
      this.pass(m.bright, B[0]);
      for (let i = 1; i < B.length; i++) { m.down.uniforms.uTex.value = B[i - 1].texture; m.down.uniforms.uTexel.value = [1 / B[i - 1].width, 1 / B[i - 1].height]; this.pass(m.down, B[i]); }
      for (let i = B.length - 1; i > 0; i--) { m.up.uniforms.uTex.value = B[i].texture; m.up.uniforms.uTexel.value = [1 / B[i].width, 1 / B[i].height]; this.pass(m.up, B[i - 1]); }
    }
    const u = m.comp.uniforms;
    u.uScene.value = this.scene.texture; u.uBloom.value = B.length ? B[0].texture : this.scene.texture;
    u.uBloomK.value = B.length ? lerp(0.35, 0.9, L.night) : 0; u.uExpo.value = lerp(0.92, 1.15, L.night); u.uNight.value = L.night;
    this.pass(m.comp, null);
  }
}
