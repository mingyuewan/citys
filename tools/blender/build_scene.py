"""Build blender/shenzhen-bay.blend from the page's exported geometry.

usage:
  Blender -b --factory-startup --python tools/blender/build_scene.py -- [EXPORT_DIR] [OUT_BLEND]
    EXPORT_DIR default build/blender_export   (made by tools/blender/export_scene.py)
    OUT_BLEND  default blender/shenzhen-bay.blend

Coordinates: page (x east, y up, z south) -> Blender (X, Y, Z) = (x, -z, y), metres.
Geometry is reused 1:1 from the page's GPU buffers; nothing is re-modelled.
Repeated props (trees, cars, lamps, signals, bus stops, cloud cards) are Geometry Nodes instances
on point clouds, so the scene has a few dozen objects instead of tens of thousands.
"""
import json
import math
import os
import sys

import bpy
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
EXP = os.path.abspath(argv[0] if len(argv) > 0 else os.path.join(ROOT, "build", "blender_export"))
OUT = os.path.abspath(argv[1] if len(argv) > 1 else os.path.join(ROOT, "blender", "shenzhen-bay.blend"))
TEX = os.path.join(ROOT, "assets", "textures")
META = json.load(open(os.path.join(EXP, "meta.json"), encoding="utf-8"))

# time of day used for the sun (same sun model as sky() in the page)
TOD = 16.9


def page_sun(tod):
    a = (tod - 6) / 12 * math.pi
    v = np.array([math.cos(a), math.sin(a) * 1.15, 0.38 + math.sin(a) * 0.15])
    return v / np.linalg.norm(v)


def to_b(p):
    """page (N,3) -> blender (N,3)"""
    return np.stack([p[:, 0], -p[:, 2], p[:, 1]], axis=1)


def load(name, dtype=np.float32):
    return np.fromfile(os.path.join(EXP, name + ".bin"), dtype=dtype)


# ---------------------------------------------------------------- scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.name = "ShenzhenBay"
scene.unit_settings.system = "METRIC"


def coll(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or scene.collection).children.link(c)
    return c


C_CITY, C_ISLE, C_GROUND, C_PROPS, C_SKY, C_TPL = (coll(n) for n in ("City", "Island", "Ground_Water", "Props_Instances", "Clouds_Sky", "Templates"))
C_TPL.hide_render = True
C_TPL.hide_viewport = True


# ---------------------------------------------------------------- node helpers
class NB:
    """tiny node-tree builder"""

    def __init__(self, tree):
        self.t = tree
        self.n = tree.nodes
        self.l = tree.links
        self.x = 0

    def node(self, kind, loc=None, **props):
        nd = self.n.new(kind)
        nd.location = loc or (self.x, 0)
        self.x += 40
        for k, v in props.items():
            if hasattr(nd, k):
                setattr(nd, k, v)
            else:
                nd.inputs[k].default_value = v
        return nd

    def link(self, a, b):
        self.l.new(a, b)

    def math(self, op, a, b=None, clamp=False):
        nd = self.node("ShaderNodeMath" if self.t.bl_idname == "ShaderNodeTree" else "ShaderNodeMath", operation=op)
        nd.use_clamp = clamp
        self._in(nd.inputs[0], a)
        if b is not None:
            self._in(nd.inputs[1], b)
        return nd.outputs[0]

    def mix(self, fac, a, b, blend="MIX"):
        nd = self.node("ShaderNodeMix", data_type="RGBA", blend_type=blend)
        self._in(nd.inputs["Factor"], fac)
        self._in(nd.inputs[6], a)
        self._in(nd.inputs[7], b)
        return nd.outputs[2]

    def mixf(self, fac, a, b):
        nd = self.node("ShaderNodeMix", data_type="FLOAT")
        self._in(nd.inputs["Factor"], fac)
        self._in(nd.inputs[2], a)
        self._in(nd.inputs[3], b)
        return nd.outputs[0]

    def smooth(self, e0, e1, x):
        nd = self.node("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
        self._in(nd.inputs["Value"], x)
        nd.inputs["From Min"].default_value = e0
        nd.inputs["From Max"].default_value = e1
        return nd.outputs[0]

    def _in(self, sock, v):
        if isinstance(v, bpy.types.NodeSocket):
            self.l.new(v, sock)
        elif isinstance(v, (tuple, list)):
            sock.default_value = v if len(v) == len(sock.default_value) else tuple(v) + (1.0,)
        else:
            sock.default_value = v


def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    nb = NB(m.node_tree)
    out = nb.node("ShaderNodeOutputMaterial", (900, 0))
    return m, nb, out


def principled(nb, out, base, rough=0.5, metal=0.0, spec=0.5, emis=None, emis_k=0.0, alpha=None, normal=None, coat=0.0):
    p = nb.node("ShaderNodeBsdfPrincipled", (600, 0))
    nb._in(p.inputs["Base Color"], base)
    nb._in(p.inputs["Roughness"], rough)
    nb._in(p.inputs["Metallic"], metal)
    nb._in(p.inputs["Specular IOR Level"], spec)
    if coat:
        nb._in(p.inputs["Coat Weight"], coat)
    if emis is not None:
        nb._in(p.inputs["Emission Color"], emis)
        nb._in(p.inputs["Emission Strength"], emis_k)
    if alpha is not None:
        nb._in(p.inputs["Alpha"], alpha)
    if normal is not None:
        nb.link(normal, p.inputs["Normal"])
    nb.link(p.outputs[0], out.inputs["Surface"])
    return p


def attr(nb, name, kind="GEOMETRY", out="Fac"):
    a = nb.node("ShaderNodeAttribute", attribute_name=name, attribute_type=kind)
    return a.outputs[out]


def image(path, colorspace="sRGB", alpha_mode=None):
    img = bpy.data.images.load(path, check_existing=True)
    img.colorspace_settings.name = colorspace
    if alpha_mode:
        img.alpha_mode = alpha_mode
    return img


def tex(nb, img, vec, interp="Linear", ext="REPEAT", proj="FLAT"):
    t = nb.node("ShaderNodeTexImage", image=img, interpolation=interp, extension=ext, projection=proj)
    if vec is not None:
        nb.link(vec, t.inputs["Vector"])
    return t


def uvmap(nb, sx, sy, name="UVMap"):
    uv = nb.node("ShaderNodeUVMap", uv_map=name)
    mp = nb.node("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (sx, sy, 1)
    nb.link(uv.outputs[0], mp.inputs["Vector"])
    return mp.outputs[0]


def sep(nb, v):
    s = nb.node("ShaderNodeSeparateXYZ")
    nb.link(v, s.inputs[0])
    return s.outputs


def bump(nb, height, strength=0.3, dist=1.0):
    b = nb.node("ShaderNodeBump", Strength=strength, Distance=dist)
    nb._in(b.inputs["Height"], height)
    return b.outputs[0]


def noise(nb, vec, scale, detail=4.0, rough=0.55):
    n = nb.node("ShaderNodeTexNoise", Scale=scale, Detail=detail, Roughness=rough)
    if vec is not None:
        nb.link(vec, n.inputs["Vector"])
    return n


IMG_ROCK = image(os.path.join(TEX, "island-rock.webp"))
IMG_FACADE = image(os.path.join(TEX, "tower-facade.webp"))
IMG_CLOUD = image(os.path.join(TEX, "cloud-puff.webp"), alpha_mode="STRAIGHT")
IMG_GROUND = image(os.path.join(EXP, "ground.png"), "Non-Color")
IMG_LU = image(os.path.join(EXP, "landuse.png"), "Non-Color")
for im, nm in ((IMG_GROUND, "ground_classmap.png"), (IMG_LU, "landuse.png")):
    im.name = nm


# ---------------------------------------------------------------- materials
def mat_facade(name, sx, sy, tint_k, rough, night_k=0.0):
    """glass curtain wall: GPT Image tower-facade texture on the page's facade UVs (u = metres along wall, v = height)"""
    m, nb, out = new_mat(name)
    t = tex(nb, IMG_FACADE, uvmap(nb, 1 / sx, 1 / sy))
    col = nb.node("ShaderNodeVertexColor", layer_name="Col").outputs[0]
    tint = nb.mix(tint_k, (1, 1, 1, 1), col, "MULTIPLY")
    base = nb.mix(1.0, t.outputs[0], tint, "MULTIPLY")
    base = nb.mix(0.15, base, (0.75, 0.85, 0.95, 1), "MIX")
    lum = nb.node("ShaderNodeRGBToBW")
    nb.link(t.outputs[0], lum.inputs[0])
    # mullions (bright, rough) vs glass (dark, glossy)
    r = nb.mixf(nb.smooth(0.35, 0.7, lum.outputs[0]), rough, 0.55)
    # warm lit rooms in the texture -> emission (night_k scales it; 0 for day renders)
    sepc = nb.node("ShaderNodeSeparateColor")
    nb.link(t.outputs[0], sepc.inputs[0])
    warm = nb.smooth(0.04, 0.16, nb.math("SUBTRACT", sepc.outputs[0], sepc.outputs[2]))
    em = nb.mix(warm, (0, 0, 0, 1), t.outputs[0])
    principled(nb, out, base, rough=r, metal=0.35, spec=0.7, emis=em, emis_k=night_k, coat=0.25)
    return m


def mat_grid(name, cell, win, glass_col, wall_mul=1.0, rough_wall=0.75):
    """residential / podium / village walls: wall = vertex colour, procedural window grid in page facade UVs"""
    m, nb, out = new_mat(name)
    uv = nb.node("ShaderNodeUVMap", uv_map="UVMap").outputs[0]
    s = sep(nb, uv)
    fx = nb.math("FRACT", nb.math("DIVIDE", s[0], cell[0]))
    fy = nb.math("FRACT", nb.math("DIVIDE", s[1], cell[1]))
    wx = nb.math("MULTIPLY", nb.smooth(win[0] - 0.02, win[0] + 0.02, fx), nb.smooth(1 - win[0] + 0.02, 1 - win[0] - 0.02, fx))
    wy = nb.math("MULTIPLY", nb.smooth(win[1] - 0.02, win[1] + 0.02, fy), nb.smooth(1 - win[1] + 0.02, 1 - win[1] - 0.02, fy))
    w = nb.math("MULTIPLY", wx, wy)
    # skip windows on roofs/caps (u = -1 on caps)
    wall_side = nb.smooth(-0.6, -0.4, s[0])
    w = nb.math("MULTIPLY", w, wall_side)
    col = nb.node("ShaderNodeVertexColor", layer_name="Col").outputs[0]
    n = noise(nb, None, 0.08, 3)
    wall = nb.mix(nb.mixf(n.outputs[0], 0.88, 1.06), col, (wall_mul, wall_mul, wall_mul, 1), "MULTIPLY")
    base = nb.mix(w, wall, glass_col)
    rough = nb.mixf(w, rough_wall, 0.08)
    principled(nb, out, base, rough=rough, spec=nb.mixf(w, 0.4, 0.9), normal=bump(nb, w, 0.25, 0.15))
    return m


def mat_simple(name, color=None, rough=0.6, metal=0.0, use_vcol=True, noise_k=0.0, spec=0.5):
    m, nb, out = new_mat(name)
    base = color or (0.6, 0.6, 0.6, 1)
    if use_vcol:
        base = nb.node("ShaderNodeVertexColor", layer_name="Col").outputs[0]
        if color:
            base = nb.mix(1.0, base, color, "MULTIPLY")
    if noise_k:
        n = noise(nb, None, 0.35, 5)
        base = nb.mix(noise_k, base, nb.mix(1.0, base, n.outputs[0], "MULTIPLY"), "MIX") if not isinstance(base, tuple) else nb.mix(noise_k, base, n.outputs[0], "MULTIPLY")
    principled(nb, out, base, rough=rough, metal=metal, spec=spec)
    return m


def mat_rock():
    """island underside: GPT Image island-rock texture, two scales + moss on up-facing ledges"""
    m, nb, out = new_mat("M_Island_Rock")
    t1 = tex(nb, IMG_ROCK, uvmap(nb, 1 / 260.0, 1 / 180.0))
    t2 = tex(nb, IMG_ROCK, uvmap(nb, 1 / 41.0, 1 / 29.0))
    rock = nb.mix(0.45, t1.outputs[0], t2.outputs[0], "OVERLAY")
    col = nb.node("ShaderNodeVertexColor", layer_name="Col").outputs[0]
    # page colours darken with depth; keep that gradient but let the texture carry the hue
    shade = nb.node("ShaderNodeRGBToBW")
    nb.link(col, shade.inputs[0])
    rock = nb.mix(1.0, rock, nb.math("MULTIPLY", shade.outputs[0], 2.3), "MULTIPLY")
    geo = nb.node("ShaderNodeNewGeometry")
    nz = sep(nb, geo.outputs["Normal"])[2]
    n = noise(nb, None, 0.012, 4)
    moss = nb.math("MULTIPLY", nb.smooth(0.35, 0.8, nz), nb.smooth(0.42, 0.62, n.outputs[0]))
    base = nb.mix(moss, rock, (0.075, 0.14, 0.045, 1))
    lum = nb.node("ShaderNodeRGBToBW")
    nb.link(t2.outputs[0], lum.inputs[0])
    lum2 = nb.node("ShaderNodeRGBToBW")
    nb.link(t1.outputs[0], lum2.inputs[0])
    h = nb.math("ADD", lum.outputs[0], nb.math("MULTIPLY", lum2.outputs[0], 2.0))
    principled(nb, out, base, rough=0.88, spec=0.3, normal=bump(nb, h, 0.6, 3.0))
    return m


def mat_grass(name="M_Grass_Lip"):
    m, nb, out = new_mat(name)
    n = noise(nb, None, 0.05, 5)
    n2 = noise(nb, None, 0.6, 3)
    base = nb.mix(n.outputs[0], (0.07, 0.16, 0.04, 1), (0.16, 0.25, 0.06, 1))
    base = nb.mix(nb.math("MULTIPLY", n2.outputs[0], 0.4), base, (0.25, 0.22, 0.10, 1))
    principled(nb, out, base, rough=0.92, spec=0.3, normal=bump(nb, n2.outputs[0], 0.3, 0.5))
    return m


def mat_ground():
    """island top: page ground class map (r water, g green, b road) + land-use zones; water is a glossy wavy surface"""
    m, nb, out = new_mat("M_Ground_Water")
    uv = nb.node("ShaderNodeUVMap", uv_map="UVMap").outputs[0]
    g = tex(nb, IMG_GROUND, uv, ext="EXTEND")
    lu = tex(nb, IMG_LU, uv, interp="Closest", ext="EXTEND")
    cs = nb.node("ShaderNodeSeparateColor")
    nb.link(g.outputs[0], cs.inputs[0])
    ls = nb.node("ShaderNodeSeparateColor")
    nb.link(lu.outputs[0], ls.inputs[0])
    # zone colour: lu.r * 255 / 30 = zone id (0 none, 1 cbd, 2 tech, 3 res, 4 village, 5 mixed, 6+ green)
    ramp = nb.node("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    zc = [(0.0, (0.30, 0.29, 0.27)), (0.5, (0.40, 0.38, 0.35)), (2.5, (0.36, 0.33, 0.30)), (3.5, (0.17, 0.165, 0.155)),
          (4.5, (0.30, 0.28, 0.25)), (5.5, (0.09, 0.17, 0.05))]
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, zc[0][1] + (1,)
    els[1].position, els[1].color = zc[1][0] * 30 / 255, zc[1][1] + (1,)
    for z, c in zc[2:]:
        e = els.new(z * 30 / 255)
        e.color = c + (1,)
    nb.link(ls.outputs[0], ramp.inputs[0])
    n = noise(nb, None, 0.02, 5)
    n2 = noise(nb, None, 0.3, 4)
    land = nb.mix(1.0, ramp.outputs[0], nb.mixf(n.outputs[0], 0.82, 1.12), "MULTIPLY")
    grass = nb.mix(n2.outputs[0], (0.06, 0.15, 0.035, 1), (0.13, 0.22, 0.05, 1))
    land = nb.mix(nb.smooth(0.2, 0.7, cs.outputs[1]), land, grass)
    b = cs.outputs[2]
    land = nb.mix(nb.smooth(0.12, 0.24, b), land, (0.33, 0.30, 0.26, 1))
    land = nb.mix(nb.smooth(0.42, 0.55, b), land, (0.10, 0.10, 0.11, 1))
    land = nb.mix(nb.smooth(0.72, 0.92, b), land, (0.06, 0.06, 0.065, 1))
    # footing contact shadow from land-use g (distance to building)
    bd = nb.math("MULTIPLY", ls.outputs[1], 255 / 8)
    land = nb.mix(1.0, land, nb.mixf(nb.smooth(0.0, 3.5, bd), 0.55, 1.0), "MULTIPLY")
    pl = principled(nb, out, land, rough=0.85, spec=0.35)
    # water
    w = nb.smooth(0.35, 0.75, cs.outputs[0])
    tc = nb.node("ShaderNodeTexCoord")
    wv = nb.node("ShaderNodeTexWave", wave_type="BANDS", bands_direction="DIAGONAL", Scale=0.004, Distortion=6.0, Detail=4.0)
    nb.link(tc.outputs["Object"], wv.inputs["Vector"])
    wn = noise(nb, tc.outputs["Object"], 0.03, 6, 0.6)
    wh = nb.math("ADD", wv.outputs["Fac"], nb.math("MULTIPLY", wn.outputs[0], 1.5))
    shallow = nb.math("SUBTRACT", 1.0, cs.outputs[0])
    wcol = nb.mix(nb.smooth(0.0, 0.5, shallow), (0.012, 0.045, 0.055, 1), (0.03, 0.12, 0.11, 1))
    water = nb.node("ShaderNodeBsdfPrincipled")
    nb._in(water.inputs["Base Color"], wcol)
    water.inputs["Roughness"].default_value = 0.06
    water.inputs["Specular IOR Level"].default_value = 0.6
    water.inputs["Coat Weight"].default_value = 0.4
    nb.link(bump(nb, wh, 0.12, 0.6), water.inputs["Normal"])
    mx = nb.node("ShaderNodeMixShader")
    nb.link(w, mx.inputs[0])
    nb.link(pl.outputs[0], mx.inputs[1])
    nb.link(water.outputs[0], mx.inputs[2])
    nb.link(mx.outputs[0], out.inputs["Surface"])
    return m


def mat_road():
    """road ribbons: asphalt + lane markings from the page's per-vertex road attributes"""
    m, nb, out = new_mat("M_Road")
    across, along, dj, hw = (attr(nb, n) for n in ("r_across", "r_along", "r_dj", "r_hw"))
    lanes, kind, ow = (attr(nb, n) for n in ("r_lanes", "r_kind", "r_ow"))
    aa = nb.math("ABSOLUTE", across)

    def band(x, c, w):
        return nb.math("LESS_THAN", nb.math("ABSOLUTE", nb.math("SUBTRACT", x, c)), w * 0.5)

    inJ = nb.math("GREATER_THAN", dj, 14.0)
    has = nb.math("GREATER_THAN", lanes, 0.5)
    edge = nb.math("MULTIPLY", band(aa, nb.math("SUBTRACT", hw, 0.45), 0.15), inJ)
    two = nb.math("LESS_THAN", ow, 0.5)
    yel = nb.math("MULTIPLY", nb.math("MULTIPLY", band(aa, 0.2, 0.15), two), inJ)
    lw = nb.math("DIVIDE", hw, nb.math("MAXIMUM", lanes, 1.0))
    dash = nb.math("LESS_THAN", nb.math("FRACT", nb.math("DIVIDE", along, 12.0)), 0.5)
    lane = nb.math("MULTIPLY", nb.math("MULTIPLY", band(aa, lw, 0.15), dash), nb.math("MULTIPLY", inJ, nb.math("GREATER_THAN", lanes, 1.5)))
    zeb = nb.math("MULTIPLY", nb.math("MULTIPLY", nb.math("GREATER_THAN", dj, 5.0), nb.math("LESS_THAN", dj, 10.0)),
                  nb.math("MULTIPLY", nb.math("GREATER_THAN", nb.math("FRACT", nb.math("DIVIDE", across, 1.1)), 0.5), nb.math("LESS_THAN", aa, nb.math("SUBTRACT", hw, 0.6))))
    white = nb.math("MAXIMUM", nb.math("MAXIMUM", edge, lane), zeb)
    white = nb.math("MULTIPLY", white, has)
    yel = nb.math("MULTIPLY", yel, has)
    n = noise(nb, None, 0.4, 6)
    asph = nb.mix(n.outputs[0], (0.028, 0.029, 0.032, 1), (0.05, 0.05, 0.055, 1))
    c = nb.mix(white, asph, (0.7, 0.7, 0.68, 1))
    c = nb.mix(yel, c, (0.75, 0.5, 0.06, 1))
    med = nb.math("SUBTRACT", kind, 1.0)
    medM = nb.math("MULTIPLY", nb.math("LESS_THAN", aa, nb.math("MULTIPLY", med, 0.5)), nb.math("GREATER_THAN", kind, 1.1))
    c = nb.mix(nb.math("MULTIPLY", medM, inJ), c, (0.06, 0.14, 0.035, 1))
    side = nb.math("LESS_THAN", kind, -0.5)
    curb = band(aa, nb.math("SUBTRACT", hw, 3.05), 0.3)
    pave = nb.mix(curb, nb.mix(n.outputs[0], (0.26, 0.245, 0.22, 1), (0.32, 0.30, 0.27, 1)), (0.5, 0.49, 0.46, 1))
    c = nb.mix(side, c, pave)
    principled(nb, out, c, rough=nb.mixf(white, 0.8, 0.5), spec=0.4)
    return m


def mat_fall():
    m, nb, out = new_mat("M_Waterfall")
    t, e, u = attr(nb, "fall_t"), attr(nb, "fall_edge"), attr(nb, "fall_u")
    cx = nb.node("ShaderNodeCombineXYZ")
    nb.link(nb.math("MULTIPLY", u, 0.07), cx.inputs[0])
    nb.link(nb.math("MULTIPLY", t, 10.0), cx.inputs[1])
    n1 = noise(nb, cx.outputs[0], 1.0, 6, 0.6)
    st = nb.smooth(0.35, 0.7, n1.outputs[0])
    a = nb.math("MULTIPLY", nb.math("ADD", 0.18, nb.math("MULTIPLY", st, 0.6)), nb.math("SUBTRACT", 1.0, nb.smooth(0.3, 0.95, t)))
    a = nb.math("MULTIPLY", a, e)
    base = nb.mix(nb.math("ADD", nb.math("MULTIPLY", st, 0.6), t), (0.42, 0.62, 0.70, 1), (0.95, 0.97, 1.0, 1))
    m.surface_render_method = "BLENDED"
    principled(nb, out, base, rough=0.35, emis=base, emis_k=0.15, alpha=a)
    return m


def mat_cloud_card():
    """cloud billboards: GPT Image cloud-puff (alpha kept), diffuse + translucent so the sun lights both sides"""
    m, nb, out = new_mat("M_Cloud_Card")
    uv = nb.node("ShaderNodeUVMap", uv_map="UVMap")
    t = tex(nb, IMG_CLOUD, uv.outputs[0], ext="CLIP")
    ca = attr(nb, "ca", "INSTANCER")
    lit = attr(nb, "lit", "INSTANCER")
    cam = nb.node("ShaderNodeCameraData")
    fade = nb.smooth(250.0, 1400.0, cam.outputs["View Distance"])
    a = nb.math("MULTIPLY", nb.math("MULTIPLY", t.outputs["Alpha"], ca), fade)
    col = nb.mix(1.0, t.outputs[0], nb.mixf(lit, 0.78, 1.0), "MULTIPLY")
    d = nb.node("ShaderNodeBsdfDiffuse")
    nb._in(d.inputs["Color"], col)
    tr = nb.node("ShaderNodeBsdfTranslucent")
    nb._in(tr.inputs["Color"], col)
    em = nb.node("ShaderNodeEmission")
    nb._in(em.inputs["Color"], col)
    em.inputs["Strength"].default_value = 0.08
    m1 = nb.node("ShaderNodeMixShader")
    m1.inputs[0].default_value = 0.4
    nb.link(d.outputs[0], m1.inputs[1])
    nb.link(tr.outputs[0], m1.inputs[2])
    ad = nb.node("ShaderNodeAddShader")
    nb.link(m1.outputs[0], ad.inputs[0])
    nb.link(em.outputs[0], ad.inputs[1])
    trn = nb.node("ShaderNodeBsdfTransparent")
    m2 = nb.node("ShaderNodeMixShader")
    nb.link(a, m2.inputs[0])
    nb.link(trn.outputs[0], m2.inputs[1])
    nb.link(ad.outputs[0], m2.inputs[2])
    nb.link(m2.outputs[0], out.inputs["Surface"])
    m.surface_render_method = "BLENDED"
    return m


def mat_cloud_sea():
    m, nb, out = new_mat("M_Cloud_Sea")
    tc = nb.node("ShaderNodeTexCoord")
    n = noise(nb, tc.outputs["Object"], 0.00022, 8, 0.58)
    n2 = noise(nb, tc.outputs["Object"], 0.0011, 6, 0.6)
    f = nb.math("ADD", n.outputs[0], nb.math("MULTIPLY", n2.outputs[0], 0.35))
    cov = nb.smooth(0.55, 0.85, f)
    base = nb.mix(cov, (0.33, 0.42, 0.56, 1), (0.92, 0.92, 0.93, 1))
    d = nb.node("ShaderNodeBsdfDiffuse")
    nb._in(d.inputs["Color"], base)
    tr = nb.node("ShaderNodeBsdfTranslucent")
    nb._in(tr.inputs["Color"], base)
    mx = nb.node("ShaderNodeMixShader")
    mx.inputs[0].default_value = 0.3
    nb.link(d.outputs[0], mx.inputs[1])
    nb.link(tr.outputs[0], mx.inputs[2])
    nb.link(bump(nb, f, 1.0, 60.0), d.inputs["Normal"])
    nb.link(mx.outputs[0], out.inputs["Surface"])
    return m


def mat_feature(name, color, stripe=0.0):
    m, nb, out = new_mat(name)
    base = color
    if stripe:
        uv = nb.node("ShaderNodeUVMap", uv_map="UVMap").outputs[0]
        s = sep(nb, uv)
        st = nb.math("LESS_THAN", nb.math("FRACT", nb.math("DIVIDE", s[0], stripe)), 0.5)
        base = nb.mix(st, color, tuple(c * 1.25 for c in color[:3]) + (1,))
    principled(nb, out, base, rough=0.8, spec=0.3)
    return m


def mat_pool():
    m, nb, out = new_mat("M_Pool")
    uv = nb.node("ShaderNodeUVMap", uv_map="UVMap").outputs[0]
    s = sep(nb, uv)
    w = nb.math("MULTIPLY", nb.math("LESS_THAN", nb.math("ABSOLUTE", s[0]), 12.5), nb.math("LESS_THAN", nb.math("ABSOLUTE", s[1]), 5.5))
    base = nb.mix(w, (0.62, 0.60, 0.55, 1), (0.02, 0.25, 0.42, 1))
    principled(nb, out, base, rough=nb.mixf(w, 0.7, 0.03), spec=0.5)
    return m


def mat_inst_color(name, rough=0.3, metal=0.4):
    """car bodies: per-instance colour from the page's traffic arrays"""
    m, nb, out = new_mat(name)
    principled(nb, out, attr(nb, "icol", "INSTANCER", "Color"), rough=rough, metal=metal, coat=0.6)
    return m


def mat_tree_leaf():
    m, nb, out = new_mat("M_Tree_Leaves")
    hue = attr(nb, "hue", "INSTANCER")
    n = noise(nb, None, 1.5, 3)
    base = nb.mix(hue, (0.035, 0.10, 0.025, 1), (0.10, 0.19, 0.035, 1))
    base = nb.mix(nb.math("MULTIPLY", n.outputs[0], 0.5), base, (0.02, 0.06, 0.015, 1))
    p = principled(nb, out, base, rough=0.75, spec=0.35)
    p.inputs["Subsurface Weight"].default_value = 0.1
    return m


M = {
    "glass": mat_facade("M_Glass_Office", 30.0, 40.0, 0.55, 0.12),
    "lmglass": mat_facade("M_Glass_Landmark", 18.0, 26.0, 0.45, 0.06),
    "resi": mat_grid("M_Residential", (3.6, 3.0), (0.2, 0.24), (0.035, 0.05, 0.06, 1), 0.74),
    "podium": mat_grid("M_Podium", (3.0, 5.0), (0.04, 0.12), (0.04, 0.06, 0.07, 1), 0.8),
    "village": mat_grid("M_Village", (3.0, 3.0), (0.3, 0.28), (0.03, 0.035, 0.04, 1), 0.95, 0.85),
    "concrete": mat_simple("M_Concrete_Roof", (0.72, 0.72, 0.72, 1), rough=0.85, noise_k=0.5),
    "metal": mat_simple("M_Metal", rough=0.28, metal=0.85),
    "shell": mat_simple("M_Lattice_Shell", rough=0.35, spec=0.6),
    "paint": mat_simple("M_Matte_Paint", rough=0.6),
    "deck": mat_simple("M_Bridge_Deck", (0.62, 0.61, 0.58, 1), rough=0.8, use_vcol=False),
    "rock": mat_rock(),
    "grass": mat_grass(),
    "net": mat_simple("M_Construction_Net", (0.06, 0.2, 0.08, 1), rough=0.9, use_vcol=False),
    "football": mat_feature("M_Field_Football", (0.05, 0.16, 0.03, 1), 10.0),
    "pool": mat_pool(),
    "basket": mat_feature("M_Court_Basketball", (0.04, 0.14, 0.28, 1)),
    "tennis": mat_feature("M_Court_Tennis", (0.03, 0.13, 0.17, 1)),
    "track": mat_feature("M_Field_Track", (0.32, 0.06, 0.04, 1)),
    "parking": mat_feature("M_Parking", (0.035, 0.036, 0.04, 1)),
    "ground": mat_ground(),
    "road": mat_road(),
    "fall": mat_fall(),
    "cloud": mat_cloud_card(),
    "cloudsea": mat_cloud_sea(),
    "carbody": mat_inst_color("M_Car_Paint"),
    "carglass": mat_simple("M_Car_Glass", (0.01, 0.012, 0.015, 1), rough=0.05, use_vcol=False, spec=0.9),
    "propbase": mat_simple("M_Prop_Base", rough=0.5, metal=0.3),
    "leaf": mat_tree_leaf(),
    "trunk": mat_simple("M_Tree_Trunk", (0.16, 0.10, 0.06, 1), rough=0.9, use_vcol=False),
}
# page material id -> key (roof faces of glass/residential/podium/village go to the concrete roof material)
MATID = {0: "glass", 1: "resi", 2: "podium", 3: "concrete", 4: "village", 5: "metal", 6: "shell", 7: "lmglass", 8: "paint", 9: "deck",
         10: "rock", 11: "grass", 12: "football", 13: "pool", 14: "basket", 15: "tennis", 16: "track", 19: "parking", 20: "net", 18: "paint"}
ROOFED = {0, 1, 2, 4}


# ---------------------------------------------------------------- mesh building
def build_mesh(name, co, tris, collection, normals=None, cols=None, uvs=None, face_mat=None, attrs=None, int_attrs=None, smooth=True):
    """co: (N,3) blender coords, tris: (T,3) int; face_mat: (T,) list of material keys index into keys"""
    me = bpy.data.meshes.new(name)
    nv, nt = len(co), len(tris)
    me.vertices.add(nv)
    me.vertices.foreach_set("co", co.astype(np.float32).ravel())
    me.loops.add(nt * 3)
    me.loops.foreach_set("vertex_index", tris.astype(np.int32).ravel())
    me.polygons.add(nt)
    me.polygons.foreach_set("loop_start", np.arange(0, nt * 3, 3, dtype=np.int32))
    me.update(calc_edges=True)
    if cols is not None:
        ca = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
        rgba = np.concatenate([cols, np.ones((nv, 1), np.float32)], 1)
        ca.data.foreach_set("color", rgba.astype(np.float32).ravel())
    if uvs is not None:
        uvl = me.uv_layers.new(name="UVMap")
        uvl.data.foreach_set("uv", uvs[tris.ravel()].astype(np.float32).ravel())
    for k, v in (attrs or {}).items():
        a = me.attributes.new(k, "FLOAT", "POINT")
        a.data.foreach_set("value", v.astype(np.float32))
    for k, v in (int_attrs or {}).items():
        a = me.attributes.new(k, "INT", "POINT")
        a.data.foreach_set("value", v.astype(np.int32))
    if face_mat is not None:
        keys = sorted(set(face_mat.tolist()))
        for k in keys:
            me.materials.append(M[k])
        lut = {k: i for i, k in enumerate(keys)}
        me.polygons.foreach_set("material_index", np.array([lut[k] for k in face_mat], np.int32))
    me.polygons.foreach_set("use_smooth", np.full(nt, smooth, bool))
    if normals is not None:
        nn = normals / np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-6)
        me.normals_split_custom_set_from_vertices(nn.astype(np.float32))
    me.validate(clean_customdata=False)
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    return ob


def mesh13(prefix):
    v = load(prefix + "_v").reshape(-1, 13)
    i = load(prefix + "_i", np.uint32).reshape(-1, 3)
    return v, i


def face_keys(v, tris):
    mat = np.rint(v[tris[:, 0], 12]).astype(int)
    ny = v[tris[:, 0], 4]
    capu = v[tris[:, 0], 9] < -0.5
    keys = []
    for m_, y, cu in zip(mat, ny, capu):
        if m_ in ROOFED and (y > 0.6 or cu):
            keys.append("concrete")
        else:
            keys.append(MATID.get(int(m_), "paint"))
    return np.array(keys)


def emit13(name, v, tris, collection, offset_z=0.0):
    # the page draws without back-face culling and flips normals in the shader, so its winding is
    # mostly clockwise; re-wind every triangle so the geometric normal agrees with the page normal
    a, b, c = v[tris[:, 0], :3], v[tris[:, 1], :3], v[tris[:, 2], :3]
    vn = v[tris[:, 0], 3:6] + v[tris[:, 1], 3:6] + v[tris[:, 2], 3:6]
    flip = (np.cross(b - a, c - a) * vn).sum(1) < 0
    tris = tris.copy()
    tris[flip] = tris[flip][:, [0, 2, 1]]
    used = np.unique(tris)
    remap = np.full(len(v), -1, np.int64)
    remap[used] = np.arange(len(used))
    sub = v[used]
    t = remap[tris]
    co = to_b(sub[:, 0:3])
    co[:, 2] += offset_z
    nrm = to_b(sub[:, 3:6])
    return build_mesh(name, co, t, collection, normals=nrm, cols=sub[:, 6:9], uvs=sub[:, 9:11], face_mat=face_keys(sub, t),
                      int_attrs={"building_id": np.rint(sub[:, 11]).astype(int)})


print("building city ...")
cv, ci = mesh13("city")
lm_tris = ci[: META["lmIdx"] // 3]
gen_tris = ci[META["lmIdx"] // 3:]
lm_bid = np.rint(cv[lm_tris[:, 0], 11]).astype(int)
C_LM = coll("Landmarks", C_CITY)
for L in META["landmarks"]:
    sel = lm_tris[lm_bid == L["i"]]
    if len(sel):
        ob = emit13("LM_%02d_%s" % (L["i"], L["en"] if L.get("en") else L["k"]), cv, sel, C_LM)
        ob["name_zh"] = L["name"]
        ob["height_m"] = L["h"]
        ob["source"] = "坐标与高度：维基百科；外形为按实物简化的示意（与网页一致）"
gob = emit13("Generated_Buildings", cv, gen_tris, C_CITY)
gob["source"] = "程序生成楼体（所在街区来自真实 OSM 路网，楼体本身为生成）"

bv, bi = mesh13("bridge")
emit13("Bridges", bv, bi, C_CITY)
fv, fi = mesh13("feat")
emit13("Sports_Pools_Parking", fv, fi, C_CITY, offset_z=0.05)

print("building island ...")
iv, ii = mesh13("island")
emit13("Island_Body_and_Islets", iv, ii, C_ISLE)

# ---------------------------------------------------------------- ground disk (page isleR outline)
R0, thH, lobe = META["isle"]["R0"], META["isle"]["thH"], META["isle"]["lobe"]
RR = META["R"]


def isleR(th):
    b = R0 * (1 + 0.05 * np.sin(3 * th + 1) + 0.035 * np.sin(5 * th + 2) + 0.02 * np.sin(9 * th + 0.5) + 0.012 * np.sin(17 * th + 3.1))
    d = (th - thH + np.pi) % (2 * np.pi) - np.pi
    l = lobe * np.exp(-((d / 0.16) ** 2))
    m = np.maximum(b, l)
    return m + 60 * np.log(np.exp((b - m) / 60) + np.exp((l - m) / 60))


N = 640
rings = 48
th = np.arange(N) / N * 2 * np.pi
pts = [np.zeros((1, 3))]
for k in range(1, rings + 1):
    f = k / rings
    r = isleR(th) * f
    pts.append(np.stack([np.cos(th) * r, np.sin(th) * r, np.zeros(N)], 1))   # page (x, z)
P = np.concatenate(pts)
tris = [[0, 1 + (i + 1) % N, 1 + i] for i in range(N)]
for k in range(rings - 1):
    a0, b0 = 1 + k * N, 1 + (k + 1) * N
    for i in range(N):
        j = (i + 1) % N
        tris += [[a0 + i, a0 + j, b0 + j], [a0 + i, b0 + j, b0 + i]]
tris = np.array(tris)
co = np.stack([P[:, 0], -P[:, 1], np.zeros(len(P))], 1)
uv = np.stack([(P[:, 0] + RR) / (2 * RR), 1 - (P[:, 1] + RR) / (2 * RR)], 1)
gd = build_mesh("Ground_and_Bay", co, tris, C_GROUND, uvs=uv)
gd.data.materials.append(M["ground"])
gd.data.polygons.foreach_set("use_smooth", np.zeros(len(tris), bool))
gd.data.polygons.foreach_set("material_index", np.zeros(len(tris), np.int32))

# ---------------------------------------------------------------- roads
print("building roads ...")
rv = load("road_v").reshape(-1, 11)
co = to_b(rv[:, 0:3])
kind = rv[:, 10]
co[:, 2] += np.where(kind < -0.5, 0.12, 0.2)
t = np.arange(len(rv)).reshape(-1, 3)
rd = build_mesh("Roads_and_Sidewalks", co, t, C_GROUND, attrs={
    "r_across": rv[:, 3], "r_along": rv[:, 4], "r_dj": np.minimum(rv[:, 5], rv[:, 6]), "r_hw": rv[:, 7], "r_lanes": rv[:, 8], "r_ow": rv[:, 9], "r_kind": rv[:, 10]},
    smooth=False)
rd.data.materials.append(M["road"])
rd["source"] = "道路 © OpenStreetMap 贡献者（ODbL）"

# ---------------------------------------------------------------- waterfalls
fv6 = load("fall_v").reshape(-1, 6)
t = np.arange(len(fv6)).reshape(-1, 3)
fo = build_mesh("Waterfalls", to_b(fv6[:, 0:3]), t, C_ISLE, attrs={"fall_u": fv6[:, 3], "fall_t": fv6[:, 4], "fall_edge": fv6[:, 5]})
fo.data.materials.append(M["fall"])
fo.visible_shadow = False

# ---------------------------------------------------------------- cloud sea
CS = 400000   # large enough that its edge sits below the horizon haze
cs = build_mesh("Cloud_Sea", np.array([[-CS, -CS, -1900], [CS, -CS, -1900], [CS, CS, -1900], [-CS, CS, -1900]], float),
                np.array([[0, 1, 2], [0, 2, 3]]), C_SKY, smooth=False)
cs.data.materials.append(M["cloudsea"])


# ---------------------------------------------------------------- instancing helpers
def template(name, co, tris, keys, normals=None, cols=None):
    ob = build_mesh(name, co, tris, C_TPL, normals=normals, cols=cols, face_mat=np.array(keys))
    return ob


def gn_instancer(name, tpl, billboard_cam=None):
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    n, l = ng.nodes, ng.links
    gi, go = n.new("NodeGroupInput"), n.new("NodeGroupOutput")
    oi = n.new("GeometryNodeObjectInfo")
    oi.inputs["Object"].default_value = tpl
    oi.transform_space = "ORIGINAL"
    ip = n.new("GeometryNodeInstanceOnPoints")
    sc = n.new("GeometryNodeInputNamedAttribute")
    sc.data_type = "FLOAT_VECTOR"
    sc.inputs["Name"].default_value = "scl"
    l.new(gi.outputs[0], ip.inputs["Points"])
    l.new(oi.outputs["Geometry"], ip.inputs["Instance"])
    l.new(sc.outputs["Attribute"], ip.inputs["Scale"])
    if billboard_cam is None:
        rt = n.new("GeometryNodeInputNamedAttribute")
        rt.data_type = "FLOAT_VECTOR"
        rt.inputs["Name"].default_value = "rot"
        l.new(rt.outputs["Attribute"], ip.inputs["Rotation"])
    else:   # face the camera, keep the card upright
        co_ = n.new("GeometryNodeObjectInfo")
        co_.inputs["Object"].default_value = billboard_cam
        co_.transform_space = "ORIGINAL"
        pos = n.new("GeometryNodeInputPosition")
        vm = n.new("ShaderNodeVectorMath")
        vm.operation = "SUBTRACT"
        l.new(co_.outputs["Location"], vm.inputs[0])
        l.new(pos.outputs[0], vm.inputs[1])
        a1 = n.new("FunctionNodeAlignRotationToVector")
        a1.axis = "Z"
        l.new(vm.outputs[0], a1.inputs["Vector"])
        a2 = n.new("FunctionNodeAlignRotationToVector")
        a2.axis = "Y"
        a2.pivot_axis = "Z"
        a2.inputs["Vector"].default_value = (0, 0, 1)
        l.new(a1.outputs[0], a2.inputs["Rotation"])
        l.new(a2.outputs[0], ip.inputs["Rotation"])
    l.new(ip.outputs[0], go.inputs[0])
    return ng


def point_cloud(name, pos, collection, tpl, rot=None, scl=None, fattrs=None, cattrs=None, billboard_cam=None):
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(pos))
    me.vertices.foreach_set("co", pos.astype(np.float32).ravel())
    for k, v in (("rot", rot), ("scl", scl)):
        if v is not None:
            a = me.attributes.new(k, "FLOAT_VECTOR", "POINT")
            a.data.foreach_set("vector", v.astype(np.float32).ravel())
    for k, v in (fattrs or {}).items():
        a = me.attributes.new(k, "FLOAT", "POINT")
        a.data.foreach_set("value", v.astype(np.float32))
    for k, v in (cattrs or {}).items():
        a = me.attributes.new(k, "FLOAT_COLOR", "POINT")
        a.data.foreach_set("color", np.concatenate([v, np.ones((len(v), 1))], 1).astype(np.float32).ravel())
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    md = ob.modifiers.new("Instances", "NODES")
    md.node_group = gn_instancer("GN_" + name, tpl, billboard_cam)
    return ob


# ---------------------------------------------------------------- trees (same templates as treeTemplate() in the page)
def tree_template(palm):
    co, tri, keys, nrm = [], [], [], []
    th, tr = (9, 0.32) if palm else (3.2, 0.35)
    for i in range(6):
        a0, a1 = i / 6 * 2 * math.pi, (i + 1) / 6 * 2 * math.pi
        b = len(co)
        dx = 0.6 if palm else 0
        for (x, y, z) in ((math.cos(a0) * tr, 0, math.sin(a0) * tr), (math.cos(a1) * tr, 0, math.sin(a1) * tr),
                          (math.cos(a1) * tr * 0.7 + dx, th, math.sin(a1) * tr * 0.7), (math.cos(a0) * tr * 0.7 + dx, th, math.sin(a0) * tr * 0.7)):
            co.append((x, y, z))
            nrm.append((x, 0, z))
        tri += [(b, b + 1, b + 2), (b, b + 2, b + 3)]
        keys += ["trunk", "trunk"]
    if not palm:
        t = (1 + 5 ** 0.5) / 2
        ico = np.array([[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t], [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]], float)
        ico /= np.linalg.norm(ico, axis=1, keepdims=True)
        F = [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]]
        b = len(co)
        for p in ico:
            co.append((p[0] * 2.9, 5.4 + p[1] * 2.9 * 0.85, p[2] * 2.9))
            nrm.append(tuple(p))
        for f in F:
            tri.append(tuple(b + k for k in f))
            keys.append("leaf")
    else:
        top = (0.6, th, 0)
        for i in range(7):
            a = i / 7 * 2 * math.pi
            ca, sa = math.cos(a), math.sin(a)
            tip = (top[0] + ca * 4.2, th - 1.8, sa * 4.2)
            mid = (top[0] + ca * 2.2, th + 0.7, sa * 2.2)
            side = (-sa * 0.9, 0, ca * 0.9)
            b = len(co)
            co += [top, (mid[0] + side[0], mid[1], mid[2] + side[2]), tip, (mid[0] - side[0], mid[1], mid[2] - side[2])]
            nrm += [(0, 1, 0), (ca * 0.3, 0.95, sa * 0.3), (ca * 0.5, 0.8, sa * 0.5), (ca * 0.3, 0.95, sa * 0.3)]
            tri += [(b, b + 1, b + 2), (b, b + 2, b + 3)]
            keys += ["leaf", "leaf"]
    co = to_b(np.array(co, float))
    return template("TPL_Palm" if palm else "TPL_Tree", co, np.array(tri), keys, normals=to_b(np.array(nrm, float)))


print("instancing trees and props ...")
T_ROUND, T_PALM = tree_template(False), tree_template(True)
for k, label in ((0, "Shrubs"), (1, "Street_Trees"), (2, "Palms"), (3, "Islet_and_Roof_Trees")):
    a = load("tree%d" % k).reshape(-1, 5)
    x, z, s, h, y = a.T
    pos = np.stack([x, -z, y], 1)
    scl = np.stack([s, s, s * (0.85 + h * 0.35)], 1)
    rot = np.stack([np.zeros_like(h), np.zeros_like(h), -h * 40], 1)
    point_cloud("Trees_" + label, pos, C_PROPS, T_PALM if META["inst"]["tree%d" % k]["palm"] else T_ROUND, rot, scl, fattrs={"hue": h})


def prop_template(name):
    tv = load(name + "_tv").reshape(-1, 10)
    ti = load(name + "_ti", np.uint16).reshape(-1, 3).astype(np.int64)
    part = np.rint(tv[ti[:, 0], 9]).astype(int)
    keys = ["carglass" if p >= 2 else "carbody" if p == 1 else "propbase" for p in part]
    return template("TPL_" + name, to_b(tv[:, 0:3]), ti, keys, normals=to_b(tv[:, 3:6]), cols=tv[:, 6:9])


TPLS = {}
for name, src in (("Street_Lamps", "lamp"), ("Parked_Cars", "parked"), ("Traffic_Snapshot", "car"), ("Traffic_Signals", "signal"), ("Bus_Stops", "busstop")):
    tpl_key = "car" if src in ("car", "parked") else src
    if tpl_key not in TPLS:
        TPLS[tpl_key] = prop_template(tpl_key)
    a = load(src + "_inst").reshape(-1, 8)
    a = a[a[:, 7] > 0.01] if src == "car" else a
    pos = to_b(a[:, 0:3])
    sx = a[:, 7]
    scl = np.stack([sx, np.ones_like(sx), np.where(sx > 1.5, 1.75, 1.0)], 1)
    rot = np.stack([np.zeros_like(sx), np.zeros_like(sx), -a[:, 3]], 1)
    point_cloud(name, pos, C_PROPS, TPLS[tpl_key], rot, scl, cattrs={"icol": a[:, 4:7]})

# ---------------------------------------------------------------- camera, cloud cards
cam_data = bpy.data.cameras.new("Camera")
cam_data.sensor_fit = "VERTICAL"
cam_data.angle_y = 0.78
cam_data.clip_start = 5.0
cam_data.clip_end = 600000.0
cam = bpy.data.objects.new("Camera", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam


def place_camera(eye_page, tgt_page, fov=0.78):
    e = to_b(np.array([eye_page], float))[0]
    t = to_b(np.array([tgt_page], float))[0]
    cam.location = e
    d = t - e
    import mathutils
    cam.rotation_euler = mathutils.Vector(d).to_track_quat("-Z", "Y").to_euler()
    cam.data.angle_y = fov


def orbit(tx, tz, ty, yaw, pitch, dist):
    cp = math.cos(pitch)
    return [tx + math.sin(yaw) * cp * dist, math.sin(pitch) * dist + ty, tz + math.cos(yaw) * cp * dist], [tx, ty, tz]


place_camera(*orbit(0, 0, -350, -0.85, 0.28, 9200))   # the page's HOME view

card = template("TPL_Cloud_Card", np.array([[-1.5, -1, 0], [1.5, -1, 0], [1.5, 1, 0], [-1.5, 1, 0]], float), np.array([[0, 1, 2], [0, 2, 3]]), ["cloud", "cloud"])
card.data.uv_layers.new(name="UVMap").data.foreach_set("uv", np.array([0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1], np.float32))
card.data.polygons.foreach_set("use_smooth", np.zeros(2, bool))

# the page's own puffs (upper + lower layers + waterfall mist)
cl = np.array(META["clouds"], float)
pos = to_b(cl[:, 0:3])
s = cl[:, 3] * 0.55
point_cloud("Clouds_Page_Puffs", pos, C_SKY, card, scl=np.stack([s, s, s], 1), fattrs={"lit": cl[:, 4], "ca": cl[:, 5]}, billboard_cam=cam)
# a denser cloud sea skirt around the island, just above the cloud-sea plane
rng = np.random.default_rng(7)
n = 650
ang = rng.uniform(0, 2 * np.pi, n)
rad = np.sqrt(rng.uniform(0, 1, n)) * 26000
keep = rad > 4800
ang, rad = ang[keep], rad[keep]
pos = np.stack([np.cos(ang) * rad, np.sin(ang) * rad, rng.uniform(-1900, -1780, len(ang))], 1)
s = rng.uniform(380, 950, len(ang)) * (1 + rad / 26000)
point_cloud("Clouds_Sea_Skirt", pos, C_SKY, card, scl=np.stack([s, s, s * 0.6], 1),
            fattrs={"lit": rng.uniform(0.6, 1.0, len(ang)), "ca": rng.uniform(0.45, 0.8, len(ang))}, billboard_cam=cam)

# ---------------------------------------------------------------- sun, sky, render settings
sd = page_sun(TOD)
sdb = to_b(np.array([sd]))[0]
sun_data = bpy.data.lights.new("Sun", "SUN")
sun_data.energy = 5.0
sun_data.angle = math.radians(0.8)
sun_data.color = (1.0, 0.86, 0.70)
sun = bpy.data.objects.new("Sun", sun_data)
scene.collection.objects.link(sun)
import mathutils
sun.rotation_euler = mathutils.Vector(-sdb).to_track_quat("-Z", "Y").to_euler()

world = bpy.data.worlds.new("Sky")
scene.world = world
world.use_nodes = True
wn = world.node_tree
wn.nodes.clear()
wb = NB(wn)
sky = wb.node("ShaderNodeTexSky", sky_type="NISHITA")
sky.sun_disc = False
sky.sun_elevation = math.asin(sdb[2])
sky.sun_rotation = math.atan2(sdb[1], sdb[0]) - math.pi / 2 + math.pi
sky.altitude = 1500.0
sky.air_density = 1.3
sky.dust_density = 0.35
sky.ozone_density = 1.6
bg = wb.node("ShaderNodeBackground", Strength=0.22)
wb.link(sky.outputs[0], bg.inputs[0])
wo = wb.node("ShaderNodeOutputWorld")
wb.link(bg.outputs[0], wo.inputs[0])
world.mist_settings.start = 3000
world.mist_settings.depth = 70000
world.mist_settings.falloff = "QUADRATIC"

r = scene.render
r.engine = "CYCLES"
r.resolution_x, r.resolution_y, r.resolution_percentage = 1600, 900, 100
r.film_transparent = True
r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGB"
cy = scene.cycles
cy.device = "CPU"
cy.samples = 96
cy.use_adaptive_sampling = True
cy.adaptive_threshold = 0.02
cy.use_denoising = True
cy.denoiser = "OPENIMAGEDENOISE"
cy.max_bounces = 4
cy.diffuse_bounces = 2
cy.glossy_bounces = 2
cy.transmission_bounces = 2
cy.transparent_max_bounces = 24
cy.caustics_reflective = False
cy.caustics_refractive = False
cy.sample_clamp_indirect = 6.0
cy.use_auto_tile = True
vs = scene.view_settings
vs.view_transform = "AgX"
for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
    try:
        vs.look = look
        break
    except TypeError:
        pass
vs.exposure = 0.15
scene.eevee.use_shadows = True
vl = scene.view_layers[0]
vl.use_pass_mist = True
vl.use_pass_environment = True

# compositor: aerial haze from the mist pass, then the sky behind (film is transparent)
scene.use_nodes = True
ct = scene.node_tree
ct.nodes.clear()
cb = NB(ct)
rl = cb.node("CompositorNodeRLayers")
haze = cb.node("CompositorNodeMixRGB", blend_type="MIX")
haze.inputs[2].default_value = (0.66, 0.72, 0.82, 1)
mk = cb.node("CompositorNodeMath", operation="MULTIPLY")
mk.inputs[1].default_value = 0.85
cb.link(rl.outputs["Mist"], mk.inputs[0])
cb.link(mk.outputs[0], haze.inputs[0])
cb.link(rl.outputs["Image"], haze.inputs[1])
sa = cb.node("CompositorNodeSetAlpha")
sa.mode = "REPLACE_ALPHA"
cb.link(haze.outputs[0], sa.inputs["Image"])
cb.link(rl.outputs["Alpha"], sa.inputs["Alpha"])
ao = cb.node("CompositorNodeAlphaOver")
cb.link(rl.outputs["Env"], ao.inputs[1])
cb.link(sa.outputs[0], ao.inputs[2])
glare = cb.node("CompositorNodeGlare", glare_type="FOG_GLOW", quality="MEDIUM")
try:
    glare.threshold = 1.2
    glare.size = 7
except AttributeError:
    pass
cb.link(ao.outputs[0], glare.inputs[0])
hs = cb.node("CompositorNodeHueSat")
hs.inputs["Saturation"].default_value = 1.12
cb.link(glare.outputs[0], hs.inputs["Image"])
comp = cb.node("CompositorNodeComposite")
cb.link(hs.outputs[0], comp.inputs[0])

scene["source_note"] = ("道路 © OpenStreetMap 贡献者（ODbL）；11 座地标坐标与高度来自维基百科（外形为简化示意）；"
                        "海岸线与绿地由路网推算；其余楼体、球场、停车场、车辆为程序生成。纹理素材由内置 GPT Image 生成。")
scene["tod"] = TOD

# ---------------------------------------------------------------- save (compressed, textures packed)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
nobj = len(bpy.data.objects)
ntri = sum(len(o.data.polygons) for o in bpy.data.objects if o.type == "MESH" and o.users_collection[0] != C_TPL and not o.modifiers)
print("saved %s  objects=%d  static tris=%d" % (OUT, nobj, ntri))
