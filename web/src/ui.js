/* Title plate, control rail, info card, loader. Ported from the "build scene" / "camera" UI code of src/city.src.html.
   Labels and the aircraft follow options come with their modules. */
import { centroid } from "./world.js";
import { ZONE_ZH } from "./data.js";
import { S, reduceMotion } from "./state.js";
import { sky, fmtTod } from "./sky.js";
import { HOME, VIEWS, flyTo, startTour, stopTour, stopUserMotion } from "./camera.js";
import { AIR } from "./air.js";
import { FALLS } from "./island.js";

export const $ = s => document.querySelector(s);
export const fmt = n => n.toLocaleString("zh-CN");
export const sleep = ms => new Promise(r => setTimeout(r, ms));
export const loader = {
  show(title, text, opts = {}) {
    $("#loader").hidden = false; $("#lTitle").textContent = title; $("#lText").textContent = text || "";
    $("#lErr").hidden = !opts.err; $("#lErr").textContent = opts.err || ""; $("#lBar").hidden = !!opts.err;
  },
  hide() { $("#loader").hidden = true; }
};

let lastMode = "";
export function applyModeUI(night) {
  const isNight = night > 0.5, mode = isNight ? "night" : "day";
  if (mode === lastMode) return; lastMode = mode;
  document.documentElement.dataset.mode = mode;
  $("#bMode").setAttribute("aria-pressed", String(isNight));
  $("#bMode").firstChild.textContent = isNight ? "日景 " : "夜景 ";
}
export function setTod(t, animate) { S.todTarget = t; if (!animate) S.tod = t; $("#tod").value = String(t); $("#todOut").textContent = fmtTod(t); }
function toggleMode() { const n = sky(S.todTarget).night > 0.5; setTod(n ? 15.5 : 20.6, true); }
function toggleOrbit() { S.orbit = !S.orbit; $("#bOrbit").setAttribute("aria-pressed", String(S.orbit)); if (S.orbit) { stopTour(); if (S.follow) stopUserMotion(); } }
function toggleTour() { if (S.tour) stopTour(); else startTour(); }
function toggleClouds() { S.showClouds = !S.showClouds; $("#bCloud").setAttribute("aria-pressed", String(S.showClouds)); }
function toggleGen() { S.showGen = !S.showGen; $("#bGen").setAttribute("aria-pressed", String(S.showGen)); if (!S.showGen && S.sel >= (S.osm ? S.osm.landmarkCount : 0)) closeCard(); }
function goHome() { flyTo(HOME(), reduceMotion ? 0 : 2200); }
export function flyToBuilding(i) {
  const b = S.osm.buildings[i]; const c = b.landmark ? b.L.c : centroid(b.ring);
  const low = b.landmark && (b.L.k === "cocoon" || b.L.k === "pebble");
  flyTo({ tx: c[0], tz: c[1], ty: low ? 0 : b.h * 0.45, yaw: S.cam.yaw + 0.5, pitch: low ? 0.5 : 0.22, dist: low ? 700 : Math.max(500, b.h * 2.4) }, reduceMotion ? 0 : 2600);
  showCard(i);
}
function flyTallest() { if (S.tallest >= 0 && S.osm) flyToBuilding(S.tallest); }
export function setPlate(open) {
  $("#plate").classList.toggle("collapsed", !open);
  $("#bPlate").textContent = open ? "收起" : "展开";
  $("#bPlate").setAttribute("aria-expanded", String(open));
  try { localStorage.setItem("szbay.plate", open ? "1" : "0"); } catch (e) {}
}
export function closeCard() { $("#card").hidden = true; S.sel = -1; }
export function showCard(i) {
  const b = S.osm.buildings[i]; S.sel = i;
  const esc = s => String(s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);
  const rows = [];
  if (b.landmark) {
    $("#cName").textContent = b.name;
    rows.push(["高度", `${b.h} m`]); rows.push(["英文名", esc(b.en)]);
    rows.push(["数据", '<span class="est">坐标、高度来自维基百科；外形为按实物简化的示意</span>']);
  } else {
    $("#cName").textContent = "生成楼体";
    rows.push(["高度", `${Math.round(b.h)} m <span class="est">（按片区随机）</span>`]);
    rows.push(["片区", ZONE_ZH[b.zone] || b.zone]); rows.push(["占地", `${fmt(Math.round(b.area))} m²`]);
    rows.push(["数据", '<span class="est">所在街区来自真实 OSM 路网，楼体本身为生成</span>']);
  }
  $("#cList").innerHTML = rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("");
  $("#card").hidden = false;
}
export function onKey(k) {
  if (k === "n") toggleMode(); else if (k === "r") toggleOrbit(); else if (k === "t") flyTallest(); else if (k === "h") goHome();
  else if (k === "g") toggleGen(); else if (k === "f") toggleTour(); else if (k === "c") toggleClouds();
  else if (k === "escape") closeCard();
}

export function initUI() {
  $("#bMode").onclick = toggleMode; $("#bOrbit").onclick = toggleOrbit; $("#bHome").onclick = goHome; $("#bTour").onclick = toggleTour;
  $("#bGen").onclick = toggleGen; $("#bCloud").onclick = toggleClouds; $("#bClose").onclick = closeCard;
  $("#tod").addEventListener("input", e => setTod(+e.target.value, false));
  $("#bPlate").onclick = () => setPlate($("#plate").classList.contains("collapsed"));
  let v = null; try { v = localStorage.getItem("szbay.plate"); } catch (e) {}
  setPlate(v === null ? innerWidth > 760 : v === "1");
  $("#selLm").onchange = e => {
    const v = e.target.value; e.target.value = ""; e.target.blur();
    if (!v) return;
    if (v[0] === "b") { flyToBuilding(+v.slice(1)); return; }
    if (v.startsWith("v-")) { flyTo(VIEWS[v](), reduceMotion ? 0 : 3000); return; }
    stopTour(); S.fly = null;
    if (v === "show") { if (sky(S.todTarget).night < 0.6) setTod(20.6, true); const A = AIR.show.anchor; flyTo({ tx: A[0] - AIR.show.f[0] * 300, tz: A[2] - AIR.show.f[2] * 300, ty: 200, yaw: Math.atan2(-AIR.show.f[0], -AIR.show.f[2]), pitch: 0.12, dist: 900 }, reduceMotion ? 0 : 2600); return; }
    S.follow = { kind: v, k: 0, sm: null };
    closeCard();
  };
  // Shenzhen local time
  const szHour = (new Date().getUTCHours() + 8 + new Date().getUTCMinutes() / 60) % 24;
  const t0 = szHour < 5 ? szHour + 24 : szHour;
  setTod(Math.round(t0 * 20) / 20, false);
}

// once the scene is built: stats line, coordinates, the fly-to menu
export function fillUI(osm, D, counts) {
  const c = counts;
  $("#stats").innerHTML = `<b>${fmt(osm.roads.length)}</b> 条 OSM 道路 · <b>${fmt(osm.landmarkCount)}</b> 座真实地标 · <b>${fmt(osm.buildings.length - osm.landmarkCount)}</b> 栋生成楼体（${c.construct} 处在建） · <b>${fmt(c.trees)}</b> 棵树 · <b>${fmt(c.shrubs)}</b> 丛绿化带灌木 · <b>${c.falls}</b> 道瀑布 · <b>${c.islets}</b> 座小浮岛 · <b>${fmt(c.lamps)}</b> 盏路灯 · <b>${fmt(c.signals)}</b> 组红绿灯 · <b>${c.bus}</b> 个公交站 · <b>${c.features}</b> 处球场、泳池和停车场`;
  $("#coords").textContent = `${D.center[0].toFixed(4)}°N ${D.center[1].toFixed(4)}°E · 范围 ${(S.R * 2 / 1000).toFixed(1)}×${(S.R * 2 / 1000).toFixed(1)} km`;
  const sel = $("#selLm");
  const og1 = document.createElement("optgroup"); og1.label = "地标"; sel.appendChild(og1);
  osm.buildings.slice(0, osm.landmarkCount).map((b, i) => [b, i]).sort((a, b) => b[0].h - a[0].h).forEach(([b, i]) => {
    const o = document.createElement("option"); o.value = "b" + i; o.textContent = `${b.name} · ${Math.round(b.h)} m`; og1.appendChild(o);
  });
  const og0 = document.createElement("optgroup"); og0.label = "视角"; sel.insertBefore(og0, og1);
  for (const [v, t] of [["v-isle", "岛屿全景"], ["v-city", "城市俯瞰"], ["v-falls", "深圳湾瀑布"], ["v-under", "岛底仰望"]]) { const o = document.createElement("option"); o.value = v; o.textContent = t; og0.appendChild(o); }
  const og2 = document.createElement("optgroup"); og2.label = "空中"; sel.appendChild(og2);
  for (const [v, t] of [["plane", "跟随航班"], ["blimp", "跟随飞艇"], ["balloon", "跟随热气球"], ["heli", "跟随直升机"], ["quad", "跟随配送无人机"], ["boat", "跟随渡轮"], ["birds", "跟随白鹭群"], ["show", "无人机灯光秀（夜间）"]]) { const o = document.createElement("option"); o.value = v; o.textContent = t; og2.appendChild(o); }
}

/* ---------------- labels: landmarks, districts, the bay, flights ---------------- */
export function buildLabels(osm, D) {
  const box = $("#labels"); box.textContent = ""; S.labels = [];
  const add = (cls, html, x, y, z, prio, dyn) => {
    const el = document.createElement("div"); el.className = "lbl " + cls; el.innerHTML = html; el.style.opacity = "0"; box.appendChild(el);
    const l = { el, x, y, z, prio, w: 0, h: 0, dyn, isB: cls === "bld" }; S.labels.push(l); return l;
  };
  const esc = s => s.replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const lms = osm.buildings.slice(0, osm.landmarkCount).filter(b => b.h >= 200 || b.L.k === "cocoon").sort((a, b) => b.h - a.h);
  const seen = new Set();
  for (const b of lms) {
    const short = b.name.replace(/[（(].*?[)）]/g, "").replace(/ (南塔|北塔)$/, "");
    if (seen.has(short)) continue; seen.add(short);
    const c = b.L.c;
    add("bld", `${esc(short)}<small>${Math.round(b.h)} m</small>`, c[0], b.h + 8, c[1], b.L.k === "cocoon" ? 2 : 3);
  }
  for (const l of D.labels) add(l.k === "sea" ? "sea" : "area", esc(l.n), l.x, l.k === "sea" ? 5 : 25, l.z, l.k === "sea" ? 5 : 1);
  S.airLabels = AIR.planes.map(p => add("air", `✈ ${p.name}`, 0, 0, 0, 4, true));
  S.labelOrder = S.labels.slice().sort((a, b) => b.prio - a.prio);
  requestAnimationFrame(() => S.labels.forEach(l => { l.w = l.el.offsetWidth; l.h = l.el.offsetHeight; }));
}
// vp: view-projection (column-major elements), cw/ch: canvas CSS size
export function placeLabels(vp, eye, cw, ch) {
  AIR.planes.forEach((p, i) => { const l = S.airLabels[i]; if (p.pos && l) { l.x = p.pos[0]; l.y = p.pos[1] + 6; l.z = p.pos[2]; } });
  const m = vp, placed = [];
  for (const l of S.labelOrder) {
    const y = l.dyn ? l.y : l.y * S.rise;
    const w = m[3] * l.x + m[7] * y + m[11] * l.z + m[15];
    const px = (m[0] * l.x + m[4] * y + m[8] * l.z + m[12]) / w, py = (m[1] * l.x + m[5] * y + m[9] * l.z + m[13]) / w, pz = (m[2] * l.x + m[6] * y + m[10] * l.z + m[14]) / w;
    let vis = w > 0 && px > -1.05 && px < 1.05 && py > -1.05 && py < 1.05 && pz < 1 && S.rise > 0.9;
    const sx = (px * 0.5 + 0.5) * cw, sy = (1 - (py * 0.5 + 0.5)) * ch;
    const d = Math.hypot(eye[0] - l.x, eye[1] - y, eye[2] - l.z);
    const isB = l.isB, isAir = l.dyn;
    if (vis && isB && d > S.R * 4.2) vis = false;
    if (vis && !isAir && eye[1] < -20) vis = false;
    if (vis && isAir && d > 5200) vis = false;
    if (vis) {
      const isC = !isB && !isAir;
      const bx = { x0: sx - l.w / 2, x1: sx + l.w / 2, y0: isC ? sy - l.h / 2 : sy - l.h, y1: isC ? sy + l.h / 2 : sy };
      if (placed.some(q => bx.x0 < q.x1 && bx.x1 > q.x0 && bx.y0 < q.y1 && bx.y1 > q.y0)) vis = false; else placed.push(bx);
    }
    l.el.style.opacity = vis ? "" : "0";
    if (vis) l.el.style.transform = `translate(${sx.toFixed(1)}px, ${sy.toFixed(1)}px) translate(-50%, ${isB ? "-100%" : isAir ? "-150%" : "-50%"})`;
  }
}
// the "空中" status line, twice a second
export function skyStatus(now) {
  if (S._skyT && now - S._skyT <= 500) return;
  S._skyT = now;
  const items = [`热气球 ${(AIR.balloons || []).length}`, `飞艇 1`, `瀑布 ${FALLS.groups.length} 道`, `船 ${(AIR.boats || []).length} 艘`, `塔吊 ${(AIR.cranes || []).length} 台`, `✈ 航班 ${AIR.planes.length}`, `🚁 直升机 ${AIR.helis.length}`, `白鹭 ${AIR.flocks.reduce((a, f) => a + f.n, 0)} 只`, `配送无人机 ${AIR.quads.length}`];
  if (AIR.show.active) items.push(`<b>灯光秀进行中 · ${AIR.show.N} 架 · 孔明灯升空</b>`); else items.push("灯光秀与孔明灯 19:00 后开始");
  $("#sky").innerHTML = "空中：" + items.join(" · ");
}
