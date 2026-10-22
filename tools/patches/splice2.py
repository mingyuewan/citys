import sys

p = sys.argv[1]
src = open(p, encoding="utf-8").read()


def rep(a, b, count=1):
    global src
    assert a in src, a[:80]
    src = src.replace(a, b, count)


def cut(start_marker, end_marker, replacement):
    global src
    a = src.index(start_marker)
    b = src.index(end_marker, a)
    src = src[:a] + replacement + src[b:]


rep('  label[for="selR"] { display: none; }\n', '')
rep('  R: RADIUS, rise: 0, riseStart: 0,', '  R: D.R, rise: 0, riseStart: 0, showGen: true, lmIdx: 0,')

# buildCity: remember where landmark geometry ends
rep('''    const t = triangulate(r);
    for (const k of t) I[ii++] = base + k;
  });
  return { V: V.subarray(0, v * 12), I: I.subarray(0, ii) };''', '''    const t = triangulate(r);
    for (const k of t) I[ii++] = base + k;
    if (bid === osm.landmarkCount - 1) lmEnd = ii;
  });
  return { V: V.subarray(0, v * 12), I: I.subarray(0, ii), lmEnd };''')
rep('  let v = 0, ii = 0;\n  const push', '  let v = 0, ii = 0, lmEnd = 0;\n  const push')
# landmark colours: glass for towers, warm white for the two low "cocoon" structures
rep('''    if (b.h >= 90) { const t = hash1(b.id * 1.7); c = [0.55 + 0.1 * t, 0.66 + 0.06 * t, 0.74 + 0.04 * t]; } // glass towers''',
    '''    if (b.h >= 90) { const t = hash1(b.id * 1.7); c = [0.55 + 0.1 * t, 0.66 + 0.06 * t, 0.74 + 0.04 * t]; } // glass towers
    if (b.landmark && b.h >= 90) c = [0.62, 0.72, 0.80];
    if (b.dome) c = [0.95, 0.94, 0.90];''')

cut('async function buildScene(data) {', '  const bridges = buildBridges(osm);', '''async function buildScene(maskImg) {
  loader.show("正在搭建深圳湾", `${fmt(D.roads.length)} 条道路 · ${fmt(D.buildings.length + D.landmarks.length)} 栋楼`);
  await sleep(30);
  const osm = decodeData(D);
  S.osm = osm;
  S.ready = false;
  disposeScene();

''')
rep('''  S.city = meshVAO(city.V, city.I);''', '''  S.city = meshVAO(city.V, city.I); S.lmIdx = city.lmEnd;''')
rep('''  loader.show("正在绘制地面", "海岸线、绿地与道路");''', '''  loader.show("正在绘制地面", "海岸、绿地与道路");''')
rep('const cv = buildGroundTexture(osm, S.R, TS);', 'const cv = buildGroundTexture(osm, S.R, TS, maskImg);')
rep('''  const known = osm.buildings.filter(b => b.known).length;
  $("#stats").innerHTML = `<b>${fmt(osm.buildings.length)}</b> 栋建筑 · <b>${fmt(osm.roads.length)}</b> 条道路 · 车流 <b>${fmt(S.traffic.cars.length)}</b><br>其中 <b>${fmt(known)}</b> 栋有实测高度/层数，其余为估算`;''',
    '''  $("#stats").innerHTML = `<b>${fmt(osm.roads.length)}</b> 条 OSM 道路 · <b>${fmt(osm.landmarkCount)}</b> 座真实地标 · <b>${fmt(osm.buildings.length - osm.landmarkCount)}</b> 栋生成楼体`;
  const sel = $("#selLm");
  osm.buildings.slice(0, osm.landmarkCount).map((b, i) => [b, i]).sort((a, b) => b[0].h - a[0].h).forEach(([b, i]) => {
    const o = document.createElement("option"); o.value = String(i); o.textContent = `${b.name} · ${Math.round(b.h)} m`; sel.appendChild(o);
  });''')

cut('function buildLabels(osm) {', '/* ---------------- Camera & input', '''function buildLabels(osm) {
  const box = $("#labels"); box.textContent = ""; S.labels = [];
  const add = (cls, html, x, y, z, prio) => {
    const el = document.createElement("div"); el.className = "lbl " + cls; el.innerHTML = html; el.style.opacity = "0"; box.appendChild(el);
    S.labels.push({ el, x, y, z, prio, w: 0, h: 0 });
  };
  const esc = s => s.replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const lms = osm.buildings.slice(0, osm.landmarkCount).filter(b => b.h >= 200 || b.dome).sort((a, b) => b.h - a.h);
  const seen = new Set();
  for (const b of lms) {
    const short = b.name.replace(/[（(].*?[)）]/g, "").replace(/ (南塔|北塔)$/, "");
    if (seen.has(short)) continue; seen.add(short);
    const c = centroid(b.ring);
    add("bld", `${esc(short)}<small>${Math.round(b.h)} m</small>`, c[0], b.h + 6, c[1], b.dome ? 2 : 3);
  }
  for (const l of D.labels) add(l.k === "sea" ? "sea" : "area", esc(l.n), l.x, l.k === "sea" ? 5 : 25, l.z, l.k === "sea" ? 5 : 1);
  requestAnimationFrame(() => S.labels.forEach(l => { l.w = l.el.offsetWidth; l.h = l.el.offsetHeight; }));
}

''')

# controls
rep('''if (k === "n") toggleMode(); else if (k === "r") toggleOrbit(); else if (k === "t") flyTallest(); else if (k === "h") goHome();''',
    '''if (k === "n") toggleMode(); else if (k === "r") toggleOrbit(); else if (k === "t") flyTallest(); else if (k === "h") goHome(); else if (k === "g") toggleGen();''')
rep('''$("#bMode").onclick = toggleMode; $("#bOrbit").onclick = toggleOrbit; $("#bTall").onclick = flyTallest; $("#bHome").onclick = goHome;''',
    '''$("#bMode").onclick = toggleMode; $("#bOrbit").onclick = toggleOrbit; $("#bHome").onclick = goHome;
function toggleGen() { S.showGen = !S.showGen; $("#bGen").setAttribute("aria-pressed", String(S.showGen)); if (!S.showGen && S.sel >= (S.osm ? S.osm.landmarkCount : 0)) closeCard(); }
$("#bGen").onclick = toggleGen;
function flyToBuilding(i) {
  const b = S.osm.buildings[i]; const c = centroid(b.ring);
  flyTo({ tx: c[0], tz: c[1], yaw: S.cam.yaw + 0.5, pitch: b.dome ? 0.55 : 0.42, dist: Math.max(520, b.h * 3.0) }, reduceMotion ? 0 : 2400);
  showCard(i);
}
$("#selLm").onchange = e => { if (e.target.value !== "") flyToBuilding(+e.target.value); e.target.value = ""; e.target.blur(); };''')
cut('function flyTallest() {', '$("#bMode").onclick', '''function flyTallest() { if (S.tallest >= 0 && S.osm) flyToBuilding(S.tallest); }
''')
rep('function goHome() { flyTo({ tx: 0, tz: 150, yaw: S.cam.yaw, pitch: 0.62, dist: S.R * 1.25 }, reduceMotion ? 0 : 1800); }',
    'function goHome() { flyTo(HOME(), reduceMotion ? 0 : 1800); }\nconst HOME = () => ({ tx: 350, tz: 250, yaw: -0.75, pitch: 0.6, dist: S.R * 1.05 });')
rep('''  flyTo({ tx: 0, tz: 150, yaw: -0.62, pitch: 0.62, dist: S.R * 1.25 }, reduceMotion ? 0 : 4200);''',
    '''  flyTo(HOME(), reduceMotion ? 0 : 4200);''')

# draw: skip generated buildings when hidden (pick + main)
rep('''  gl.bindVertexArray(S.city.vao); gl.drawElements(gl.TRIANGLES, S.city.count, gl.UNSIGNED_INT, 0);
  if (S.bridge) { gl.bindVertexArray(S.bridge.vao); gl.drawElements(gl.TRIANGLES, S.bridge.count, gl.UNSIGNED_INT, 0); }
  const r = canvas''', '''  gl.bindVertexArray(S.city.vao); gl.drawElements(gl.TRIANGLES, S.showGen ? S.city.count : S.lmIdx, gl.UNSIGNED_INT, 0);
  if (S.bridge) { gl.bindVertexArray(S.bridge.vao); gl.drawElements(gl.TRIANGLES, S.bridge.count, gl.UNSIGNED_INT, 0); }
  const r = canvas''')
rep('''  gl.bindVertexArray(S.city.vao); gl.drawElements(gl.TRIANGLES, S.city.count, gl.UNSIGNED_INT, 0);
  if (S.bridge) { gl.bindVertexArray(S.bridge.vao); gl.drawElements(gl.TRIANGLES, S.bridge.count, gl.UNSIGNED_INT, 0); }

  // traffic''', '''  gl.bindVertexArray(S.city.vao); gl.drawElements(gl.TRIANGLES, S.showGen ? S.city.count : S.lmIdx, gl.UNSIGNED_INT, 0);
  if (S.bridge) { gl.bindVertexArray(S.bridge.vao); gl.drawElements(gl.TRIANGLES, S.bridge.count, gl.UNSIGNED_INT, 0); }

  // traffic''')

# info card
cut('const TYPE_ZH = {', '/* ---------------- Render loop', '''function showCard(i) {
  const b = S.osm.buildings[i]; S.sel = i;
  const esc = s => String(s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);
  const rows = [];
  if (b.landmark) {
    $("#cName").textContent = b.name;
    rows.push(["高度", `${b.h} m`]);
    rows.push(["英文名", esc(b.en)]);
    rows.push(["数据", '<span class="est">坐标、高度来自维基百科；体块轮廓为示意</span>']);
  } else {
    $("#cName").textContent = "生成楼体";
    rows.push(["高度", `${Math.round(b.h)} m <span class="est">（按片区随机）</span>`]);
    rows.push(["片区", ZONE_ZH[b.zone] || b.zone]);
    rows.push(["占地", `${fmt(Math.round(b.area))} m²`]);
    rows.push(["数据", '<span class="est">所在街区来自真实 OSM 路网，楼体本身为生成</span>']);
  }
  $("#cList").innerHTML = rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("");
  $("#card").hidden = false;
}

''')

# loading flow
a = src.index('/* ---------------- Loading flow')
b = src.index('</script>', a)
src = src[:a] + '''/* ---------------- Boot ---------------- */
(async () => {
  try {
    const mask = await loadMask();
    await buildScene(mask);
  } catch (e) {
    console.error(e);
    loader.show("加载失败", "内置数据读取出错，请刷新页面重试。", { actions: true, err: e.message || String(e) });
  }
})();
''' + src[b:]

open(p, "w", encoding="utf-8").write(src)
print("ok")
