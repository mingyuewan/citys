"""Frame-by-frame demo recorder for 深圳湾空中之岛.
usage: python3 tools/record.py OUTDIR [--test|--bench] [--page index.html]
env: VW, VH, FPS (default 1280x720@30). Encode afterwards, e.g.
  ffmpeg -framerate 24 -i OUTDIR/f_%05d.jpg -c:v libx264 -pix_fmt yuv420p -crf 18 demo.mp4
"""
import base64
import json
import os
import sys
import time

from playwright.sync_api import sync_playwright

OUT = sys.argv[1]
PAGE = os.path.abspath(sys.argv[sys.argv.index("--page") + 1] if "--page" in sys.argv else "index.html")
TEST = "--test" in sys.argv
BENCH = "--bench" in sys.argv
W, H, FPS = int(os.environ.get("VW", 1280)), int(os.environ.get("VH", 720)), int(os.environ.get("FPS", 30))
os.makedirs(OUT, exist_ok=True)

INIT = """
window.SZ_TEST = { scale: 1 };
window.__T = 1000;
(() => {
  const cbs = [];
  window.requestAnimationFrame = cb => { cbs.push(cb); return cbs.length; };
  performance.now = () => window.__T;
  window.__step = ms => { window.__T += ms; const c = cbs.splice(0); for (const f of c) f(window.__T); };
})();
"""

SETUP = r"""
(() => {
  const st = document.createElement("style");
  st.textContent = `#rail,#plate,#card,#loader,#hint{display:none!important}
  #cap{position:fixed;left:56px;bottom:52px;color:#fff;font-family:"Noto Serif CJK SC","Noto Serif CJK TC",serif;text-shadow:0 2px 14px rgba(0,0,0,.55),0 0 2px rgba(0,0,0,.6);pointer-events:none}
  #cap .t{font-size:40px;font-weight:900;letter-spacing:.06em}
  #cap .s{font-family:"Noto Sans CJK SC","Noto Sans CJK TC",sans-serif;font-size:17px;font-weight:500;letter-spacing:.12em;opacity:.9;margin-top:8px}
  #cap .bar{width:42px;height:3px;background:#f2a541;margin-bottom:14px;border-radius:2px}
  #mark{position:fixed;right:40px;bottom:40px;color:rgba(255,255,255,.75);font:500 12px "Noto Sans CJK SC",sans-serif;letter-spacing:.14em;text-shadow:0 1px 6px rgba(0,0,0,.6)}
  #endc{position:fixed;inset:0;display:grid;place-items:center;background:rgba(5,8,14,0);color:#fff;font-family:"Noto Serif CJK SC",serif;pointer-events:none}
  #endc div{text-align:center}#endc .t{font-size:64px;font-weight:900;letter-spacing:.08em}#endc .t span{color:#f2a541}
  #endc .s{font:500 16px "Noto Sans CJK SC",sans-serif;letter-spacing:.3em;margin-top:14px;opacity:.85}
  .lbl.air{display:none}`;
  document.head.appendChild(st);
  const cap = document.createElement("div"); cap.id = "cap"; cap.innerHTML = '<div class="bar"></div><div class="t"></div><div class="s"></div>'; document.body.appendChild(cap);
  const mk = document.createElement("div"); mk.id = "mark"; mk.textContent = "深圳湾 · 空中之岛  ·  道路 © OpenStreetMap"; document.body.appendChild(mk);
  const ec = document.createElement("div"); ec.id = "endc"; ec.innerHTML = '<div><div class="t">深圳湾<span>·</span>空中之岛</div><div class="s">SHENZHEN BAY · FLOATING ISLAND</div></div>'; ec.style.opacity = 0; document.body.appendChild(ec);
  window.__cap = (t, s, a) => { cap.querySelector(".t").textContent = t; cap.querySelector(".s").textContent = s; cap.style.opacity = a; cap.style.transform = `translateY(${(1 - a) * 12}px)`; };
  const ez = k => k < .5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
  const lerp = (a, b, t) => a + (b - a) * t;
  const cam = (o) => { S.fly = null; S.follow = null; S.tour = null; document.body.classList.remove("touring"); Object.assign(S.cam, o); };
  const mix = (A, B, e) => { const o = {}; for (const k in A) o[k] = k === "dist" ? Math.exp(lerp(Math.log(A[k]), Math.log(B[k]), e)) : lerp(A[k], B[k], e); return o; };
  const L = k => D.landmarks.find(l => l.k === k);
  const cr = L("bamboo");
  const G = FALLS.groups.slice().sort((a, b) => b.w - a.w)[0];
  const tower = S.osm.buildings.find(b => !b.landmark && b.zone === "cbd" && b.h > 120 && inIsle(b.x, b.z, 200));
  const tc = Math.cos(tower.ang), ts = Math.sin(tower.ang);
  const SH = AIR.show;
  const showView = { tx: SH.anchor[0] - SH.f[0] * 300, tz: SH.anchor[2] - SH.f[2] * 300, ty: 210, yaw: Math.atan2(-SH.f[0], -SH.f[2]), pitch: 0.1, dist: 1050 };
  const setT = v => { S.tod = S.todTarget = v; };
  window.SHOTS = [
    { sec: 8, t: "深圳湾 · 空中之岛", s: "南山后海 · 真实 OSM 路网与地标",
      init() { setT(15.6); S.rise = 0; S.riseStart = performance.now(); },
      frame(k) { cam(mix({ tx: 0, tz: 0, ty: -500, yaw: -0.25, pitch: 0.62, dist: 20000 }, { tx: 0, tz: 0, ty: -350, yaw: -0.9, pitch: 0.27, dist: 9000 }, ez(k))); } },
    { sec: 7, t: "海水从岛缘倾泻而下", s: "五道瀑布 · 云海 · 漂浮的小岛",
      init() { setT(15.6); S.rise = 1; },
      frame(k) { const yaw = Math.atan2(G.ox, G.oz); cam(mix({ tx: G.x + G.ox * 200, tz: G.z + G.oz * 200, ty: -420, yaw: yaw + 0.75, pitch: 0.16, dist: 4600 }, { tx: G.x + G.ox * 200, tz: G.z + G.oz * 200, ty: -650, yaw: yaw + 0.15, pitch: 0.06, dist: 3100 }, ez(k))); } },
    { sec: 9, t: "越过岛缘，飞入城市", s: "空中漫游",
      init() { setT(15.6); startTour(); S.tour.speed = 0; },
      frame(k) { if (!S.tour) { startTour(); S.tour.speed = 0; } S.tour.u = lerp(2.75, 6.1, k); } },
    { sec: 6, t: "华润大厦「春笋」", s: "392.5 m · 56 道白色肋条",
      init() { setT(13.2); },
      frame(k) { cam({ tx: cr.c[0], tz: cr.c[1], ty: lerp(140, 210, k), yaw: lerp(0.3, 1.5, ez(k)), pitch: lerp(0.18, 0.1, k), dist: lerp(560, 430, k) }); } },
    { sec: 6, t: "街道", s: "车流 · 红绿灯 · 公交站 · 行人",
      init() { setT(12.6); },
      frame(k) { cam({ tx: -326.9 + lerp(-20, 20, k), tz: -671.7, ty: 0, yaw: lerp(0.35, 0.95, ez(k)), pitch: lerp(0.62, 0.5, k), dist: lerp(150, 115, k) }); } },
    { sec: 8, t: "日落 · 华灯初上", s: "时间流转 17:00 → 19:35",
      init() {},
      frame(k) { setT(lerp(16.9, 19.6, k)); cam(mix({ tx: 250, tz: 250, ty: 0, yaw: -0.95, pitch: 0.42, dist: 2700 }, { tx: 450, tz: 350, ty: 0, yaw: -0.45, pitch: 0.3, dist: 2200 }, ez(k))); } },
    { sec: 10, t: "无人机灯光秀", s: "九百架无人机 · 孔明灯升空",
      init() { setT(21); SH.t = 0; },
      frame(k) { cam(mix(showView, { ...showView, yaw: showView.yaw + 0.22, dist: 820, ty: 240 }, ez(k))); } },
    { sec: 5, t: "窗后的房间", s: "夜里亮灯的每一间屋子",
      init() { setT(21.2); },
      frame(k) { cam({ tx: tower.x + ts * (tower.d / 2) + tc * lerp(-12, 12, k), tz: tower.z - tc * (tower.d / 2) + ts * lerp(-12, 12, k), ty: 46, yaw: Math.atan2(ts, -tc) + lerp(0.45, 0.2, k), pitch: 0.05, dist: 48 }); } },
    { sec: 8, t: "夜色中的空中之岛", s: "",
      init() { setT(21.3); },
      frame(k) { cam(mix({ tx: 300, tz: 300, ty: 0, yaw: -0.5, pitch: 0.35, dist: 2300 }, { tx: 0, tz: 0, ty: -350, yaw: -1.05, pitch: 0.25, dist: 9800 }, ez(k))); } },
  ];
  window.__end = a => { ec.style.opacity = a; ec.style.background = `rgba(5,8,14,${a * 0.55})`; };
  return SHOTS.map(s => s.sec);
})()
"""

with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
    pg.set_default_timeout(600000)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    pg.add_init_script(INIT)
    pg.goto("file://" + PAGE)
    pg.wait_for_function("document.querySelector('#loader').hidden", polling=500)
    secs = pg.evaluate(SETUP)
    cdp = pg.context.new_cdp_session(pg)
    # warm up a few frames
    for _ in range(3):
        pg.evaluate("__step(33.333)")
    fno = 0
    t0 = time.time()
    total = sum(int(s * FPS) for s in secs)
    for si, sec in enumerate(secs):
        if BENCH and si not in (3, 6): continue
        n = int(sec * FPS)
        idxs = [0, n // 2, n - 1] if TEST else (range(n // 2, n // 2 + 8) if BENCH else range(n))
        pg.evaluate(f"SHOTS[{si}].init()")
        for i in idxs:
            k = i / max(1, n - 1)
            fade = min(1, i / 18, (n - 1 - i) / 18)
            cap_a = max(0.0, min(1.0, (i - 10) / 14, (n - 1 - i - 8) / 14))
            last = si == len(secs) - 1
            end_a = max(0.0, min(1.0, (i - (n - 60)) / 30)) if last else 0
            pg.evaluate(f"""(() => {{ const s = SHOTS[{si}]; s.frame({k}); __cap(s.t, s.s, {cap_a if not last or end_a == 0 else 0}); __end({end_a}); __step(1000/{FPS}); }})()""")
            shot = cdp.send("Page.captureScreenshot", {"format": "jpeg", "quality": 93})
            fn = f"{OUT}/{'t_%d_%04d' % (si, i) if TEST else 'f_%05d' % fno}.jpg"
            with open(fn, "wb") as fh:
                fh.write(base64.b64decode(shot["data"]))
            fno += 1
            if BENCH and fno == 1: t0 = time.time(); fno0 = 1
            if fno % 30 == 0:
                el = time.time() - t0
                print(f"frame {fno}/{total}  {el / fno:.2f}s/frame  eta {(total - fno) * el / fno / 60:.1f} min", flush=True)
    print("done", fno, "frames", f"{(time.time() - t0) / max(1, fno - 1):.2f}s/frame", errs[:5], flush=True)
    b.close()
