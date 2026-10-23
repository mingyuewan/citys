/* Post: HDR + MSAA scene target (with depth) → bloom (bright, 2× down chain, tent up chain; as the old engine) and a
   ½ ¼ ⅛ blur pyramid for the tilt-shift → style A composite to the canvas (materials/post.js). LOOK holds its knobs. */
import * as THREE from "three";
import { lerp } from "./world.js";
import { makeBright, makeDown, makeUp, makeComp } from "./materials/post.js";

// style A look: tilt-shift strength and range, grade (see compFS); tuned against build/style/concept-*.png
export const LOOK = { tilt: [1.0, 0.18, 1.1, 0.26], warm: [1.03, 1.0, 0.96], lift: [0.035, 0.025, 0.06], sat: 1.16, vig: 0.28, cavity: [0.35, 0.22, 1.5] };
export class Post {
  constructor(renderer) {
    this.r = renderer;
    this.hdr = renderer.capabilities.isWebGL2 && renderer.extensions.has("EXT_color_buffer_float");
    this.type = this.hdr ? THREE.HalfFloatType : THREE.UnsignedByteType;
    this.w = this.h = 0; this.scene = null; this.bloom = []; this.dof = [];
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
    for (const b of [...this.bloom, ...this.dof]) b.dispose();
    const opt = { type: this.type, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, depthBuffer: false };
    this.scene = new THREE.WebGLRenderTarget(w, h, { ...opt, depthBuffer: true, samples: 4, depthTexture: new THREE.DepthTexture(w, h) });
    this.dof = [1, 2, 3].map(k => new THREE.WebGLRenderTarget(Math.max(1, w >> k), Math.max(1, h >> k), opt));
    this.bloom = [];
    let bw = w >> 1, bh = h >> 1;
    for (let i = 0; i < 5 && bw > 8 && bh > 8; i++) { this.bloom.push(new THREE.WebGLRenderTarget(bw, bh, opt)); bw >>= 1; bh >>= 1; }
  }
  pass(mat, target) { this.quad.material = mat; this.r.setRenderTarget(target); this.r.render(this.qs, this.qc); }
  // draw `scene` into the HDR target, then bloom + composite onto the canvas
  // focus: distance from the eye to what it looks at (the orbit target)
  render(scene, camera, L, focus) {
    const r = this.r, B = this.bloom, m = this.m;
    r.setRenderTarget(this.scene); r.setClearColor(0x000000, 1); r.clear(true, true, false);
    r.render(scene, camera);
    if (B.length) {
      m.bright.uniforms.uTex.value = this.scene.texture; m.bright.uniforms.uThr.value = this.hdr ? lerp(1.15, 0.85, L.night) : 0.8;
      this.pass(m.bright, B[0]);
      for (let i = 1; i < B.length; i++) { m.down.uniforms.uTex.value = B[i - 1].texture; m.down.uniforms.uTexel.value = [1 / B[i - 1].width, 1 / B[i - 1].height]; this.pass(m.down, B[i]); }
      for (let i = B.length - 1; i > 0; i--) { m.up.uniforms.uTex.value = B[i].texture; m.up.uniforms.uTexel.value = [1 / B[i].width, 1 / B[i].height]; this.pass(m.up, B[i - 1]); }
    }
    // blur pyramid for the tilt-shift
    for (let i = 0; i < 3; i++) { const src = i ? this.dof[i - 1] : this.scene; m.down.uniforms.uTex.value = src.texture; m.down.uniforms.uTexel.value = [1 / src.width, 1 / src.height]; this.pass(m.down, this.dof[i]); }
    const u = m.comp.uniforms;
    u.uDepth.value = this.scene.depthTexture; u.uD0.value = this.dof[0].texture; u.uD1.value = this.dof[1].texture; u.uD2.value = this.dof[2].texture;
    u.uTexD1.value = [1 / this.dof[1].width, 1 / this.dof[1].height]; u.uTexD2.value = [1 / this.dof[2].width, 1 / this.dof[2].height];
    u.uNear.value = camera.near; u.uFar.value = camera.far; u.uFocus.value = focus;
    u.uTexel.value = [1 / this.w, 1 / this.h]; u.uCav.value = LOOK.cavity;
    u.uTilt.value = LOOK.tilt; u.uWarm.value = LOOK.warm; u.uLift.value = LOOK.lift; u.uSat.value = LOOK.sat; u.uVig.value = LOOK.vig;
    u.uScene.value = this.scene.texture; u.uBloom.value = B.length ? B[0].texture : this.scene.texture;
    u.uBloomK.value = B.length ? lerp(0.35, 0.9, L.night) : 0; u.uExpo.value = lerp(0.92, 1.15, L.night); u.uNight.value = L.night;
    this.pass(m.comp, null);
  }
}
