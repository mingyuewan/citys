"""Export the page's actual generated geometry for Blender.

Opens the page in headless Chrome (Playwright), waits for buildScene(), then reads the
GPU buffers back with gl.getBufferSubData, so Blender gets exactly the meshes the page draws:
  city (landmarks + generated buildings), bridges, island + islets, sports features,
  road ribbons, waterfall sheets, tree / lamp / parked-car instances, and the ground class map.

usage: .venv/bin/python tools/blender/export_scene.py [URL] [OUTDIR]
  URL    default http://127.0.0.1:8765/index.html  (serve the project root over HTTP)
  OUTDIR default build/blender_export
env: CHROME = path to a Chrome executable (default: /Applications/Google Chrome.app/...)
"""
import base64
import json
import os
import sys
import time

from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/index.html"
OUT = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "build", "blender_export"))
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
os.makedirs(OUT, exist_ok=True)

# Runs in the page. Registers each buffer under a name and returns its byte length.
GRAB = r"""
() => {
  const reg = window.__EXP = {};
  const readBuf = (buf, target, bytes, Ctor) => {
    gl.bindBuffer(target, buf);
    const n = bytes != null ? bytes : gl.getBufferParameter(target, gl.BUFFER_SIZE);
    const out = new Ctor(n / Ctor.BYTES_PER_ELEMENT);
    gl.getBufferSubData(target, 0, out);
    return out;
  };
  const vaoBuf = (vao, loc) => { gl.bindVertexArray(vao); const b = gl.getVertexAttrib(loc, gl.VERTEX_ATTRIB_ARRAY_BUFFER_BINDING); return b; };
  const vaoIdx = vao => { gl.bindVertexArray(vao); return gl.getParameter(gl.ELEMENT_ARRAY_BUFFER_BINDING); };
  const put = (name, arr) => { reg[name] = new Uint8Array(arr.buffer, arr.byteOffset, arr.byteLength); return arr.byteLength; };
  const meta = { landmarkCount: S.osm.landmarkCount, lmIdx: S.lmIdx, R: S.R, isle: ISLE, buildings: [], landmarks: [], meshes: {}, inst: {}, falls: FALLS.groups };
  // 13-float mesh buffers
  for (const [name, m] of [["city", S.city], ["bridge", S.bridge], ["island", S.island], ["feat", S.feat]]) {
    if (!m) continue;
    gl.bindVertexArray(null);
    put(name + "_v", readBuf(m.vb, gl.ARRAY_BUFFER, null, Float32Array));
    gl.bindVertexArray(null);
    put(name + "_i", readBuf(m.ib, gl.ELEMENT_ARRAY_BUFFER, null, Uint32Array));
    meta.meshes[name] = { stride: 13, idx: m.count };
  }
  // roads: 11 floats / vertex, non-indexed triangles
  const rb = vaoBuf(S.roadVAO, 0); gl.bindVertexArray(null);
  put("road_v", readBuf(rb, gl.ARRAY_BUFFER, null, Float32Array));
  meta.meshes.road = { stride: 11, verts: S.roadCount, walk: S.walkCount };
  // waterfalls: 6 floats / vertex
  put("fall_v", new Float32Array(FALLS.v)); meta.meshes.fall = { stride: 6, verts: FALLS.v.length / 6 };
  // tree instances: per instance x, z, scale, hue, y
  S.trees.forEach((T, k) => {
    const b = vaoBuf(T.vao, 3); gl.bindVertexArray(null);
    put("tree" + k, readBuf(b, gl.ARRAY_BUFFER, null, Float32Array));
    meta.inst["tree" + k] = { n: T.n, stride: 5, palm: k === 2 };
  });
  // prop templates + instances (x y z yaw | r g b scaleX)
  for (const [name, I, tpl] of [["lamp", S.lampVAO, TPL.lamp], ["parked", S.parked, TPL.car], ["car", S.carInst, TPL.car], ["signal", S.sigVAO, TPL.signal], ["busstop", S.busVAO, TPL.busstop]]) {
    const b = vaoBuf(I.vao, 4); gl.bindVertexArray(null);
    put(name + "_inst", readBuf(b, gl.ARRAY_BUFFER, null, Float32Array));
    put(name + "_tv", tpl.v); put(name + "_ti", tpl.i);
    meta.inst[name] = { n: I.n, stride: 8, tplStride: 10 };
  }
  // building records (for names in Blender)
  S.osm.buildings.slice(0, S.osm.landmarkCount).forEach((b, i) => meta.landmarks.push({ i, name: b.name, en: b.en, h: b.h, k: b.L.k, c: b.L.c }));
  meta.genCount = S.osm.buildings.length - S.osm.landmarkCount;
  // ground class map (r water, g green, b road) at 4096 + land-use and mask PNGs
  const cv = buildGroundTexture(S.osm, S.R, 4096, window.__mask);
  meta.ground = cv.toDataURL("image/png");
  meta.lu = D.lu; meta.mask = D.mask;
  meta.clouds = S.clouds.puffs.map(p => [p.x, p.y, p.z, p.s, p.lit, p.a, p.fixed ? 1 : 0]);
  meta.islets = ISLETS.map(I => ({ cx: I.cx, cy: I.cy, cz: I.cz, r: I.r, hasFall: I.hasFall }));
  meta.stats = { roads: S.osm.roads.length, landmarks: S.osm.landmarkCount, tris: S.tris };
  gl.bindVertexArray(null);
  const sizes = {}; for (const k in reg) sizes[k] = reg[k].byteLength;
  return { meta, sizes };
}
"""

CHUNK = 8 << 20


def main():
    t0 = time.time()
    with sync_playwright() as p:
        br = p.chromium.launch(executable_path=CHROME, headless=True, args=["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist"])
        pg = br.new_page(viewport={"width": 960, "height": 540})
        pg.on("console", lambda m: print("[page]", m.text) if m.type in ("error", "warning") else None)
        # keep a handle on the mask image the page decodes (buildGroundTexture needs it)
        pg.add_init_script("window.SZ_TEST = { scale: 0.5 };")
        pg.goto(URL)
        pg.wait_for_function("() => typeof S !== 'undefined' && S.ready", timeout=240000)
        pg.evaluate("async () => { window.__mask = await loadMask(); }")
        print("scene ready in %.1fs; renderer: %s" % (time.time() - t0, pg.evaluate(
            "() => { const e = gl.getExtension('WEBGL_debug_renderer_info'); return e ? gl.getParameter(e.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER); }")))
        res = pg.evaluate(GRAB)
        meta, sizes = res["meta"], res["sizes"]
        for name, n in sizes.items():
            with open(os.path.join(OUT, name + ".bin"), "wb") as f:
                for off in range(0, n, CHUNK):
                    b64 = pg.evaluate("([k, o, n]) => { const a = window.__EXP[k].subarray(o, o + n); let s = ''; for (let i = 0; i < a.length; i += 32768) s += String.fromCharCode.apply(null, a.subarray(i, i + 32768)); return btoa(s); }", [name, off, CHUNK])
                    f.write(base64.b64decode(b64))
            print("  %-14s %8.2f MB" % (name, n / 1e6))
        for key, fn in (("ground", "ground.png"), ("lu", "landuse.png"), ("mask", "mask.png")):
            data = meta.pop(key)
            if data.startswith("data:"):
                data = data.split(",", 1)[1]
            with open(os.path.join(OUT, fn), "wb") as f:
                f.write(base64.b64decode(data))
        with open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)
        br.close()
    print("exported to %s in %.1fs" % (OUT, time.time() - t0))


if __name__ == "__main__":
    main()
