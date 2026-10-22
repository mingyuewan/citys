"""Render shots from blender/shenzhen-bay.blend.

usage:
  Blender -b blender/shenzhen-bay.blend --python tools/blender/render.py -- [SHOT ...] [--res 1600x900] [--samples 96] [--engine CYCLES|EEVEE] [--out renders]
SHOT: overview (page HOME view) | city (CBD close-up around 华润大厦春笋) | falls (bay waterfall)
"""
import math
import os
import sys
import time

import bpy
import mathutils

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def opt(name, default):
    if name in argv:
        i = argv.index(name)
        v = argv[i + 1]
        del argv[i:i + 2]
        return v
    return default


res = opt("--res", "1600x900")
samples = int(opt("--samples", "96"))
engine = opt("--engine", "CYCLES").upper()
outdir = os.path.join(ROOT, opt("--out", "renders"))
suffix = opt("--suffix", "")
shots = argv or ["overview"]
scene = bpy.context.scene
cam = scene.objects["Camera"]


def to_b(p):
    return mathutils.Vector((p[0], -p[2], p[1]))


def orbit(tx, tz, ty, yaw, pitch, dist):
    cp = math.cos(pitch)
    return [tx + math.sin(yaw) * cp * dist, math.sin(pitch) * dist + ty, tz + math.cos(yaw) * cp * dist], [tx, ty, tz]


def look(eye, tgt, fov=0.78):
    e, t = to_b(eye), to_b(tgt)
    cam.location = e
    cam.rotation_euler = (t - e).to_track_quat("-Z", "Y").to_euler()
    cam.data.angle_y = fov


# landmark centre of 华润大厦 (page x, z) — read from the object so the shot follows the data
bamboo = next((o for o in scene.objects if o.name.startswith("LM_00")), None)
bc = bamboo.matrix_world @ (sum((mathutils.Vector(b) for b in bamboo.bound_box), mathutils.Vector()) / 8) if bamboo else mathutils.Vector((0, 0, 0))
bx, bz = bc.x, -bc.y

SHOTS = {
    "overview": lambda: look(*orbit(0, 0, -350, -0.85, 0.28, 9200)),
    "city": lambda: look(*orbit(bx + 120, bz - 60, 120, -0.55, 0.20, 1500), fov=0.62),
    "falls": lambda: look(*orbit(2300, 1900, -650, 0.9, 0.08, 4200)),
}

w, h = (int(v) for v in res.lower().split("x"))
r = scene.render
r.resolution_x, r.resolution_y = w, h
if engine.startswith("EEVEE"):
    r.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items} else "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = samples
else:
    r.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    scene.cycles.threads = 0
os.makedirs(outdir, exist_ok=True)
for s in shots:
    SHOTS[s]()
    bpy.context.view_layer.update()
    path = os.path.join(outdir, "shenzhen-bay-%s%s.png" % (s, suffix))
    r.filepath = path
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print("RENDERED %s  %dx%d  %s  samples=%d  %.1fs" % (path, w, h, r.engine, samples, time.time() - t0))
