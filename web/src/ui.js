/* Title plate, control rail, info card, loader. Ported from the "build scene" / "camera" UI code of src/city.src.html.
   Labels and the aircraft follow options come with their modules. */
import { centroid } from "./world.js";
import { ZONE_ZH } from "./data.js";
import { S, reduceMotion } from "./state.js";
import { sky, fmtTod } from "./sky.js";
import { HOME, VIEWS, flyTo, startTour, stopTour, stopUserMotion } from "./camera.js";

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
  };
  // Shenzhen local time
  const szHour = (new Date().getUTCHours() + 8 + new Date().getUTCMinutes() / 60) % 24;
  const t0 = szHour < 5 ? szHour + 24 : szHour;
  setTod(Math.round(t0 * 20) / 20, false);
}

// once the scene is built: stats line, coordinates, the fly-to menu
export function fillUI(osm, D, counts) {
  $("#stats").innerHTML = `<b>${fmt(osm.roads.length)}</b> 条 OSM 道路 · <b>${fmt(osm.landmarkCount)}</b> 座真实地标 · <b>${fmt(osm.buildings.length - osm.landmarkCount)}</b> 栋生成楼体（${counts.construct} 处在建） · <b>${counts.falls}</b> 道瀑布 · <b>${counts.islets}</b> 座小浮岛`;
  $("#coords").textContent = `${D.center[0].toFixed(4)}°N ${D.center[1].toFixed(4)}°E · 范围 ${(S.R * 2 / 1000).toFixed(1)}×${(S.R * 2 / 1000).toFixed(1)} km`;
  const sel = $("#selLm");
  const og1 = document.createElement("optgroup"); og1.label = "地标"; sel.appendChild(og1);
  osm.buildings.slice(0, osm.landmarkCount).map((b, i) => [b, i]).sort((a, b) => b[0].h - a[0].h).forEach(([b, i]) => {
    const o = document.createElement("option"); o.value = "b" + i; o.textContent = `${b.name} · ${Math.round(b.h)} m`; og1.appendChild(o);
  });
  const og0 = document.createElement("optgroup"); og0.label = "视角"; sel.insertBefore(og0, og1);
  for (const [v, t] of [["v-isle", "岛屿全景"], ["v-city", "城市俯瞰"], ["v-falls", "深圳湾瀑布"], ["v-under", "岛底仰望"]]) { const o = document.createElement("option"); o.value = v; o.textContent = t; og0.appendChild(o); }
}
