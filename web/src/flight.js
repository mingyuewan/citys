/* Flight mode (phase 4): fly a small seaplane round the island, between the towers and through the waterfalls.
   Steering by dragging (mouse or touch) or the arrow keys, W / S throttle, Space boost, Esc to land back in the
   orbit view. A chase camera follows. Collisions against a height field of every building (rasterized at 8 m when
   the scene is built), the ground and the rock body; passing through a waterfall sheet counts. */
import { S, reduceMotion } from "./state.js";
import { clamp, lerp, isleR } from "./world.js";
import { isleScaleAt, FALLS } from "./island.js";
import { TPL } from "./templates.js";
import { emit } from "./air.js";

const $ = s => document.querySelector(s);
export const FLY = { on: false, pos: [0, 0, 0], yaw: 0, pitch: 0, roll: 0, speed: 0, throttle: 0.45, steer: [0, 0], keys: new Set(),
  crash: null, falls: 0, inFall: false, eye: null, t: 0, best: 0 };
const SPEED = [45, 170], BOOST = 260;

/* ---------------- height field of the city (max roof height per 8 m cell) ---------------- */
const HF = { n: 0, cell: 8, ext: 3500, h: null, who: null };
function insideRing(x, z, r) { let c = false; for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const [xi, zi] = r[i], [xj, zj] = r[j]; if ((zi > z) !== (zj > z) && x < (xj - xi) * (z - zi) / (zj - zi) + xi) c = !c; } return c; }
export function buildHeightField(osm) {
  HF.n = Math.ceil(2 * HF.ext / HF.cell); HF.h = new Float32Array(HF.n * HF.n); HF.who = new Int32Array(HF.n * HF.n).fill(-1);
  osm.buildings.forEach((b, bid) => {
    const r = b.ring; if (!r || r.length < 3) return;
    let x0 = 1e9, x1 = -1e9, z0 = 1e9, z1 = -1e9;
    for (const [x, z] of r) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); z0 = Math.min(z0, z); z1 = Math.max(z1, z); }
    const i0 = Math.max(0, Math.floor((x0 + HF.ext) / HF.cell)), i1 = Math.min(HF.n - 1, Math.floor((x1 + HF.ext) / HF.cell));
    const j0 = Math.max(0, Math.floor((z0 + HF.ext) / HF.cell)), j1 = Math.min(HF.n - 1, Math.floor((z1 + HF.ext) / HF.cell));
    const h = b.h + (b.landmark ? 0 : 3);
    for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
      const k = j * HF.n + i, x = -HF.ext + (i + 0.5) * HF.cell, z = -HF.ext + (j + 0.5) * HF.cell;
      if (h > HF.h[k] && (insideRing(x, z, r) || (i1 - i0 < 2 && j1 - j0 < 2))) { HF.h[k] = h; HF.who[k] = bid; }
    }
  });
}
function heightAt(x, z) {
  const i = Math.floor((x + HF.ext) / HF.cell), j = Math.floor((z + HF.ext) / HF.cell);
  if (i < 0 || j < 0 || i >= HF.n || j >= HF.n) return [0, -1];
  const k = j * HF.n + i; return [HF.h[k], HF.who[k]];
}

/* ---------------- control ---------------- */
let hud = null;
export function startFlight(from) {
  FLY.on = true; S.flight = true; S.tour = null; S.fly = null; S.follow = null; S.orbit = false;
  document.body.classList.add("flying");
  const e = from || [-5200, 520, 2600];
  FLY.pos = e.slice(); FLY.yaw = Math.atan2(-e[2], -e[0]); FLY.pitch = -0.06; FLY.roll = 0; FLY.speed = 110; FLY.throttle = 0.45;
  FLY.crash = null; FLY.eye = null; FLY.falls = 0; FLY.t = 0;
  hud = $("#flyhud"); if (hud) hud.hidden = false;
  $("#bFly") && $("#bFly").setAttribute("aria-pressed", "true");
}
export function stopFlight() {
  if (!FLY.on) return;
  FLY.on = false; S.flight = false; document.body.classList.remove("flying", "splash");
  if (hud) hud.hidden = true;
  $("#bFly") && $("#bFly").setAttribute("aria-pressed", "false");
  // land the orbit camera on what the plane was looking at
  const p = FLY.pos, f = forward();
  Object.assign(S.cam, { tx: clamp(p[0] + f[0] * 600, -4000, 4000), tz: clamp(p[2] + f[2] * 600, -4000, 4000), ty: 0, yaw: Math.atan2(-f[0], -f[2]), pitch: 0.35, dist: 1600 });
}
const forward = () => [Math.cos(FLY.pitch) * Math.cos(FLY.yaw), Math.sin(FLY.pitch), Math.cos(FLY.pitch) * Math.sin(FLY.yaw)];

export function bindFlightInput(canvas) {
  addEventListener("keydown", e => {
    if (!FLY.on || (e.target.closest && e.target.closest("select,input"))) return;
    const k = e.key.toLowerCase();
    if (k === "escape") { stopFlight(); e.preventDefault(); return; }
    FLY.keys.add(k); if (k.startsWith("arrow") || k === " ") e.preventDefault();
  });
  addEventListener("keyup", e => FLY.keys.delete(e.key.toLowerCase()));
  let drag = null;
  canvas.addEventListener("pointerdown", e => { if (FLY.on) drag = { x: e.clientX, y: e.clientY }; });
  addEventListener("pointermove", e => {
    if (!FLY.on || !drag) return;
    const s = Math.min(innerWidth, innerHeight) * 0.35;
    FLY.steer = [clamp((e.clientX - drag.x) / s, -1, 1), clamp((e.clientY - drag.y) / s, -1, 1)];
  });
  addEventListener("pointerup", () => { drag = null; FLY.steer = [0, 0]; });
}

/* ---------------- per frame ---------------- */
// returns [eye, target] for the camera, or null when not flying
export function stepFlight(dt, now) {
  if (!FLY.on) return null;
  FLY.t += dt;
  const K = FLY.keys;
  if (FLY.crash) {   // tumbling for a moment, then a fresh start
    FLY.crash.t += dt;
    if (FLY.crash.t > 2.2) { const p = FLY.crash.respawn; FLY.crash = null; startFlight(p); }
  } else {
    // steering: drag offset or arrow keys; the plane banks into turns
    const sx = clamp(FLY.steer[0] + (K.has("arrowright") || K.has("d") ? 1 : 0) - (K.has("arrowleft") || K.has("a") ? 1 : 0), -1, 1);
    const sy = clamp(FLY.steer[1] + (K.has("arrowdown") ? 1 : 0) - (K.has("arrowup") ? 1 : 0), -1, 1);
    if (K.has("w")) FLY.throttle = Math.min(1, FLY.throttle + dt * 0.5);
    if (K.has("s")) FLY.throttle = Math.max(0, FLY.throttle - dt * 0.5);
    const boost = K.has(" ") ? 1 : 0;
    FLY.yaw += sx * 0.9 * dt;
    FLY.pitch = clamp(FLY.pitch - sy * 0.75 * dt, -0.95, 0.85);
    FLY.pitch *= 1 - dt * 0.15 * (1 - Math.abs(sy));   // level out by itself
    FLY.roll = lerp(FLY.roll, -sx * 0.75, Math.min(1, dt * 3));
    const want = boost ? BOOST : lerp(SPEED[0], SPEED[1], FLY.throttle);
    FLY.speed = lerp(FLY.speed, want - Math.sin(FLY.pitch) * 30, Math.min(1, dt * 0.9));
    const f = forward();
    for (let i = 0; i < 3; i++) FLY.pos[i] += f[i] * FLY.speed * dt;
    // keep within the sky: turn back beyond 14 km, stay above the cloud sea and below 3 km
    const p = FLY.pos, r = Math.hypot(p[0], p[2]);
    if (r > 14000) { const back = Math.atan2(-p[2], -p[0]); let d = back - FLY.yaw; d = Math.atan2(Math.sin(d), Math.cos(d)); FLY.yaw += d * Math.min(1, dt * 0.8); }
    if (p[1] < -1820) { p[1] = -1820; FLY.pitch = Math.max(FLY.pitch, 0.1); }
    if (p[1] > 3200) { p[1] = 3200; FLY.pitch = Math.min(FLY.pitch, -0.05); }
    collide(p);
    waterfalls(p);
  }
  const f = forward(), p = FLY.pos;
  // chase camera
  const back = 17 + FLY.speed * 0.04, want = [p[0] - f[0] * back, p[1] - f[1] * back + 5, p[2] - f[2] * back];
  FLY.eye = FLY.eye ? FLY.eye.map((v, i) => lerp(v, want[i], Math.min(1, dt * (reduceMotion ? 10 : 5)))) : want;
  const shake = FLY.crash ? (2.2 - FLY.crash.t) * 0.8 : 0;
  const eye = FLY.eye.map((v, i) => v + (shake ? (Math.sin(now * 0.05 + i * 2) * shake) : 0));
  hudUpdate();
  return [eye, [p[0] + f[0] * 60, p[1] + f[1] * 60, p[2] + f[2] * 60]];
}

// the plane and its spinning propeller: after the aerial layer's per-frame reset (air.js updateAir)
export function drawFlight(now) {
  if (!FLY.on) return;
  const f = forward(), p = FLY.pos, tumble = FLY.crash ? FLY.crash.t * 6 : 0;
  emit(TPL.flyer, p, FLY.yaw, FLY.pitch - (FLY.crash ? FLY.crash.t * 0.6 : 0), FLY.roll + tumble, 1);
  emit(TPL.prop, [p[0] + f[0] * 3.8, p[1] + f[1] * 3.8, p[2] + f[2] * 3.8], FLY.yaw, FLY.pitch, FLY.roll + now * 0.06, 1);
}
function crash(msg) {
  if (FLY.crash) return;
  const p = FLY.pos, a = Math.atan2(p[2], p[0]) + 0.6, d = Math.max(4200, Math.hypot(p[0], p[2]) + 1500);
  FLY.crash = { t: 0, msg, respawn: [Math.cos(a) * d, 480, Math.sin(a) * d] };
}
function collide(p) {
  const rr = Math.hypot(p[0], p[2]), R0 = isleR(Math.atan2(p[2], p[0]));
  if (p[1] < 0) {   // under the rim: the rock body narrows with depth
    if (rr < R0 * isleScaleAt(p[1]) * 0.98 && p[1] > -2640) crash("撞上了岛底的岩壁");
    return;
  }
  if (rr < R0) {
    const [h, who] = heightAt(p[0], p[2]);
    if (p[1] < Math.max(h, 4)) {
      const b = who >= 0 && S.osm.buildings[who];
      crash(b ? (b.name ? `撞上了 ${b.name.replace(/[（(].*?[)）]/g, "")}` : `撞上了一栋 ${Math.round(b.h)} 米高的楼`) : "降落失败：撞到了地面");
    }
  }
}
function waterfalls(p) {
  let inside = false;
  for (const G of FALLS.groups) {
    const dx = p[0] - G.x, dz = p[2] - G.z, along = dx * -G.oz + dz * G.ox, out = dx * G.ox + dz * G.oz;
    const t = clamp((G.y - p[1]) / G.H, 0, 1), sheet = 6 + 150 * Math.pow(t, 1.5) * (G.H / 1400);
    if (Math.abs(along) < G.w * 0.5 && p[1] < G.y && p[1] > G.y - G.H * 0.95 && Math.abs(out - sheet) < 28) inside = true;
  }
  if (inside && !FLY.inFall) FLY.falls++;
  FLY.inFall = inside;
  document.body.classList.toggle("splash", inside);
}
function hudUpdate() {
  if (!hud) return;
  const p = FLY.pos, h = Math.round(p[1]), v = Math.round(FLY.speed * 3.6);
  hud.querySelector(".v").textContent = `${v} km/h`;
  hud.querySelector(".h").textContent = `${h} m`;
  hud.querySelector(".f").textContent = FLY.falls ? `穿越瀑布 ×${FLY.falls}` : "";
  hud.querySelector(".msg").textContent = FLY.crash ? FLY.crash.msg + " · 重新起飞…" : "";
}
