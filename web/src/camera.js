/* Orbit camera, flyTo, view presets, scripted aerial tour, pointer / wheel / keyboard input.
   Ported from the "camera" section of src/city.src.html. Following aircraft comes with air.js. */
import { clamp, lerp, norm3, isleR } from "./world.js";
import { FALLS, isleScaleAt } from "./island.js";
import { S, reduceMotion } from "./state.js";
import { AIR, quadPos } from "./air.js";

const $ = s => document.querySelector(s);
let D = null;
export function initCamera(data) { D = data; }

export const HOME = () => ({ tx: 0, tz: 0, ty: -350, yaw: -0.85, pitch: 0.28, dist: 9200 });
export const VIEWS = {
  "v-isle": HOME,
  "v-city": () => ({ tx: 250, tz: 250, ty: 0, yaw: -0.82, pitch: 0.5, dist: 2500 }),
  "v-falls": () => {
    const G = FALLS.groups.slice().sort((a, b) => b.w - a.w)[0] || { x: 2000, z: 2000, ox: 0.7, oz: 0.7 };
    return { tx: G.x + G.ox * 200, tz: G.z + G.oz * 200, ty: -620, yaw: Math.atan2(G.ox, G.oz) + 0.35, pitch: 0.1, dist: 3400 };
  },
  "v-under": () => ({ tx: 0, tz: 0, ty: -700, yaw: S.cam.yaw, pitch: -0.16, dist: 6200 })
};

export function flyTo(to, ms) {
  stopTour(); S.follow = null;
  const from = { ...S.cam };
  if (!ms) { Object.assign(S.cam, to); S.fly = null; return; }
  let dy = to.yaw - from.yaw; while (dy > Math.PI) dy -= 2 * Math.PI; while (dy < -Math.PI) dy += 2 * Math.PI;
  S.fly = { from, to: { ...to, yaw: from.yaw + dy }, t0: performance.now(), ms };
}
export function clampCam() {
  const c = S.cam;
  c.dist = Math.min(24000, Math.max(45, c.dist));
  c.pitch = Math.min(1.52, Math.max(c.dist > 4200 ? -0.6 : ((c.ty || 0) < -50 ? -0.3 : 0.06), c.pitch));
  const lim = S.R * 1.3; c.tx = clamp(c.tx, -lim, lim); c.tz = clamp(c.tz, -lim, lim);
}
function orbitEye() {
  const c = S.cam, cp = Math.cos(c.pitch);
  return [c.tx + Math.sin(c.yaw) * cp * c.dist, Math.sin(c.pitch) * c.dist + (c.ty || 0), c.tz + Math.cos(c.yaw) * cp * c.dist];
}
// scripted aerial tour (Catmull-Rom through control points)
function tourPoints() {
  const L = k => (D.landmarks.find(l => l.k === k) || { c: [0, 0] }).c;
  const cr = L("bamboo"), itc = L("tiered"), tx = L("tencentS"), one = L("taper"), coc = L("cocoon"), hk = L("hanking");
  const G = FALLS.groups.slice().sort((a, b) => b.w - a.w)[0] || { x: 2200, z: 1800, ox: 0.7, oz: 0.6 };
  const fx = G.x, fz = G.z, ox = G.ox, oz = G.oz;
  return [
    [9500, 2600, 9000], [fx + ox * 2600, 300, fz + oz * 2600], [fx + ox * 1100 + oz * 600, -350, fz + oz * 1100 - ox * 600], [fx + ox * 500 - oz * 500, 120, fz + oz * 500 + ox * 500],
    [fx * 0.75, 220, fz * 0.75], [900, 160, 700],
    [cr[0] + 420, 330, cr[1] + 120], [cr[0] + 120, 360, cr[1] - 380], [cr[0] - 330, 300, cr[1] - 150], [coc[0] + 200, 120, coc[1] - 260],
    [itc[0] + 300, 260, itc[1] + 100], [hk[0] + 260, 380, hk[1] - 60], [hk[0] - 300, 300, hk[1] + 280], [tx[0] - 220, 220, tx[1] + 120],
    [one[0] - 200, 260, one[1] - 260], [one[0] + 250, 200, one[1] + 300], [400, 90, 1700],
    [-2400, 150, 2600], [-4300, -500, 3300], [-3500, -1500, 900], [-1000, -2150, -3800], [3200, -1300, -4800], [6800, 400, -2600], [9500, 1800, 3500]
  ];
}
function cr3(p0, p1, p2, p3, t) { const t2 = t * t, t3 = t2 * t; return [0, 1, 2].map(i => 0.5 * ((2 * p1[i]) + (-p0[i] + p2[i]) * t + (2 * p0[i] - 5 * p1[i] + 4 * p2[i] - p3[i]) * t2 + (-p0[i] + 3 * p1[i] - 3 * p2[i] + p3[i]) * t3)); }
function tourAt(P, u) {
  const n = P.length; u = ((u % n) + n) % n;
  const i = Math.floor(u), t = u - i;
  return cr3(P[(i + n - 1) % n], P[i], P[(i + 1) % n], P[(i + 2) % n], t);
}
export function startTour() {
  S.fly = null; S.follow = null;
  const P = tourPoints();
  S.tour = { P, u: 0.0, speed: 0.055 };
  $("#bTour").setAttribute("aria-pressed", "true"); document.body.classList.add("touring");
}
export function stopTour() {
  if (!S.tour) return;
  const eye = S.eyeNow, tgt = S.tgtNow;
  S.tour = null; $("#bTour").setAttribute("aria-pressed", "false"); document.body.classList.remove("touring");
  if (eye && tgt) adoptView(eye, tgt);
}
function adoptView(eye, tgt) {
  // project look target to ground along the view ray
  const dir = norm3([tgt[0] - eye[0], tgt[1] - eye[1], tgt[2] - eye[2]]);
  let t = dir[1] < -0.05 ? -eye[1] / dir[1] : 1500; t = Math.min(t, 6000);
  const gx = eye[0] + dir[0] * t, gz = eye[2] + dir[2] * t;
  const dx = eye[0] - gx, dz = eye[2] - gz, dist = Math.hypot(dx, eye[1], dz);
  Object.assign(S.cam, { tx: gx, tz: gz, ty: 0, dist, pitch: Math.asin(clamp(eye[1] / dist, -1, 1)), yaw: Math.atan2(dx, dz) });
  clampCam();
}

// per frame: advance tour / fly / orbit and return [eye, target]
export function stepCamera(now, dt) {
  let eye, tgt;
  if (S.tour) {
    S.tour.u += dt * S.tour.speed * (reduceMotion ? 0 : 1);
    eye = tourAt(S.tour.P, S.tour.u * 1.0);
    const ahead = tourAt(S.tour.P, S.tour.u + 0.9);
    const hd = Math.hypot(ahead[0] - eye[0], ahead[2] - eye[2]) || 1;
    tgt = [ahead[0], Math.min(ahead[1], eye[1]) - hd * (0.12 + Math.min(0.35, eye[1] / 4000)), ahead[2]];
  } else if (S.follow) {
    const t = now / 1000, f = S.follow; let obj, back = 120, up = 30;
    if (f.kind === "plane") { obj = AIR.planes[0]; back = 160; up = 35; }
    else if (f.kind === "heli") { obj = AIR.helis[0]; obj.dir = [Math.cos(obj.yaw), 0, Math.sin(obj.yaw)]; back = 60; up = 18; }
    else if (f.kind === "quad") { const q = AIR.quads[0]; obj = q; const a = quadPos(q, q.t + 0.5); q.dir = norm3([a[0] - q.pos[0], 0.0001, a[2] - q.pos[2]]); back = 28; up = 9; }
    else if (f.kind === "blimp") { obj = AIR.blimp; back = 160; up = 30; }
    else if (f.kind === "balloon") { const B = AIR.balloons[0]; obj = B; const a = t * B.w + B.ph; B.dir = norm3([-Math.sin(a) * Math.sign(B.w), 0, Math.cos(a) * Math.sign(B.w)]); back = 70; up = 8; }
    else if (f.kind === "boat") { obj = (AIR.boats || []).find(b => b.type === "ferry") || (AIR.boats || [])[0]; back = 110; up = 30; }
    else if (f.kind === "birds") { const F = AIR.flocks[0]; obj = F; const a = t * F.w + F.ph; F.dir = norm3([Math.cos(a) * F.A[0] * F.w, 0, Math.cos(a * 2 + 1) * 2 * F.A[1] * F.w]); back = 70; up = 22; }
    if (obj && obj.pos) {
      const d = obj.dir || [1, 0, 0];
      const want = [obj.pos[0] - d[0] * back, obj.pos[1] + up, obj.pos[2] - d[2] * back];
      f.sm = f.sm ? f.sm.map((v, i) => lerp(v, want[i], Math.min(1, dt * 2.5))) : (S.eyeNow ? S.eyeNow.slice() : want);
      f.k = Math.min(1, f.k + dt * 0.6);
      eye = f.sm; tgt = [obj.pos[0] + d[0] * 60, obj.pos[1] - 6, obj.pos[2] + d[2] * 60];
    } else { eye = orbitEye(); tgt = [S.cam.tx, S.cam.ty || 0, S.cam.tz]; }
  } else {
    if (S.fly) {
      const f = S.fly, k = Math.min(1, (now - f.t0) / f.ms), e = k < .5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
      for (const key of ["tx", "tz", "yaw", "pitch"]) S.cam[key] = f.from[key] + (f.to[key] - f.from[key]) * e;
      S.cam.ty = lerp(f.from.ty || 0, f.to.ty || 0, e);
      S.cam.dist = Math.exp(Math.log(f.from.dist) + (Math.log(f.to.dist) - Math.log(f.from.dist)) * e);
      if (k >= 1) S.fly = null;
    } else if (S.orbit && !drag && !pinch) S.cam.yaw += dt * 0.06;
    eye = orbitEye(); tgt = [S.cam.tx, S.cam.ty || 0, S.cam.tz];
  }
  if (eye[1] < -1820) eye[1] = -1820;   // stay above the sea of clouds
  { // keep the camera out of the island
    const rr = Math.hypot(eye[0], eye[2]), R0 = isleR(Math.atan2(eye[2], eye[0]));
    if (eye[1] > -5 && eye[1] < 8 && rr < R0) eye[1] = 8;
    else if (eye[1] <= -5) { const lim = R0 * isleScaleAt(eye[1]) * 1.06 + 40; if (rr < lim) { const k = lim / Math.max(rr, 1); eye[0] *= k; eye[2] *= k; } }
  }
  S.eyeNow = eye; S.tgtNow = tgt;
  return [eye, tgt];
}

/* ---------------- input ---------------- */
let drag = null; const pointers = new Map(); let pinch = null;
function userTook() { if (S.tour) stopTour(); if (S.follow) { adoptView(S.eyeNow, S.tgtNow); S.follow = null; } S.fly = null; }
// onClick(x, y): a press without drag (picking); onKey(k): non-camera shortcuts
export function bindInput(canvas, { onClick, onKey }) {
  canvas.addEventListener("contextmenu", e => e.preventDefault());
  canvas.addEventListener("pointerdown", e => {
    canvas.setPointerCapture(e.pointerId);
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.size === 2) {
      userTook();
      const [a, b] = [...pointers.values()];
      pinch = { d: Math.hypot(a.x - b.x, a.y - b.y), ang: Math.atan2(b.y - a.y, b.x - a.x), my: (a.y + b.y) / 2, cam: { ...S.cam } };
      drag = null;
    } else drag = { x: e.clientX, y: e.clientY, sx: e.clientX, sy: e.clientY, rot: e.button === 2 || e.shiftKey || e.button === 1, moved: false };
    canvas.classList.add("dragging");
  });
  canvas.addEventListener("pointermove", e => {
    if (!pointers.has(e.pointerId)) return;
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pinch && pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      const d = Math.hypot(a.x - b.x, a.y - b.y), ang = Math.atan2(b.y - a.y, b.x - a.x), my = (a.y + b.y) / 2;
      S.cam.dist = pinch.cam.dist * pinch.d / Math.max(d, 1); S.cam.yaw = pinch.cam.yaw - (ang - pinch.ang); S.cam.pitch = pinch.cam.pitch + (my - pinch.my) * 0.005;
      clampCam(); return;
    }
    if (!drag) return;
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y; drag.x = e.clientX; drag.y = e.clientY;
    if (!drag.moved && Math.hypot(e.clientX - drag.sx, e.clientY - drag.sy) > 4) { drag.moved = true; userTook(); }
    if (!drag.moved) return;
    if (drag.rot) { S.cam.yaw -= dx * 0.005; S.cam.pitch += dy * 0.004; }
    else {
      const k = S.cam.dist * 0.0018 * (900 / Math.max(600, canvas.clientHeight));
      const cy = Math.cos(S.cam.yaw), sy = Math.sin(S.cam.yaw);
      S.cam.tx += (-dx * cy - dy * sy) * k; S.cam.tz += (dx * sy - dy * cy) * k;
    }
    clampCam();
  });
  const endPointer = e => {
    if (drag && !drag.moved && pointers.size === 1 && e.type === "pointerup") onClick(e.clientX, e.clientY);
    pointers.delete(e.pointerId);
    if (pointers.size < 2) pinch = null;
    if (!pointers.size) { drag = null; canvas.classList.remove("dragging"); }
  };
  canvas.addEventListener("pointerup", endPointer); canvas.addEventListener("pointercancel", endPointer);
  canvas.addEventListener("wheel", e => { e.preventDefault(); userTook(); S.cam.dist *= Math.exp(e.deltaY * 0.0012); clampCam(); }, { passive: false });
  addEventListener("keydown", e => {
    if (e.target.closest && e.target.closest("select,input")) return;
    const k = e.key.toLowerCase(), c = S.cam, step = c.dist * 0.04;
    if (["w", "arrowup", "s", "arrowdown", "a", "arrowleft", "d", "arrowright", "q", "e"].includes(k)) {
      userTook();
      if (k === "w" || k === "arrowup") { c.tx -= Math.sin(c.yaw) * step; c.tz -= Math.cos(c.yaw) * step; }
      else if (k === "s" || k === "arrowdown") { c.tx += Math.sin(c.yaw) * step; c.tz += Math.cos(c.yaw) * step; }
      else if (k === "a" || k === "arrowleft") { c.tx -= Math.cos(c.yaw) * step; c.tz += Math.sin(c.yaw) * step; }
      else if (k === "d" || k === "arrowright") { c.tx += Math.cos(c.yaw) * step; c.tz -= Math.sin(c.yaw) * step; }
      else if (k === "q") c.yaw += 0.08; else if (k === "e") c.yaw -= 0.08;
      clampCam();
    } else onKey(k);
  });
}
export function stopUserMotion() { userTook(); }
