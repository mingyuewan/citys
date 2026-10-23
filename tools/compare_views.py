"""Side-by-side screenshots of the old page and the three.js port for the same views (phase 1 parity checks).

usage: .venv/bin/python tools/compare_views.py [--old URL] [--new URL] [--size 1280x720] [--views overview-day,city-day,...]
                                              [--out build/compare] [--no-clouds]
Serve the project root first (python3 -m http.server 8765 --bind 127.0.0.1). Both pages boot with the fake clock of
tools/webgl_check.py; each view is set through the test hooks (S, HOME, VIEWS), then stepped a few frames.
Writes <out>/<view>-old.png, <view>-new.png and <view>-pair.png (old | new), and prints mean luma per image.
--no-clouds hides the old page's cloud puffs (not ported yet) so the two frames differ only by unported layers.
env CHROME = Chrome executable.
"""
import os
import sys
from io import BytesIO

from PIL import Image, ImageDraw, ImageStat
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


OLD = opt("--old", "http://127.0.0.1:8765/index.html")
NEW = opt("--new", "http://127.0.0.1:8765/web/index.html")
SIZE = opt("--size", "1280x720")
OUT = opt("--out", "build/compare")
NO_CLOUDS = "--no-clouds" in args
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
# name → (camera expression, time of day); the six phase-1 acceptance views of docs/handoff.md
ALL_VIEWS = {
    "overview-day": ("HOME()", 15.5),
    "city-day": ("VIEWS['v-city']()", 15.5),
    "falls-day": ("VIEWS['v-falls']()", 15.5),
    "under-day": ("VIEWS['v-under']()", 15.5),
    "street-day": ("({ tx: -326.9, tz: -671.7, ty: 0, yaw: 0.6, pitch: 0.55, dist: 130 })", 12.6),
    "city-night": ("VIEWS['v-city']()", 21.0),
}
VIEWS = [v for v in opt("--views", ",".join(ALL_VIEWS)).split(",") if v]
SETVIEW = """([v, tod, noClouds]) => { S.fly = null; S.follow = null; S.tour = null; S.orbit = false; S.rise = 1;
  if (noClouds) S.showClouds = false;
  Object.assign(S.cam, eval(v)); S.tod = S.todTarget = tod; for (let i = 0; i < 6; i++) window.__step(16.7); }"""


def luma(im):
    return round(ImageStat.Stat(im.convert("L")).mean[0], 1)


def shoot(br, url):
    pg = br.new_page(viewport={"width": W, "height": H})
    errors = []
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" and "favicon" not in m.text else None)
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.add_init_script(FAKE_CLOCK)
    pg.goto(url)
    pg.wait_for_function("() => typeof S !== 'undefined' && S.ready", timeout=240000, polling=500)
    pg.evaluate("() => { for (let i = 0; i < 10; i++) window.__step(16.7); }")
    shots = {}
    for name in VIEWS:
        v, tod = ALL_VIEWS[name]
        pg.evaluate(SETVIEW, [v, tod, NO_CLOUDS])
        pg.wait_for_timeout(700)   # let the day/night panel transition (0.6 s CSS) finish
        shots[name] = Image.open(BytesIO(pg.screenshot())).convert("RGB")
    pg.close()
    return shots, errors


def main():
    os.makedirs(OUT, exist_ok=True)
    with sync_playwright() as p:
        br = p.chromium.launch(executable_path=CHROME, headless=True, args=LAUNCH)
        old, old_err = shoot(br, OLD)
        new, new_err = shoot(br, NEW)
        br.close()
    for name in VIEWS:
        a, b = old[name], new[name]
        a.save(os.path.join(OUT, name + "-old.png"))
        b.save(os.path.join(OUT, name + "-new.png"))
        pair = Image.new("RGB", (W * 2 + 8, H + 28), (20, 20, 24))
        pair.paste(a, (0, 28))
        pair.paste(b, (W + 8, 28))
        d = ImageDraw.Draw(pair)
        d.text((10, 8), "old  " + OLD, fill=(230, 230, 230))
        d.text((W + 18, 8), "new  " + NEW, fill=(230, 230, 230))
        pair.save(os.path.join(OUT, name + "-pair.png"))
        print("%-14s luma old %5.1f  new %5.1f" % (name, luma(a), luma(b)))
    for label, errs in (("old", old_err), ("new", new_err)):
        if errs:
            print("%s page errors:" % label)
            for e in errs[:20]:
                print("  ", e[:400])


if __name__ == "__main__":
    main()
