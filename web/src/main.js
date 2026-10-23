/* Boot, render loop, shadow pass, picking, test hooks.
   Time comes only from performance.now() / the requestAnimationFrame argument and the loop runs only through
   requestAnimationFrame: tools/record.py and tools/webgl_check.py replace both to step frames. */
import * as THREE from "three";
import { S, reduceMotion } from "./state.js";
import { ISLE, inIsle, clamp, meshGeometry, orient } from "./world.js";
import { loadData, loadImg, decodeData } from "./data.js";
import { buildCity, CONSTRUCT } from "./buildings.js";
import { buildIsland, makeFalls, FALLS, ISLETS } from "./island.js";
import { buildBridges, makeRoads, updateRoads, LAMPS, SIGLIGHTS, BUSLIGHTS } from "./roads.js";
import { makeProps, updateProps } from "./props.js";
import { makeTraffic, updateTraffic, TRAFFIC } from "./traffic.js";
import { makeAir, updateAir, finishAir, AIR } from "./air.js";
import { ROOFTREES, ROOFTREE_Y } from "./buildings.js";
import { LATE_SHADOW } from "./instancing.js";
import { makeGround } from "./ground.js";
import { sky, skyAmbient, makeSky, makeSea, makeClouds, updateClouds } from "./sky.js";
import { U } from "./materials/common.js";
import { makeMeshMaterial, makeShadowMaterial } from "./materials/building.js";
import { Post, LOOK } from "./post.js";
import { HOME, VIEWS, flyTo, initCamera, stepCamera, bindInput, startTour, stopTour } from "./camera.js";
import { $, fmt, sleep, loader, initUI, fillUI, applyModeUI, setTod, setPlate, showCard, closeCard, flyToBuilding, onKey, buildLabels, placeLabels, skyStatus } from "./ui.js";

const canvas = $("#gl");
let renderer;
try {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: "high-performance", alpha: false });
} catch (e) {
  loader.show("浏览器不支持 WebGL2", "请使用最新版 Chrome、Edge、Firefox 或 Safari 打开。", { err: " " }); throw e;
}
// the old engine wrote shader output straight to the canvas: no colour management, no three.js tone mapping
THREE.ColorManagement.enabled = false;
renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
renderer.autoClear = false;
const gl = renderer.getContext();
// GPU context loss (common on mobile when backgrounded): stop drawing, then rebuild by reloading
const CTX = { lost: false };
canvas.addEventListener("webglcontextlost", e => { e.preventDefault(); CTX.lost = true; loader.show("显卡上下文已丢失", "正在等待浏览器恢复 WebGL…"); });
canvas.addEventListener("webglcontextrestored", () => { loader.show("正在恢复", "重新载入场景"); location.reload(); });

const scene = new THREE.Scene(), shadowScene = new THREE.Scene(), dynShadowScene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(0.78 * 180 / Math.PI, 1, 1, 90000);
const post = new Post(renderer);
const meshMat = makeMeshMaterial();
const M = { city: null, island: null, sky: makeSky(), sea: makeSea(), ground: null };
scene.add(M.sky, M.sea);

/* ---------------- textures (GPT Image, downscaled by tools/make_web_textures.py) ---------------- */
const TEX = { rock: null, facade: null, cloud: null };
function loadTex(url, repeat) {
  return new Promise(res => new THREE.TextureLoader().load(url, t => {
    // v = up, like the facade UVs (flipY on, the three.js default); sampled raw, no sRGB decode
    t.wrapS = t.wrapT = repeat ? THREE.RepeatWrapping : THREE.ClampToEdgeWrapping;
    t.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
    res(t);
  }, undefined, () => res(null)));
}
const texReady = Promise.all([loadTex("assets/island-rock.webp", true), loadTex("assets/tower-facade.webp", true), loadTex("assets/cloud-puff.webp", false)])
  .then(([rock, facade, cloud]) => { TEX.rock = rock; TEX.facade = facade; TEX.cloud = cloud; });

/* ---------------- shadow map ----------------
   Depth texture with hardware compare (sampler2DShadow in the shaders), sized to the device, refit around the focus each frame. */
const LOW_END = matchMedia("(pointer: coarse)").matches || Math.min(screen.width, screen.height) < 700;
const SM = { size: Math.min(LOW_END ? 2048 : 3072, renderer.capabilities.maxTextureSize), on: true, texel: 0, rt: null, cam: new THREE.OrthographicCamera() };
{
  const depthRT = size => {
    const dt = new THREE.DepthTexture(size, size);
    dt.minFilter = dt.magFilter = THREE.LinearFilter; dt.compareFunction = THREE.LessEqualCompare;
    return new THREE.WebGLRenderTarget(size, size, { depthTexture: dt, format: THREE.RedFormat, minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter });
  };
  // static casters: redrawn only when sun, focus, extent or what is shown changes (SM.key); moving casters every frame
  SM.depthRT = depthRT;
  SM.rt = depthRT(SM.size); SM.dynSize = Math.min(1536, SM.size); SM.dyn = depthRT(SM.dynSize); SM.key = "";
}
function setShadowSize(size) { SM.rt.dispose(); SM.size = size; SM.rt = SM.depthRT(size); SM.key = ""; }
const shadowMat = makeShadowMaterial();
shadowScene.userData.shadowMat = shadowMat;

/* ---------------- resolution ---------------- */
// dynamic resolution: a few fixed levels with hysteresis and a minimum dwell time, so render targets are only
// reallocated when the load really changes (from the old engine; tests pin it through window.SZ_TEST)
const PERF_LEVELS = [1, 0.85, 0.72, 0.6];
const PERF = { level: 0, scale: (window.SZ_TEST && window.SZ_TEST.scale) || 1, ema: 0.016, lastAdj: 0, slow: 0, fast: 0 };
function adaptPerf(now, dt) {
  PERF.ema += (dt - PERF.ema) * 0.05;
  if (window.SZ_TEST || !S.ready || document.hidden) return;
  if (PERF.ema > 0.036) { PERF.slow += dt; PERF.fast = 0; } else if (PERF.ema < 0.019) { PERF.fast += dt; PERF.slow = 0; } else { PERF.slow = PERF.fast = 0; }
  const since = now - PERF.lastAdj;
  let lv = PERF.level;
  if (PERF.slow > 2 && since > 4000 && lv < PERF_LEVELS.length - 1) lv++;
  else if (PERF.fast > 6 && since > 10000 && lv > 0) lv--;
  if (lv === PERF.level) return;
  PERF.level = lv; PERF.scale = PERF_LEVELS[lv]; PERF.lastAdj = now; PERF.slow = PERF.fast = 0;
  // at the lowest level also drop the shadow map to 2048 (one-off reallocation)
  if (lv === PERF_LEVELS.length - 1 && SM.size > 2048) setShadowSize(2048);
}
const VIEW = { cw: Math.max(1, canvas.clientWidth), ch: Math.max(1, canvas.clientHeight) };
new ResizeObserver(es => { const r = es[es.length - 1].contentRect; VIEW.cw = Math.max(1, r.width); VIEW.ch = Math.max(1, r.height); }).observe(canvas);
function resize() {
  const dpr = Math.min(devicePixelRatio || 1, 2, Math.sqrt(3.2e6 / (VIEW.cw * VIEW.ch))) * PERF.scale;
  const w = Math.max(1, Math.round(VIEW.cw * dpr)), h = Math.max(1, Math.round(VIEW.ch * dpr));
  if (canvas.width !== w || canvas.height !== h) renderer.setSize(w, h, false);
  post.setSize(w, h);
}

/* ---------------- build scene ---------------- */
async function buildScene() {
  const D = await loadData();
  window.D = D; S.R = D.R; initCamera(D);
  await texReady;
  loader.show("正在搭建深圳湾", `${fmt(D.roads.length)} 条道路 · ${fmt(D.buildings.length + D.landmarks.length)} 栋楼`);
  await sleep(30);
  const [maskImg, luImg] = await Promise.all([loadImg(D.mask), loadImg(D.lu)]);
  const osm = decodeData(D); S.osm = osm;
  const bridges = buildBridges(osm);   // marks bridge roads as ribbons: the ground and road mesh skip them
  const city = buildCity(osm, D); orient(city.V, city.I);
  S.lmIdx = city.lmEnd; S.tris = city.I.length / 3;
  M.city = new THREE.Mesh(meshGeometry(city.V, city.I), meshMat);
  loader.show("正在绘制地面", "海岸、绿地与道路"); await sleep(30);
  M.ground = makeGround(osm, D, maskImg, luImg, renderer);
  loader.show("正在升起岛屿", "岩层、垂岩、瀑布与小浮岛"); await sleep(30);
  const isle = buildIsland(maskImg, D); S.waterAt = isle.waterAt; orient(isle.V, isle.I);
  M.island = new THREE.Mesh(meshGeometry(isle.V, isle.I), meshMat);
  M.city.frustumCulled = M.island.frustumCulled = false;   // vertices are lifted in the shader during the rise
  M.island.renderOrder = 1;
  loader.show("正在铺路", "车道线、斑马线、人行道、路灯与球场"); await sleep(30);
  makeRoads(osm, bridges, meshMat, scene, shadowScene);
  loader.show("正在种树", "行道树、车流、行人、瀑布与云层"); await sleep(30);
  const itx = [], ity = [];
  for (const I of ISLETS) { itx.push(...I.tx); ity.push(...I.ty); }
  itx.push(...ROOFTREES); ity.push(...ROOFTREE_Y);
  M.props = makeProps(D, { x: itx, y: ity }, meshMat, scene, shadowScene);
  makeTraffic(osm, bridges, isle.waterAt, scene, dynShadowScene);
  scene.add(makeFalls());
  M.clouds = makeClouds(TEX.cloud); scene.add(M.clouds.mesh);
  makeAir(osm, D, isle.waterAt, scene, dynShadowScene);
  M.city.geometry.computeBoundingSphere();
  scene.add(M.ground, M.city, M.island);
  for (const m of [M.city, M.island]) { const s = new THREE.Mesh(m.geometry, shadowMat); s.frustumCulled = false; shadowScene.add(s); }

  let tallest = -1, th = 0;
  osm.buildings.forEach((b, i) => { if (b.h > th) { th = b.h; tallest = i; } });
  S.tallest = tallest;
  const P = M.props, nTrees = P.trees[1].count + P.trees[2].count + P.trees[3].count;
  fillUI(osm, D, { construct: CONSTRUCT.length, falls: FALLS.groups.length, islets: ISLETS.length, trees: nTrees, shrubs: P.trees[0].count,
    lamps: LAMPS.length, signals: SIGLIGHTS.length, bus: BUSLIGHTS.length, features: P.features.n });
  buildLabels(osm, D);
  S.sel = -1; $("#card").hidden = true;
  S.rise = reduceMotion ? 1 : 0; S.riseStart = performance.now(); S.ready = true;
  S.cam = { tx: 0, tz: 0, ty: -400, yaw: -0.3, pitch: 0.75, dist: 21000 };
  flyTo(HOME(), reduceMotion ? 0 : 7000);
  loader.hide();
}

/* ---------------- picking: ray against the city mesh, building index from the bid attribute ---------------- */
const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
function pick(cx, cy) {
  if (!S.ready || CTX.lost) return;
  const r = canvas.getBoundingClientRect();
  ndc.set((cx - r.left) / r.width * 2 - 1, -((cy - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(ndc, camera);
  const hit = ray.intersectObject(M.city, false)[0];
  const id = hit ? M.city.geometry.attributes.bid.getX(hit.face.a) : -1;
  if (id >= 0 && id < S.osm.buildings.length) showCard(id); else closeCard();
}

/* ---------------- render loop ---------------- */
let last = performance.now();
const v3 = (u, a) => u.value.set(a[0], a[1], a[2]);
function tick(now) {
  requestAnimationFrame(tick);
  const dt = Math.min(0.05, (now - last) / 1000); last = now;
  if (CTX.lost) return;
  adaptPerf(now, dt);
  resize();
  // clock
  if (Math.abs(S.todTarget - S.tod) > 0.001) { S.tod += (S.todTarget - S.tod) * Math.min(1, dt * 2.2); if (Math.abs(S.todTarget - S.tod) < 0.01) S.tod = S.todTarget; }
  const L = sky(S.tod);
  applyModeUI(L.night);
  S.wind[0] += dt * 6; S.wind[1] += dt * 2.5;
  if (S.ready && S.rise < 1) S.rise = Math.min(1, (now - S.riseStart) / 4200);

  // camera
  const [eye, tgt] = stepCamera(now, reduceMotion && S.tour ? 0 : dt);
  const W = canvas.width, H = canvas.height;
  const dist = Math.hypot(eye[0] - tgt[0], eye[1] - tgt[1], eye[2] - tgt[2]);
  camera.near = clamp(Math.min(dist, Math.abs(eye[1]) + 60) * 0.02, 0.8, 60); camera.far = 90000; camera.aspect = W / H;
  camera.updateProjectionMatrix();
  camera.position.set(eye[0], eye[1], eye[2]); camera.up.set(0, 1, 0); camera.lookAt(tgt[0], tgt[1], tgt[2]); camera.updateMatrixWorld();
  U.uVP.value.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);

  if (!S.ready) {
    renderer.setRenderTarget(null); renderer.setClearColor(new THREE.Color(0.05, 0.06, 0.09), 1); renderer.clear();
    return;
  }

  // shadow map fitted around the focus, snapped to texels
  const focus = S.tour || S.follow ? [eye[0] + (tgt[0] - eye[0]) * 0.4, 0, eye[2] + (tgt[2] - eye[2]) * 0.4] : [tgt[0], 0, tgt[2]];
  const hs0 = clamp((S.tour || S.follow ? Math.max(500, Math.abs(eye[1]) * 2.2) : dist * 0.75), 350, 4300);
  const hs = 350 * Math.pow(1.04, Math.round(Math.log(hs0 / 350) / Math.log(1.04)));   // 4 % steps: zooming redraws the static map only per step
  const texelW = 2 * hs / SM.size; SM.texel = texelW;
  const fx = Math.round(focus[0] / texelW) * texelW, fz = Math.round(focus[2] / texelW) * texelW;
  const ld = L.lightDir, lc = SM.cam;
  lc.left = -hs; lc.right = hs; lc.bottom = -hs; lc.top = hs; lc.near = 100; lc.far = 10000; lc.updateProjectionMatrix();
  lc.position.set(fx + ld[0] * 5000, ld[1] * 5000, fz + ld[2] * 5000);
  if (Math.abs(ld[1]) > 0.99) lc.up.set(1, 0, 0); else lc.up.set(0, 1, 0);
  lc.lookAt(fx, 0, fz); lc.updateMatrixWorld();
  U.uLightVP.value.multiplyMatrices(lc.projectionMatrix, lc.matrixWorldInverse);

  // uniforms shared by every scene material
  v3(U.uSunDir, L.sun); v3(U.uLightDir, L.lightDir); v3(U.uLightCol, L.lightCol);
  U.uNight.value = L.night; U.uGold.value = L.gold; v3(U.uCam, eye);
  U.uFogDen.value = 1 / (S.R * (6.5 + 9.0 * (1 - L.night)));   // style A: clearer air by day
  U.uIsle.value.set(ISLE.R0, ISLE.thH, ISLE.lobe); v3(U.uSkyAmb, skyAmbient(L));
  U.uTime.value = now / 1000; U.uWind.value.set(S.wind[0], S.wind[1]);
  U.uShadow.value = SM.rt.depthTexture; U.uShadowOn.value = L.dayF > 0.15 && SM.on ? 1 : 0;
  U.uShadowDyn.value = SM.dyn.depthTexture; U.uShadowDynOn.value = U.uShadowOn.value;
  U.uShadowTexel.value.set(1 / SM.size, 1 / SM.size); U.uNOff.value = SM.texel * 1.5;
  U.uRise.value = S.rise; U.uMaxR.value = S.R * 1.42;
  U.uRock.value = TEX.rock || U.uRock.value; U.uFacade.value = TEX.facade || U.uFacade.value;
  U.uTexOn.value.set(TEX.rock ? 1 : 0, TEX.facade ? 1 : 0);
  M.sky.material.uniforms.uInvVP.value.copy(U.uVP.value).invert(); v3(M.sky.material.uniforms.uMoonDir, L.moon);
  const mu = meshMat.uniforms;
  mu.uSel.value = S.sel; mu.uLit.value = L.lit; mu.uAccent.value = L.night > 0.5 ? [1.6, 1.0, 0.35] : [0.85, 0.45, 0.12];
  M.city.geometry.setDrawRange(0, S.showGen ? Infinity : S.lmIdx);
  // streets: cells by distance, moving things stepped and packed, clouds drifted and sorted
  updateRoads(eye); updateProps(eye);
  updateTraffic(reduceMotion ? 0 : dt, now / 1000, L.night > 0.5, eye);
  const pm = TRAFFIC.lights.material.uniforms; pm.uPx.value = H / (2 * Math.tan(0.39)); pm.uAdd.value = 1;
  updateAir(now / 1000, reduceMotion ? 0 : dt, L, eye); finishAir(H / (2 * Math.tan(0.39)));
  M.clouds.mesh.visible = S.showClouds; if (S.showClouds) updateClouds(M.clouds, S.wind, eye, L.night, camera);

  if (L.dayF > 0.15 && SM.on) {
    if (S.rise > 0.9) lc.layers.enable(LATE_SHADOW); else lc.layers.disable(LATE_SHADOW);
    const key = [ld[0].toFixed(5), ld[1].toFixed(5), ld[2].toFixed(5), fx, fz, hs, S.rise < 1 ? now : 1, S.showGen].join();
    if (key !== SM.key) { SM.key = key; SM.redraws = (SM.redraws || 0) + 1; renderer.setRenderTarget(SM.rt); renderer.clear(false, true, false); renderer.render(shadowScene, lc); }
    renderer.setRenderTarget(SM.dyn); renderer.clear(false, true, false); renderer.render(dynShadowScene, lc);
  }
  post.render(scene, camera, L, Math.max(dist, 1));
  placeLabels(U.uVP.value.elements, eye, VIEW.cw, VIEW.ch);
  skyStatus(now);
}
requestAnimationFrame(tick);

/* ---------------- boot ---------------- */
initUI();
bindInput(canvas, { onClick: pick, onKey });
// test hooks (tools/record.py, tools/webgl_check.py) — see docs/handoff.md §4.4
Object.assign(window, { $, S, PERF, setTod, flyTo, VIEWS, HOME, startTour, stopTour, flyToBuilding, closeCard, setPlate, FALLS, AIR, inIsle, pick,
  canvas, gl, renderer, camera, post, SM, CTX });
window.__dbg = { LOOK, scene, shadowScene, dynShadowScene, M, meshMat, post, SM, U, THREE, PERF };   // debugging / profiling only
buildScene().catch(e => { console.error(e); loader.show("加载失败", "场景构建出错，请刷新页面重试。", { err: e.message || String(e) }); });
