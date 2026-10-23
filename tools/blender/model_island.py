"""Floating-island rock body for the page (phase 3): layered sandstone / slate strata with overhanging ledges,
gullies and hanging spires, colours and ambient occlusion baked into the vertex colours, exported as glTF.

usage: Blender -b --factory-startup --python tools/blender/model_island.py -- data/szbay.json web/assets/island.glb [--blend out.blend]

The top rim follows the page's isleR(θ) exactly (world.js: keep ISLE_* below in sync), and is lowered where the bay
spills over it (the page's water mask), so the ground plane, roads and waterfall sheets still meet it. The radial
profile follows ISLE_PROF (island.js), which the page also uses for camera collision.
Coordinates: Blender (X, Y, Z) = page (x, -z, y); exported with +Y up, so the glb is in page coordinates.
Node "ISLAND_body"; materials "M11_grass" (lip) and "M10_rock" (page material ids 11 and 10).
"""
import base64
import json
import math
import os
import sys
import tempfile

import bmesh
import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
DATA, OUT = argv[0], argv[1]
BLEND = argv[argv.index("--blend") + 1] if "--blend" in argv else None
D = json.load(open(DATA, encoding="utf-8"))

# ---- island outline: same as web/src/world.js (ISLE, ISLE_WAVES, ISLE_LOBE_W, ISLE_SOFT)
R0, WAVES, LOBE_W, SOFT = 2850.0, [(0.05, 3, 1), (0.035, 5, 2), (0.02, 9, 0.5), (0.012, 17, 3.1)], 0.16, 60.0
hk = next(l for l in D["landmarks"] if l["k"] == "hanking")
TH_H, LOBE = math.atan2(hk["c"][1], hk["c"][0]), math.hypot(hk["c"][0], hk["c"][1]) + 75


def isle_r(th):
    w = 1.0 + sum(a * np.sin(f * th + p) for a, f, p in WAVES)
    b = R0 * w
    d = (th - TH_H + np.pi) % (2 * np.pi) - np.pi
    lo = LOBE * np.exp(-(d / LOBE_W) ** 2)
    m = np.maximum(b, lo)
    return m + SOFT * np.log(np.exp((b - m) / SOFT) + np.exp((lo - m) / SOFT))


# ---- radial profile: web/src/island.js ISLE_PROF [y, scale]
PROF = np.array([[0.6, 1.0], [-6, 1.014], [-24, 1.004], [-62, 0.99], [-140, 0.955], [-290, 0.905], [-500, 0.83], [-760, 0.73],
                 [-1040, 0.61], [-1340, 0.48], [-1640, 0.35], [-1940, 0.23], [-2230, 0.13], [-2480, 0.055], [-2640, 0.0]])


def prof_scale(y):
    return np.interp(-y, -PROF[:, 0], PROF[:, 1])


# ---- the bay: water mask, sampled as the page does (island.js makeWater: point at 0.982 of the rim)
def water_mask():
    fd, path = tempfile.mkstemp(suffix=".png"); os.close(fd)
    open(path, "wb").write(base64.b64decode(D["mask"]))
    im = bpy.data.images.load(path)
    w, h = im.size
    px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, im.channels)[::-1, :, 0]   # rows top-down, as the canvas
    os.remove(path)
    R = D["R"]
    def at(x, z):
        i = np.clip(np.floor((x + R) / (2 * R) * w).astype(int), 0, w - 1); j = np.clip(np.floor((z + R) / (2 * R) * h).astype(int), 0, h - 1)
        return px[j, i] > 0.5
    return at


# ---- value noise (3D, smooth), fbm, hashing
def hash3(i, j, k):
    n = np.sin(i * 127.1 + j * 311.7 + k * 74.7) * 43758.5453
    return n - np.floor(n)


def vnoise3(x, y, z):
    i, j, k = np.floor(x), np.floor(y), np.floor(z)
    fx, fy, fz = x - i, y - j, z - k
    ux, uy, uz = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy), fz * fz * (3 - 2 * fz)
    c = lambda a, b, d: hash3(i + a, j + b, k + d)
    x00 = c(0, 0, 0) + (c(1, 0, 0) - c(0, 0, 0)) * ux; x10 = c(0, 1, 0) + (c(1, 1, 0) - c(0, 1, 0)) * ux
    x01 = c(0, 0, 1) + (c(1, 0, 1) - c(0, 0, 1)) * ux; x11 = c(0, 1, 1) + (c(1, 1, 1) - c(0, 1, 1)) * ux
    y0 = x00 + (x10 - x00) * uy; y1 = x01 + (x11 - x01) * uy
    return y0 + (y1 - y0) * uz


def fbm(x, y, z, oct=4):
    s, a, f = 0.0, 0.5, 1.0
    for _ in range(oct):
        s = s + a * vnoise3(x * f, y * f, z * f); f *= 2.03; a *= 0.5
    return s / (1 - 0.5 ** oct)


# strata: bands of varying thickness, wavy along the rim; returns band index and position in band (0 bottom … 1 top)
def strata(px, y, pz):
    wav = (fbm(px * 0.0016, y * 0.0005, pz * 0.0016, 3) - 0.5) * 70
    thick = 72 + 55 * fbm(px * 0.0004 + 9, y * 0.0003, pz * 0.0004, 2)   # thick, chunky beds
    ph = (y + wav) / thick
    return np.floor(ph), ph - np.floor(ph)


ROCK_PAL = np.array([[0.84, 0.60, 0.40], [0.88, 0.70, 0.48], [0.76, 0.48, 0.34], [0.62, 0.57, 0.54], [0.52, 0.49, 0.48], [0.82, 0.64, 0.44]])   # sandstone, ochre, terracotta, warm slate, dark slate, buff
ROCK_W = np.array([0.26, 0.22, 0.18, 0.12, 0.06, 0.16])


def band_colour(b):
    h = hash3(b, 3.7, 1.1)
    idx = np.searchsorted(np.cumsum(ROCK_W), h * ROCK_W.sum())
    return ROCK_PAL[np.clip(idx, 0, len(ROCK_PAL) - 1)]


# ---- main body: a grid of rings (rows) × angles (cols), seam column duplicated for the u coordinate
N = 640
ths = np.linspace(0, 2 * np.pi, N + 1)
ys = [0.6, -6.0, -24.0, -62.0]
y = -62.0
while y > -2560:
    y -= 9 + 0.011 * abs(y)
    ys.append(max(y, -2560))
ys += [-2600.0, -2640.0]
ys = np.array(ys)
K = len(ys)
TH, Y = np.meshgrid(ths, ys)                     # K × (N+1)
rim = isle_r(TH)
C, S_ = np.cos(TH), np.sin(TH)
ux, uz = C * R0, S_ * R0                           # noise coordinates on a cylinder: no seam
depth = np.clip((-Y - 40) / 260, 0, 1)
lobes = fbm(ux * 0.0011, Y * 0.0011, uz * 0.0011) - 0.5
gully = 1 - np.abs(fbm(ux * 0.0042 + 5, Y * 0.0016, uz * 0.0042) * 2 - 1)
band, fpos = strata(ux, Y, uz)
lip = (0.034 * fpos ** 3 - 0.010) * (0.5 + 1.0 * hash3(band, 1.3, 7.7))   # each band's top juts out a little: ledges and overhangs
r = rim * prof_scale(Y) * (1 + depth * (0.13 * lobes - 0.045 * gully ** 2 + lip))
Yd = Y + depth * (fbm(ux * 0.002 + 3, Y * 0.002, uz * 0.002) - 0.5) * 36
water = water_mask()
wet = water(np.cos(ths) * isle_r(ths) * 0.982, np.sin(ths) * isle_r(ths) * 0.982)
Yd[0, wet] = -1.6
r[1, wet] *= 0.995
r[-1, :] = 0.0
X, Z = C * r, S_ * r

col = band_colour(band) * (1.06 - 0.26 * depth)[..., None]
col = col * (0.9 + 0.2 * fbm(ux * 0.02, Y * 0.03, uz * 0.02, 2))[..., None]
soil, grass, wetc = np.array([0.62, 0.42, 0.28]), np.array([0.40, 0.56, 0.24]), np.array([0.22, 0.27, 0.28])
col[0:2] = grass; col[2:4] = soil
col[0:3, wet] = wetc

# ambient occlusion proxy from the grid: concave places (the surface behind its neighbours) and ledge undersides darken
P = np.stack([X, Yd, Z], -1)
nb = (np.roll(P, 1, 1) + np.roll(P, -1, 1) + np.concatenate([P[:1], P[:-1]]) + np.concatenate([P[1:], P[-1:]])) / 4
out = np.stack([C, np.zeros_like(C), S_], -1)
cav = np.einsum("ijk,ijk->ij", P - nb, out)                                  # > 0: sticks out, < 0: recessed
ao = np.clip(1 + cav / 12, 0.72, 1.12)
col *= ao[..., None]

# ---- hanging spires: tapering, slightly bent columns of rings with the same strata
rng = np.random.default_rng(4242)
spires = []
for s in range(96):
    k = int(rng.integers(8, int(K * 0.72))); j = int(rng.integers(0, N))
    if Yd[k, j] > -160: continue
    th0 = ths[j]; bx, bz, by = X[k, j] * 0.95, Z[k, j] * 0.95, Yd[k, j] + 30
    rad = 22 + rng.random() * 85 * (1 - k / K * 0.6); ln = 140 + rng.random() * 520
    bend = rng.normal(0, 0.12, 2)
    spires.append((bx, by, bz, rad, ln, bend, th0))


def spire_rings(bx, by, bz, rad, ln, bend, th0, rings=16, sides=11):
    pts, cols, us, axes = [], [], [], []
    for i in range(rings + 1):
        t = i / rings
        cy = by - t * ln
        cx, cz = bx + bend[0] * ln * t * t, bz + bend[1] * ln * t * t
        axes.append((cx, cz))
        rr = rad * (1 - t) ** 1.35 + 0.6 * (1 - t)
        a = np.linspace(0, 2 * np.pi, sides + 1)
        n = 1 + 0.18 * (vnoise3(np.cos(a) * 3 + bx * 0.01, np.full_like(a, cy * 0.02), np.sin(a) * 3 + bz * 0.01) - 0.5)
        px, pz = cx + np.cos(a) * rr * n, cz + np.sin(a) * rr * n
        b, f = strata(px, np.full_like(a, cy), pz)
        c = band_colour(b) * (1 - 0.3 * min(1, (-cy - 40) / 260)) * (0.75 + 0.25 * (1 - t))
        pts.append(np.stack([px, np.full_like(a, cy), pz], -1)); cols.append(c); us.append(a * max(rad, 1))
    return np.array(pts), np.array(cols), np.array(us), axes


# ---- build the Blender mesh (Blender coords: X = x, Y = -z, Z = y)
bm = bmesh.new()
uv_l = bm.loops.layers.uv.new("UVMap")
col_l = bm.loops.layers.float_color.new("Col")


# axis(i) → ring centre (x, z) in page coords: faces are wound to face away from it (and a little downward), so the
# normals point out of the rock — the body is open at the top, Blender's recalc_face_normals would guess wrong
def grid(Pg, Cg, Ug, mat_of_row, axis=lambda i: (0.0, 0.0)):
    R_, Q_ = Pg.shape[0], Pg.shape[1]
    V = [[bm.verts.new((Pg[i, j, 0], -Pg[i, j, 2], Pg[i, j, 1])) for j in range(Q_)] for i in range(R_)]
    for i in range(R_ - 1):
        cx, cz = axis(i)
        for j in range(Q_ - 1):
            a, b, d = Pg[i, j], Pg[i, j + 1], Pg[i + 1, j]
            nrm = np.cross(b - a, d - a)
            out = np.array([a[0] - cx, -0.25 * math.hypot(a[0] - cx, a[2] - cz), a[2] - cz])
            quad = (V[i][j], V[i][j + 1], V[i + 1][j + 1], V[i + 1][j])
            f = bm.faces.new(quad if np.dot(nrm, out) >= 0 else quad[::-1])
            f.material_index = mat_of_row(i); f.smooth = True
            for loop, (ii, jj) in zip(f.loops, ((i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j))):
                loop[uv_l].uv = (Ug[ii, jj] / U_SCALE, 0.0)
                c = Cg[ii, jj]; loop[col_l] = (c[0], c[1], c[2], 1.0)


U_body = TH * isle_r(0.0)                       # arc length, as the page's rock body (island.js rockBody)
# u is stored divided by U_SCALE (extras "uScale"): gltfpack quantizes texcoords to 0…1 when no texture carries the scale
U_SCALE = float(2 * np.pi * isle_r(0.0))
grid(np.stack([X, Yd, Z], -1), col, U_body, lambda i: 0 if i < 1 else 1)
for sp in spires:
    Pp, Cp, Up, ax = spire_rings(*sp)
    grid(Pp, Cp, Up, lambda i: 1, axis=lambda i: ax[i])
bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts if abs(v.co.z + 2640) < 1e-3], dist=0.01)   # close the tip

bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new("ISLAND_body")
bm.to_mesh(me); bm.free()
me.color_attributes.active_color = me.color_attributes["Col"]
ob = bpy.data.objects.new("ISLAND_body", me)
bpy.context.scene.collection.objects.link(ob)
ob["uScale"] = U_SCALE
ob["source"] = "tools/blender/model_island.py (procedural: strata, ledges, gullies, spires; outline = page isleR)"
for name, base in (("M11_grass", (0.40, 0.56, 0.24, 1)), ("M10_rock", (0.75, 0.55, 0.40, 1))):
    m = bpy.data.materials.new(name); m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]; bsdf.inputs["Base Color"].default_value = base
    attr = m.node_tree.nodes.new("ShaderNodeVertexColor"); attr.layer_name = "Col"
    m.node_tree.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    me.materials.append(m)
print("ISLAND_body", len(me.vertices), "verts", len(me.polygons), "faces", K, "rows", len(spires), "spires", int(wet.sum()), "wet columns")
if BLEND:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(BLEND), compress=True)
bpy.ops.export_scene.gltf(filepath=os.path.abspath(OUT), export_format="GLB", export_yup=True, export_apply=True, export_extras=True,
                          export_vertex_color="ACTIVE", export_normals=True, export_texcoords=True, export_materials="EXPORT")
print("exported", OUT, os.path.getsize(OUT))
