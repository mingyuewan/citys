"""Landmark models for the page (phase 3): the China Resources HQ "Spring Bamboo" and the Shenzhen Bay Sports Center
"Spring Cocoon", in local coordinates (centre at the origin, metres, page frame: x east, y up, z south); the page puts
each on its landmark's position and rotation (data/szbay.json, moved onto the OSM footprint by tools/osm/merge_osm.py).

usage: Blender -b --factory-startup --python tools/blender/model_landmarks.py -- data/szbay.json build/landmarks.raw.glb [--blend out.blend]
Nodes "LM_bamboo", "LM_cocoon"; materials "M<id>_…" with the page's material ids (7 landmark glass, 5 metal,
8 matte paint, 2 podium); colours in COLOR_0; texcoord u (facade coordinate round the tower) stored as u / uScale.
"""
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
DATA, OUT = argv[0], argv[1]
BLEND = argv[argv.index("--blend") + 1] if "--blend" in argv else None
D = json.load(open(DATA, encoding="utf-8"))
LM = {l["k"]: l for l in D["landmarks"]}
MATS = {7: "M7_landmark_glass", 5: "M5_metal", 8: "M8_paint", 2: "M2_podium"}


class Mesh:
    """Faces in page coordinates; each face wound to point away from a reference point given with it."""
    def __init__(self, u_scale):
        self.v, self.f, self.u_scale = [], [], u_scale

    def vert(self, p, col, u=0.0):
        self.v.append((tuple(p), tuple(col), u)); return len(self.v) - 1

    def face(self, idx, mat, ref, smooth=True):
        P = [np.array(self.v[i][0]) for i in idx]
        n = np.cross(P[1] - P[0], P[2] - P[0])
        if np.linalg.norm(n) < 1e-9 and len(P) > 3: n = np.cross(P[2] - P[0], P[3] - P[0])
        c = sum(P) / len(P)
        if np.dot(n, c - np.array(ref)) < 0: idx = idx[::-1]
        self.f.append((idx, mat, smooth))

    def grid(self, rows, cols_fn, mat, ref_fn, u_fn=lambda i, j: 0.0, closed=True):
        """rows: list of rings (lists of 3D points); ring i, point j."""
        R, Q = len(rows), len(rows[0])
        ids = [[self.vert(rows[i][j], cols_fn(i, j), u_fn(i, j)) for j in range(Q)] for i in range(R)]
        for i in range(R - 1):
            for j in range(Q if closed else Q - 1):
                j1 = (j + 1) % Q
                self.face([ids[i][j], ids[i][j1], ids[i + 1][j1], ids[i + 1][j]], mat, ref_fn(i, j))

    def tube(self, path, side, w, d, col, mat):
        """A square-section member along `path` (points), `side` the across direction per point; d outward offset."""
        for k in range(len(path) - 1):
            a, b = np.array(path[k]), np.array(path[k + 1])
            sa, sb = np.array(side[k]), np.array(side[k + 1])
            t = b - a; t /= max(np.linalg.norm(t), 1e-9)
            oa = np.cross(t, sa); oa /= max(np.linalg.norm(oa), 1e-9)   # outward (side × up turned round)
            ob = np.cross(t, sb); ob /= max(np.linalg.norm(ob), 1e-9)
            ca, cb = a + oa * d / 2, b + ob * d / 2
            corners = lambda c, s, o: [c + s * w / 2 + o * d / 2, c - s * w / 2 + o * d / 2, c - s * w / 2 - o * d / 2, c + s * w / 2 - o * d / 2]
            A, B = corners(ca, sa, oa), corners(cb, sb, ob)
            for q in range(4):
                ids = [self.vert(A[q], col), self.vert(A[(q + 1) % 4], col), self.vert(B[(q + 1) % 4], col), self.vert(B[q], col)]
                self.face(ids, mat, ((ca + cb) / 2).tolist(), smooth=False)

    def to_object(self, name):
        bm = bmesh.new()
        uv_l = bm.loops.layers.uv.new("UVMap"); col_l = bm.loops.layers.float_color.new("Col")
        bv = [bm.verts.new((p[0], -p[2], p[1])) for p, _, _ in self.v]   # page (x, y, z) → Blender (x, −z, y)
        mats = sorted({m for _, m, _ in self.f}); slot = {m: i for i, m in enumerate(mats)}
        for idx, m, smooth in self.f:
            try:
                f = bm.faces.new([bv[i] for i in idx])
            except ValueError:
                continue
            f.material_index = slot[m]; f.smooth = smooth
            for loop, i in zip(f.loops, idx):
                c = self.v[i][1]; loop[col_l] = (c[0], c[1], c[2], 1.0); loop[uv_l].uv = (self.v[i][2] / self.u_scale, 0.0)
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        me.color_attributes.active_color = me.color_attributes["Col"]
        for m in mats:
            mat = bpy.data.materials.get(MATS[m]) or bpy.data.materials.new(MATS[m])
            me.materials.append(mat)
        ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
        ob["uScale"] = self.u_scale
        return ob, len(me.vertices), len(me.polygons)


def smooth_profile(prof, n):
    """Monotone resampling of [t, s] pairs with a light smoothing pass."""
    t = np.linspace(0, 1, n)
    s = np.interp(t, [p[0] for p in prof], [p[1] for p in prof])
    for _ in range(3): s[1:-1] = (s[:-2] + 2 * s[1:-1] + s[2:]) / 4
    return t, s


# ---------------------------------------------------------------- Spring Bamboo (China Resources HQ, 392.5 m)
def bamboo():
    L = LM["bamboo"]; H, R0, NF = L["h"], L["s"][0], 56
    prof = [[0, 1], [0.25, 0.985], [0.5, 0.955], [0.7, 0.915], [0.8, 0.88], [0.86, 0.80], [0.91, 0.66], [0.95, 0.47], [0.98, 0.26], [1.0, 0.02]]
    t, s = smooth_profile(prof, 140)
    m = Mesh(2 * math.pi * R0)
    glass = (0.90, 0.88, 0.82); fin = (0.96, 0.96, 0.94)
    NS = NF * 2
    ang = np.linspace(0, 2 * np.pi, NS, endpoint=False)
    rings = [[(math.cos(a) * R0 * si, ti * H, math.sin(a) * R0 * si) for a in ang] for ti, si in zip(t, s)]
    m.grid(rings, lambda i, j: glass, 7, lambda i, j: (0, t[i] * H, 0), u_fn=lambda i, j: ang[j] * R0)
    # 56 white fins: blades standing out from the glass, flaring into roots at the foot, closing over the crown
    for k in range(NF):
        a = (k + 0.5) / NF * 2 * np.pi; ca, sa = math.cos(a), math.sin(a)
        path, side = [], []
        for ti, si in zip(t[::2], s[::2]):
            dep = 3.4 * min(1, si * 1.6) + 6.5 * max(0.0, 0.05 - ti) / 0.05   # the roots spread at the base
            rr = R0 * si + dep * 0.5
            path.append((ca * rr, ti * H, sa * rr)); side.append((-sa, 0, ca))
        m.tube(path, side, 1.3, 3.4, fin, 5)
    # crown diagrid: diagonal members between neighbouring fins over the top fifth
    tc = t[t > 0.8][::3]
    for k in range(NF):
        for q in range(len(tc) - 1):
            for dirn in (1, -1):
                a0 = (k + 0.5) / NF * 2 * np.pi; a1 = (k + 0.5 + dirn) / NF * 2 * np.pi
                r0 = R0 * np.interp(tc[q], t, s) + 1.8; r1 = R0 * np.interp(tc[q + 1], t, s) + 1.8
                p0 = (math.cos(a0) * r0, tc[q] * H, math.sin(a0) * r0); p1 = (math.cos(a1) * r1, tc[q + 1] * H, math.sin(a1) * r1)
                m.tube([p0, p1], [(-math.sin(a0), 0, math.cos(a0)), (-math.sin(a1), 0, math.cos(a1))], 0.8, 1.0, fin, 5)
    # glass lobby at the foot
    lob = [[(math.cos(a) * (R0 + 9), y, math.sin(a) * (R0 + 9)) for a in ang] for y in (0.0, 11.0)]
    m.grid(lob, lambda i, j: (0.78, 0.84, 0.86), 2, lambda i, j: (0, 5, 0), u_fn=lambda i, j: ang[j] * (R0 + 9))
    cap = [[(math.cos(a) * r, 11.0, math.sin(a) * r) for a in ang] for r in (R0 + 9, R0 * 1.0)]
    m.grid(cap, lambda i, j: (0.86, 0.85, 0.82), 8, lambda i, j: (0, -10, 0))
    return m.to_object("LM_bamboo")


# ---------------------------------------------------------------- Spring Cocoon (Shenzhen Bay Sports Center)
def cocoon():
    L = LM["cocoon"]; a, b, H = L["s"][0] / 2, L["s"][1] / 2, L["h"]
    m = Mesh(math.pi * (a + b))
    def surf(th, ph, k=1.0):
        rs = math.cos(ph) ** 0.62                     # fuller than an ellipsoid: a cocoon, not a dome
        return (math.cos(th) * a * rs * k, math.sin(ph) * H * (k if k < 1 else 1), math.sin(th) * b * rs * k)
    NT, NP = 128, 18
    ths = np.linspace(0, 2 * np.pi, NT, endpoint=False); phs = np.linspace(0, math.pi / 2 * 0.985, NP)
    skin = [[surf(th, ph, 0.985) for th in ths] for ph in phs]
    m.grid(skin, lambda i, j: (0.80, 0.86, 0.88), 5, lambda i, j: (0, -20, 0), u_fn=lambda i, j: ths[j] * (a + b) / 2)
    top = [[surf(th, phs[-1], 0.985) for th in ths], [(0, H * 0.985, 0)] * NT]
    m.grid(top, lambda i, j: (0.80, 0.86, 0.88), 5, lambda i, j: (0, -20, 0))
    # the diagrid: two families of white members spiralling up the shell
    white = (0.97, 0.96, 0.93)
    NR, TW = 44, 1.15
    for fam in (1, -1):
        for r in range(NR):
            th0 = r / NR * 2 * math.pi
            path, side = [], []
            for q in range(15):
                u = q / 14; ph = u * math.pi / 2 * 0.86; th = th0 + fam * u * TW
                p = surf(th, ph, 1.0)
                path.append(p)
                e = np.array(surf(th + 0.01, ph, 1.0)) - np.array(surf(th - 0.01, ph, 1.0)); e /= np.linalg.norm(e)
                side.append(tuple(e))
            m.tube(path, side, 2.6, 1.8, white, 8)
    # the ring beam it stands on and the podium with its glazed front
    ring = [[(math.cos(th) * a * k, y, math.sin(th) * b * k) for th in ths] for k, y in ((1.04, 0.0), (1.04, 7.0))]
    m.grid(ring, lambda i, j: (0.84, 0.86, 0.86), 2, lambda i, j: (0, 3, 0), u_fn=lambda i, j: ths[j] * (a + b) / 2 * 1.04)
    capr = [[(math.cos(th) * a * k, 7.0, math.sin(th) * b * k) for th in ths] for k in (1.04, 0.96)]
    m.grid(capr, lambda i, j: (0.90, 0.89, 0.86), 8, lambda i, j: (0, -10, 0))
    return m.to_object("LM_cocoon")


bpy.ops.wm.read_factory_settings(use_empty=True)
for name in MATS.values():
    bpy.data.materials.new(name)
for fn in (bamboo, cocoon):
    ob, nv, nf = fn()
    print(ob.name, nv, "verts", nf, "faces")
if BLEND:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(BLEND), compress=True)
bpy.ops.export_scene.gltf(filepath=os.path.abspath(OUT), export_format="GLB", export_yup=True, export_apply=True, export_extras=True,
                          export_vertex_color="ACTIVE", export_normals=True, export_texcoords=True, export_materials="EXPORT")
print("exported", OUT, os.path.getsize(OUT))
