"""Clean screenshots of the web/ page (no UI) for look development.

usage: .venv/bin/python tools/shoot_views.py [--url URL] [--out build/style] [--tag name] [--size 1280x720] [--query "style=..."] [--no-models] [view ...]
Writes <out>/<tag>-<view>.png for the views below. Serve the project root first. env CHROME = Chrome executable.
"""
import os
import sys

from playwright.sync_api import sync_playwright

args = sys.argv[1:]


def opt(name, default):
    if name in args:
        i = args.index(name)
        v = args[i + 1]
        del args[i:i + 2]
        return v
    return default


URL = opt("--url", "http://127.0.0.1:8765/web/index.html")
QUERY = opt("--query", "")
OUT = opt("--out", "build/style")
TAG = opt("--tag", "now")
W, H = (int(v) for v in opt("--size", "1280x720").split("x"))
NO_MODELS = "--no-models" in args   # block web/assets/*.glb: the procedural fallbacks
if NO_MODELS:
    args.remove("--no-models")
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
FAKE = """window.SZ_TEST={scale:1};window.__T=1000;(()=>{const cbs=[];window.requestAnimationFrame=cb=>{cbs.push(cb);return cbs.length;};performance.now=()=>window.__T;window.__step=ms=>{window.__T+=ms;const c=cbs.splice(0);for(const f of c)f(window.__T);};})();"""
VIEWS = {
    "overview": ("HOME()", 15.5),
    "city": ("VIEWS['v-city']()", 15.5),
    "cbd": ("({ tx: -60, tz: -260, ty: 60, yaw: 0.9, pitch: 0.32, dist: 1100 })", 16.4),
    "street": ("({ tx: -326.9, tz: -671.7, ty: 0, yaw: 0.6, pitch: 0.55, dist: 130 })", 12.6),
    "falls": ("VIEWS['v-falls']()", 15.5),
    "dusk": ("VIEWS['v-city']()", 17.3),
    "night": ("VIEWS['v-city']()", 21.0),
    "under": ("VIEWS['v-under']()", 15.5),
    "rock": ("({ tx: -1700, tz: 1700, ty: -650, yaw: -0.785, pitch: 0.05, dist: 2300 })", 15.5),
}
SET = """([v, tod]) => { S.fly = null; S.follow = null; S.tour = null; S.orbit = false; S.rise = 1;
  Object.assign(S.cam, eval(v)); S.tod = S.todTarget = tod; for (let i = 0; i < 6; i++) window.__step(16.7); }"""
os.makedirs(OUT, exist_ok=True)
with sync_playwright() as p:
    br = p.chromium.launch(executable_path=CHROME, headless=True, args=["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist"])
    pg = br.new_page(viewport={"width": W, "height": H})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and "favicon" not in m.text else None)
    pg.add_init_script(FAKE)
    if NO_MODELS:
        pg.route("**/*.glb", lambda r: r.abort())
    pg.goto(URL + ("?" + QUERY if QUERY else ""))
    pg.wait_for_function("() => typeof S !== 'undefined' && S.ready", timeout=240000, polling=500)
    pg.add_style_tag(content="#rail,#plate,#card,#loader,#labels{display:none!important}")
    pg.evaluate("() => { for (let i = 0; i < 10; i++) window.__step(16.7); }")
    for name in (args or VIEWS):
        pg.evaluate(SET, list(VIEWS[name]))
        pg.screenshot(path=os.path.join(OUT, "%s-%s.png" % (TAG, name)))
    br.close()
print("errors:", errs[:5])
