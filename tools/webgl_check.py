"""WebGL smoke test + A/B frame-time benchmark for the page (headless Chrome via Playwright).

usage: .venv/bin/python tools/webgl_check.py [URL ...] [--size 1280x720] [--frames 60] [--shots DIR] [--dynres] [--fallbacks]
  URL defaults to http://127.0.0.1:8765/index.html (serve the project root over HTTP; file:// is not used)
For each URL: boots with a fake clock (like tools/record.py), checks console errors, render-target mode, shadow size,
non-black output for day/night views, picking, canvas resizes; then times N frames per view
(each frame: tick + 1-pixel readPixels to wait for the GPU). With --dynres it also runs the real
requestAnimationFrame loop for 40 s under two synthetic loads (pixel-proportional; periodic spikes).
With --fallbacks it forces "no MSAA for RGBA16F" / "no MSAA at all" via getInternalformatParameter and
simulates a context loss with WEBGL_lose_context (new page only). and counts render-target reallocations.
env CHROME = Chrome executable.
"""
import json
import os
import statistics
import sys
import time

from playwright.sync_api import sync_playwright

CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
args = sys.argv[1:]


def opt(name, default):
    if name in args:
        i = args.index(name)
        v = args[i + 1]
        del args[i:i + 2]
        return v
    return default


SIZE = opt("--size", "1280x720")
FRAMES = int(opt("--frames", "60"))
SHOTS = opt("--shots", "")
DYNRES = "--dynres" in args
if DYNRES:
    args.remove("--dynres")
FALLBACKS = "--fallbacks" in args
if FALLBACKS:
    args.remove("--fallbacks")
URLS = args or ["http://127.0.0.1:8765/index.html"]
W, H = (int(v) for v in SIZE.split("x"))
LAUNCH = ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist", "--enable-unsafe-swiftshader"]

FAKE_CLOCK = """
window.SZ_TEST = { scale: 1 };
window.__T = 1000;
(() => {
  const cbs = [];
  window.requestAnimationFrame = cb => { cbs.push(cb); return cbs.length; };
  performance.now = () => window.__T;
  window.__step = ms => { window.__T += ms; const c = cbs.splice(0); for (const f of c) f(window.__T); };
})();
"""

VIEWS = {
    "overview-day": ("HOME()", 15.5),
    "city-day": ("VIEWS['v-city']()", 15.5),
    "city-night": ("VIEWS['v-city']()", 21.0),
    "street-day": ("({ tx: -326.9, tz: -671.7, ty: 0, yaw: 0.6, pitch: 0.55, dist: 130 })", 12.6),
}

SETVIEW = """([v, tod]) => { S.fly = null; S.follow = null; S.tour = null; S.orbit = false; S.rise = 1;
  Object.assign(S.cam, eval(v)); S.tod = S.todTarget = tod; for (let i = 0; i < 4; i++) window.__step(16.7); }"""

TIME = """(n) => { const px = new Uint8Array(4), ts = [];
  for (let i = 0; i < n; i++) { const t0 = Date.now(); window.__step(16.7); gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px); ts.push(Date.now() - t0); }
  return ts; }"""

INFO = """() => ({
  rt: typeof RT !== 'undefined' ? (RT.mode || ((typeof floatRT !== 'undefined' && floatRT ? 'RGBA16F' : 'RGBA8') + ' MSAA×' + RT.samples)) : '?',
  w: canvas.width, h: canvas.height, sm: SM.size, smOn: SM.on !== false,
  tex: typeof TEX !== 'undefined' ? { rock: !!TEX.rock, facade: !!TEX.facade, cloud: !!TEX.cloud } : null,
  glErr: gl.getError(), maxSamples: gl.getParameter(gl.MAX_SAMPLES),
  f16Samples: Array.from(gl.getInternalformatParameter(gl.RENDERBUFFER, gl.RGBA16F, gl.SAMPLES) || []),
  renderer: (() => { const e = gl.getExtension('WEBGL_debug_renderer_info'); return e ? gl.getParameter(e.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER); })() })"""


def mean_luma(png_bytes):
    from io import BytesIO

    from PIL import Image, ImageStat
    im = Image.open(BytesIO(png_bytes)).convert("L")
    return ImageStat.Stat(im).mean[0]


def run(url, br):
    rep = {"url": url, "errors": [], "views": {}, "checks": {}}
    pg = br.new_page(viewport={"width": W, "height": H})
    pg.on("console", lambda m: rep["errors"].append(m.text) if m.type == "error" and "favicon" not in m.text else None)
    pg.on("pageerror", lambda e: rep["errors"].append(str(e)))
    pg.add_init_script(FAKE_CLOCK)
    t0 = time.time()
    pg.goto(url)
    pg.wait_for_function("() => typeof S !== 'undefined' && S.ready", timeout=240000, polling=500)
    rep["boot_s"] = round(time.time() - t0, 1)
    pg.evaluate("() => { for (let i = 0; i < 10; i++) window.__step(16.7); }")
    rep["info"] = pg.evaluate(INFO)
    tag = "new" if "baseline" not in url else "baseline"
    for name, (v, tod) in VIEWS.items():
        pg.evaluate(SETVIEW, [v, tod])
        pg.evaluate(TIME, 15)   # warm-up
        ts = pg.evaluate(TIME, FRAMES)
        png = pg.screenshot()
        luma = mean_luma(png)
        if SHOTS:
            os.makedirs(SHOTS, exist_ok=True)
            open(os.path.join(SHOTS, "%s-%s-%dx%d.png" % (tag, name, W, H)), "wb").write(png)
        rep["views"][name] = {"median_ms": statistics.median(ts), "mean_ms": round(statistics.mean(ts), 2), "p90_ms": sorted(ts)[int(len(ts) * 0.9)], "luma": round(luma, 1)}
    # picking: click the tallest landmark's screen position (should open the info card)
    pg.evaluate(SETVIEW, ["VIEWS['v-city']()", 15.5])
    xy = pg.evaluate("""() => { const b = S.osm.buildings[S.tallest], c = b.L ? b.L.c : [b.x, b.z]; const p = M.xf(frame.vp, c[0], b.h * 0.5, c[1]);
      const r = canvas.getBoundingClientRect(); return [r.left + (p[0] * 0.5 + 0.5) * r.width, r.top + (1 - (p[1] * 0.5 + 0.5)) * r.height, b.name]; }""")
    pg.evaluate("([x, y]) => pick(x, y)", xy[:2])
    rep["checks"]["pick"] = pg.evaluate("() => ({ sel: S.sel, card: !$('#card').hidden, name: $('#cName').textContent })")
    rep["checks"]["pick"]["expected"] = xy[2]
    # resize: canvas follows the window, render targets follow
    sizes = []
    for vw, vh in ((800, 600), (390, 844), (1600, 900), (W, H)):
        pg.set_viewport_size({"width": vw, "height": vh})
        pg.evaluate("() => new Promise(r => setTimeout(r, 120))")
        pg.evaluate("() => { for (let i = 0; i < 3; i++) window.__step(16.7); }")
        info = pg.evaluate("() => ({ w: canvas.width, h: canvas.height, rtw: RT.w, rth: RT.h, err: gl.getError() })")
        luma = mean_luma(pg.screenshot())
        sizes.append({"viewport": [vw, vh], **info, "luma": round(luma, 1)})
    rep["checks"]["resize"] = sizes
    pg.close()
    if DYNRES:
        # real requestAnimationFrame with synthetic per-frame CPU load; count render-target reallocations in 40 s.
        #  fill: load proportional to canvas pixels (≈45 ms/frame at full size) → controller must settle
        #  spiky: 2.5 s of 55 ms frames every 8 s, otherwise 4 ms → passing hitches should not cause resize churn
        loads = {
            "fill": "const c = document.getElementById('gl'); const ms = 45 * (c && c.width > 1 ? c.width * c.height / (%d * %d) : 1);" % (W, H),
            "spiky": "const ms = performance.now() % 8000 < 2500 ? 55 : 4;",
        }
        for lname, js in loads.items():
            pg = br.new_page(viewport={"width": W, "height": H})
            pg.on("pageerror", lambda e: rep["errors"].append(str(e)))
            pg.add_init_script("""(() => { const raf = window.requestAnimationFrame.bind(window);
              window.requestAnimationFrame = cb => raf(t => { %s const e = performance.now() + ms; while (performance.now() < e) {} cb(t); }); })();""" % js)
            pg.goto(url)
            pg.wait_for_function("() => typeof S !== 'undefined' && S.ready", timeout=240000, polling=500)
            pg.evaluate("""() => { window.__realloc = []; const orig = setupRT; window.setupRT = (w, h) => { if (RT.w !== w || RT.h !== h) window.__realloc.push([Math.round(performance.now()), w, h]); return orig(w, h); }; }""")
            pg.evaluate("() => new Promise(r => setTimeout(r, 40000))")
            rep["checks"]["dynres_40s_" + lname] = pg.evaluate("() => ({ reallocations: window.__realloc.length, sizes: window.__realloc.map(a => a[1] + 'x' + a[2]), scale: PERF.scale })")
            pg.close()
    if FALLBACKS:
        for label, deny in (("no_f16_msaa", "fmt === 0x881A"), ("no_msaa", "true")):
            pg = br.new_page(viewport={"width": W, "height": H})
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.add_init_script(FAKE_CLOCK + """(() => { const o = WebGL2RenderingContext.prototype.getInternalformatParameter;
              WebGL2RenderingContext.prototype.getInternalformatParameter = function (t, fmt, p) { if (p === this.SAMPLES && (%s)) return new Int32Array(0); return o.call(this, t, fmt, p); }; })();""" % deny)
            pg.goto(url)
            pg.wait_for_function("() => typeof S !== 'undefined' && S.ready", timeout=240000, polling=500)
            pg.evaluate(SETVIEW, ["VIEWS['v-city']()", 15.5])
            rep["checks"]["fallback_" + label] = {"rt": pg.evaluate("() => RT.mode"), "glErr": pg.evaluate("() => gl.getError()"),
                                                  "luma": round(mean_luma(pg.screenshot()), 1), "errors": errs}
            pg.close()
        pg = br.new_page(viewport={"width": W, "height": H})
        pg.add_init_script(FAKE_CLOCK)
        pg.goto(url)
        pg.wait_for_function("() => typeof S !== 'undefined' && S.ready", timeout=240000, polling=500)
        pg.evaluate("() => { window.__reloaded = false; window.__lc = gl.getExtension('WEBGL_lose_context'); window.__lc.loseContext(); }")
        pg.wait_for_timeout(300)
        lost = pg.evaluate("() => ({ lost: CTX.lost, loader: !$('#loader').hidden, title: $('#lTitle').textContent })")
        try:
            with pg.expect_navigation(timeout=15000):
                pg.evaluate("() => window.__lc.restoreContext()")
            pg.wait_for_function("() => typeof S !== 'undefined' && S.ready", timeout=240000, polling=500)
            restored = "reloaded and rebuilt"
        except Exception as e:  # noqa: BLE001
            restored = "failed: %s" % e
        rep["checks"]["context_loss"] = {"on_lost": lost, "on_restore": restored}
        pg.close()
    return rep


def main():
    out = []
    with sync_playwright() as p:
        br = p.chromium.launch(executable_path=CHROME, headless=True, args=LAUNCH)
        for u in URLS:
            r = run(u, br)
            out.append(r)
            print(json.dumps(r, ensure_ascii=False, indent=1))
        br.close()
    if len(out) == 2:
        print("\nA/B (median ms per frame, %dx%d, %d frames):" % (W, H, FRAMES))
        for v in VIEWS:
            a, b = out[0]["views"][v]["median_ms"], out[1]["views"][v]["median_ms"]
            print("  %-14s %6.1f -> %6.1f ms" % (v, a, b))


if __name__ == "__main__":
    main()
