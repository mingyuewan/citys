"""Build the embedded dataset for 深圳湾空中城市.

Inputs : OSM road network of Shenzhen (shapefile, ni1o1/pygeo-tutorial) + landmark table (Wikipedia).
Outputs: data/szbay.json  (roads, land/green mask PNG, buildings, landmarks, labels)
         data/debug.png    (top-down check image)
"""
import base64
import io
import json
import math
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from shp import read_dbf, read_shp  # noqa: E402

SRC = sys.argv[1]
OUT = sys.argv[2]

LAT0, LON0 = 22.5150, 113.9420          # 后海 · 华润大厦一带
R = 3200                                # half-size of the square, metres
RES = 4.0                               # raster metres / px
N = int(2 * R / RES)
KY = 110574.0
KX = 111320.0 * math.cos(math.radians(LAT0))


def to_xz(lon, lat):
    return ((lon - LON0) * KX, (LAT0 - lat) * KY)


def to_px(x, z):
    return ((x + R) / RES, (z + R) / RES)


# ---------------------------------------------------------------- roads
st, bb, shapes = read_shp(SRC + "/shenzhen_osmroad.shp")
_, recs = read_dbf(SRC + "/shenzhen_osmroad.dbf")

VEH_W = {  # full carriageway width (m) used for blocks / drawing
    "motorway": 24, "trunk": 22, "primary": 18, "secondary": 14, "tertiary": 10,
    "motorway_link": 8, "trunk_link": 8, "primary_link": 7, "secondary_link": 7, "tertiary_link": 6,
    "residential": 7, "unclassified": 7, "living_street": 6, "service": 4.5,
}
FOOT = {"footway", "cycleway", "path", "pedestrian", "steps", "track"}
CLASS_ORDER = ["motorway", "trunk", "primary", "secondary", "tertiary", "motorway_link", "trunk_link", "primary_link",
               "secondary_link", "tertiary_link", "residential", "unclassified", "living_street", "service",
               "footway", "cycleway", "path", "pedestrian", "steps", "track"]

dlon = (R + 200) / KX
dlat = (R + 200) / KY
roads = []
for s, r in zip(shapes, recs):
    if not s:
        continue
    x0, y0, x1, y1 = s["bbox"]
    if x1 < LON0 - dlon or x0 > LON0 + dlon or y1 < LAT0 - dlat or y0 > LAT0 + dlat:
        continue
    fc = r["fclass"]
    if fc not in CLASS_ORDER:
        continue
    for part in s["parts"]:
        pts = [to_xz(lon, lat) for lon, lat in part]
        roads.append({
            "fc": fc, "name": r["name"], "bridge": r["bridge"] == "T", "tunnel": r["tunnel"] == "T",
            "oneway": r["oneway"] == "F" and False or r["oneway"] in ("T", "F") and r["oneway"] == "F",
            "ow": r["oneway"], "layer": int(float(r["layer"] or 0)), "pts": pts, "id": r["osm_id"],
        })
print("roads in box:", len(roads))


def poly_px(pts):
    return np.array([to_px(x, z) for x, z in pts], dtype=np.float32)


def draw_lines(img, sel, width_fn, val=255):
    for rd in sel:
        w = width_fn(rd)
        if w <= 0:
            continue
        p = np.round(poly_px(rd["pts"]) * 8).astype(np.int32)
        cv2.polylines(img, [p], False, val, thickness=max(1, int(round(w / RES))), lineType=cv2.LINE_8, shift=3)


# ---------------------------------------------------------------- land mask
surface = [rd for rd in roads if not rd["tunnel"]]
skel = np.zeros((N, N), np.uint8)
# long bridges over the bay must not create land
def length(rd):
    p = rd["pts"]
    return sum(math.hypot(p[i + 1][0] - p[i][0], p[i + 1][1] - p[i][1]) for i in range(len(p) - 1))


def is_sea_bridge(rd):
    return rd["bridge"] and ("Shenzhen Bay Bridge" in rd["name"] or "深圳湾公路大桥" in rd["name"] or
                             (rd["fc"].startswith("motorway") and rd["pts"] and to_lat(rd) < 22.494))


def to_lat(rd):
    return LAT0 - min(z for _, z in rd["pts"]) / KY * -1 if False else LAT0 - max(z for _, z in rd["pts"]) / KY


draw_lines(skel, [rd for rd in surface if not is_sea_bridge(rd)], lambda rd: 4)
k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * 45 + 1, 2 * 45 + 1))   # ~180 m radius
land = cv2.morphologyEx(skel, cv2.MORPH_CLOSE, k_close)
# fill enclosed holes (lakes inside parks stay land; real lakes are not in the data anyway)
inv = (land == 0).astype(np.uint8)
n_cc, lab, stats, _ = cv2.connectedComponentsWithStats(inv, 4)
for i in range(1, n_cc):
    x, y, w, h, a = stats[i]
    touches = x == 0 or y == 0 or x + w >= N or y + h >= N
    if not touches and a < 120000:      # < ~1.9 km² enclosed → land
        land[lab == i] = 255
# keep only water connected to the real sea: south edge, east edge south of 22.522, west edge south of 22.51
wat = (land == 0).astype(np.uint8)
n_w, wlab, wst, _ = cv2.connectedComponentsWithStats(wat, 4)
z_e = int(((LAT0 - 22.522) * KY + R) / RES)
z_w = int(((LAT0 - 22.510) * KY + R) / RES)
for i in range(1, n_w):
    comp = wlab == i
    keep = comp[-1, :].any() or comp[max(0, z_e):, -1].any() or comp[max(0, z_w):, 0].any()
    if not keep or wst[i][4] < 20000:
        land[comp] = 255
# a little shoreline beyond the outermost promenade
land = cv2.dilate(land, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
land = cv2.GaussianBlur(land, (0, 0), 2.0)
land = (land > 127).astype(np.uint8)
print("land fraction:", land.mean())

# ---------------------------------------------------------------- blocks
veh = [rd for rd in surface if rd["fc"] in VEH_W and not (rd["bridge"] and rd["layer"] >= 1 and rd["fc"].endswith("link"))]
roadmask = np.zeros((N, N), np.uint8)
draw_lines(roadmask, veh, lambda rd: VEH_W[rd["fc"]] + 6)   # + sidewalks
blocks = ((land > 0) & (roadmask == 0)).astype(np.uint8)
n_b, blab, bstats, bcent = cv2.connectedComponentsWithStats(blocks, 4)

footmask = np.zeros((N, N), np.uint8)
draw_lines(footmask, [rd for rd in surface if rd["fc"] in FOOT], lambda rd: RES)
servmask = np.zeros((N, N), np.uint8)
draw_lines(servmask, [rd for rd in surface if rd["fc"] == "service"], lambda rd: RES)
water = (land == 0).astype(np.uint8)
near_water = cv2.dilate(water, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))  # 60 m

foot_cnt = np.bincount(blab.ravel(), weights=(footmask > 0).ravel(), minlength=n_b)
serv_cnt = np.bincount(blab.ravel(), weights=(servmask > 0).ravel(), minlength=n_b)
nw_cnt = np.bincount(blab.ravel(), weights=(near_water > 0).ravel(), minlength=n_b)

# ---------------------------------------------------------------- landmarks (Wikipedia coordinates & heights)
LANDMARKS = [
    # name, lon, lat, height, shape, size(w,d) or radius, rotation(deg)
    ("华润大厦（春笋）", 113.94167, 22.51694, 392.5, "circle", 33, 0, "China Resources Headquarters", "bamboo"),
    ("深圳湾一号 T7", 113.93722, 22.50861, 341.4, "rect", (44, 44), 20, "One Shenzhen Bay Tower 7", "taper"),
    ("中洲控股金融中心", 113.9285, 22.5205, 300.8, "rect", (46, 46), 10, "Zhongzhou Holdings Financial Center", "roundtaper"),
    ("腾讯滨海大厦 南塔", 113.9302, 22.5250, 248.0, "rect", (58, 34), 18, "Tencent Binhai Mansion", "tencentS"),
    ("腾讯滨海大厦 北塔", 113.9310, 22.5262, 194.0, "rect", (58, 34), 18, "Tencent Binhai Mansion", "tencentN"),
    ("深圳湾创新科技中心 T1", 113.94139, 22.53139, 311.1, "rect", (48, 48), 0, "Shenzhen Bay ITC Tower 1", "tiered"),
    ("深圳湾创新科技中心 T2", 113.94060, 22.53030, 247.2, "rect", (40, 40), 0, "Shenzhen Bay ITC Tower 2", "tiered"),
    ("汉京金融中心", 113.93164, 22.54348, 358.9, "rect", (42, 54), 5, "Hanking Center", "hanking"),
    ("汇云中心", 113.9653417, 22.5269083, 359.2, "rect", (48, 48), 0, "Huiyun Center", "taper"),
    ("深圳湾体育中心（春茧）", 113.94583, 22.52083, 46.0, "ellipse", (290, 210), 30, "Shenzhen Bay Sports Center", "cocoon"),
    ("深圳湾文化广场", 113.94000, 22.51500, 36.0, "ellipse", (190, 120), 25, "Shenzhen Bay Cultural Plaza", "pebble"),
]
lm_out = []
lm_clear = np.zeros((N, N), np.uint8)
for name, lon, lat, h, shape, size, rot, en, kind in LANDMARKS:
    cx, cz = to_xz(lon, lat)
    a = math.radians(rot)
    if shape == "circle":
        ring = [(cx + size * math.cos(t * 2 * math.pi / 28), cz + size * math.sin(t * 2 * math.pi / 28)) for t in range(28)]
    elif shape == "ellipse":
        ring = []
        for t in range(40):
            u, v = size[0] / 2 * math.cos(t * 2 * math.pi / 40), size[1] / 2 * math.sin(t * 2 * math.pi / 40)
            ring.append((cx + u * math.cos(a) - v * math.sin(a), cz + u * math.sin(a) + v * math.cos(a)))
    else:
        w, d = size
        ring = []
        for u, v in [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]:
            ring.append((cx + u * math.cos(a) - v * math.sin(a), cz + u * math.sin(a) + v * math.cos(a)))
    if abs(cx) > R or abs(cz) > R:
        continue
    pp = np.round(poly_px(ring) * 8).astype(np.int32)
    cv2.fillPoly(lm_clear, [pp], 255, shift=3)
    lm_out.append({"n": name, "en": en, "h": h, "r": [[round(x, 1), round(z, 1)] for x, z in ring],
                   "dome": shape == "ellipse", "k": kind, "c": [round(cx, 1), round(cz, 1)],
                   "s": [size, size] if shape == "circle" else list(size), "rot": rot})
lm_clear = cv2.dilate(lm_clear, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * 12 + 1, 2 * 12 + 1)))

# ---------------------------------------------------------------- block classification + building fill
rng = np.random.default_rng(20261021)
park_mask = np.zeros((N, N), np.uint8)
buildings = []
HOUHAI = to_xz(113.9405, 22.5185)
SCIPARK = to_xz(113.9470, 22.5370)
SHEKOU = to_xz(113.9170, 22.4930)


def zone_of(x, z):
    dh = math.hypot(x - HOUHAI[0], z - HOUHAI[1])
    ds = math.hypot(x - SCIPARK[0], z - SCIPARK[1])
    dk = math.hypot(x - SHEKOU[0], z - SHEKOU[1])
    if dh < 900:
        return "cbd"
    if ds < 900:
        return "tech"
    if dk < 1300:
        return "shekou"
    return "res"


ZONES = {  # footprint w range, d range, spacing gap, height range, tall chance
    "cbd": dict(w=(32, 55), d=(30, 50), gap=(22, 40), h=(60, 200), tall=0.35, tallh=(200, 290)),
    "tech": dict(w=(35, 70), d=(22, 40), gap=(18, 30), h=(40, 140), tall=0.15, tallh=(150, 230)),
    "shekou": dict(w=(18, 45), d=(14, 30), gap=(10, 20), h=(15, 70), tall=0.12, tallh=(80, 160)),
    "res": dict(w=(22, 36), d=(18, 30), gap=(12, 22), h=(55, 120), tall=0.1, tallh=(120, 170)),
    "village": dict(w=(10, 16), d=(10, 16), gap=(2.5, 4), h=(18, 32), tall=0.0, tallh=(0, 0)),
}

stats_out = {"park": 0, "built": 0, "plain": 0}
blk_ang = np.zeros(n_b); blk_kind = [""] * n_b
for bi in range(1, n_b):
    x, y, w, h, area_px = bstats[bi]
    area = area_px * RES * RES
    if area < 500:
        stats_out["plain"] += 1
        continue
    foot_d = foot_cnt[bi] * RES / area          # m of path per m²
    serv_d = serv_cnt[bi] * RES / area
    nw = nw_cnt[bi] / area_px
    sub = (blab[y:y + h, x:x + w] == bi).astype(np.uint8)
    cxm = (bcent[bi][0] * RES) - R
    czm = (bcent[bi][1] * RES) - R
    is_park = (foot_d > 0.012 and serv_d < 0.006) or (nw > 0.08 and serv_d < 0.01) or (foot_d > 0.02 and serv_d < 0.012)
    _c, _ = cv2.findContours(sub, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if _c:
        blk_ang[bi] = math.radians(cv2.minAreaRect(max(_c, key=cv2.contourArea))[2])
    if is_park and area > 3000:
        blk_kind[bi] = "park"
        park_mask[y:y + h, x:x + w][sub > 0] = 255
        stats_out["park"] += 1
        continue
    stats_out["built"] += 1
    zone = zone_of(cxm, czm)
    if zone in ("res", "shekou") and serv_d > 0.03 and area < 60000:
        zone = "village"      # dense alley grid → 城中村 style
    blk_kind[bi] = zone
    Z = ZONES[zone]
    # orientation from the block's min-area rectangle
    cnts, _ = cv2.findContours(sub, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        continue
    (rcx, rcy), (rw, rh), ang = cv2.minAreaRect(max(cnts, key=cv2.contourArea))
    th = math.radians(ang)
    ux, uz = math.cos(th), math.sin(th)       # along-axis
    vx, vz = -uz, ux
    setback = 5 if zone == "village" else 9
    inner = cv2.erode(sub, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * int(setback / RES) + 1,) * 2))
    if inner.sum() == 0:
        continue
    occ = np.zeros_like(inner)
    # walk a rotated grid across the block
    half = math.hypot(w, h) * RES / 2 + 60
    bx0 = x * RES - R + w * RES / 2
    bz0 = y * RES - R + h * RES / 2
    s = -half + rng.uniform(0, 20)
    while s < half:
        bw = rng.uniform(*Z["w"])
        t = -half + rng.uniform(0, 20)
        while t < half:
            bd = rng.uniform(*Z["d"])
            px = bx0 + ux * (s + bw / 2) + vx * (t + bd / 2)
            pz = bz0 + uz * (s + bw / 2) + vz * (t + bd / 2)
            corners = []
            for a1, a2 in [(-bw / 2, -bd / 2), (bw / 2, -bd / 2), (bw / 2, bd / 2), (-bw / 2, bd / 2)]:
                corners.append((px + ux * a1 + vx * a2, pz + uz * a1 + vz * a2))
            cp = np.array([((cx_ + R) / RES - x, (cz_ + R) / RES - y) for cx_, cz_ in corners], np.float32)
            ok = True
            if cp[:, 0].min() < 0 or cp[:, 1].min() < 0 or cp[:, 0].max() >= w or cp[:, 1].max() >= h:
                ok = False
            if ok:
                m = np.zeros_like(inner)
                cv2.fillPoly(m, [np.round(cp * 8).astype(np.int32)], 1, shift=3)
                cnt = m.sum()
                if cnt == 0 or (m & inner).sum() < cnt * 0.97 or (m & occ).any():
                    ok = False
                else:
                    gx, gy = x + int(cp[:, 0].mean()), y + int(cp[:, 1].mean())
                    if lm_clear[min(N - 1, gy), min(N - 1, gx)] or (lm_clear[y:y + h, x:x + w] & (m * 255)).any():
                        ok = False
            if ok and rng.random() < (0.95 if zone == "village" else 0.88):
                occ |= cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
                if rng.random() < Z["tall"]:
                    hh = rng.uniform(*Z["tallh"])
                else:
                    hh = rng.uniform(*Z["h"])
                # podium + tower: in CBD / tech, some buildings sit on a wider podium
                buildings.append([round(px, 1), round(pz, 1), round(bw, 1), round(bd, 1),
                                  round(math.degrees(th), 1), round(hh), zone])
            t += bd + rng.uniform(*Z["gap"])
        s += bw + rng.uniform(*Z["gap"])

print("blocks:", stats_out, "buildings:", len(buildings))

# ---------------------------------------------------------------- trees
bocc = np.zeros((N, N), np.uint8)
for b in buildings:
    px, pz, bw, bd, ang, hh, zn = b
    a = math.radians(ang); ux, uz = math.cos(a), math.sin(a)
    corners = [(px + ux * a1 - uz * a2, pz + uz * a1 + ux * a2) for a1, a2 in [(-bw / 2, -bd / 2), (bw / 2, -bd / 2), (bw / 2, bd / 2), (-bw / 2, bd / 2)]]
    cv2.fillPoly(bocc, [np.round(poly_px(corners) * 8).astype(np.int32)], 255, shift=3)
bocc = cv2.dilate(bocc, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))) | lm_clear
carriage = np.zeros((N, N), np.uint8)
draw_lines(carriage, veh, lambda rd: VEH_W[rd["fc"]] + 1)
footc = np.zeros((N, N), np.uint8)
draw_lines(footc, [rd for rd in surface if rd["fc"] in FOOT], lambda rd: 3)
# ---- sports grounds, courts and pools in the free space of blocks and parks
FEAT = {  # kind: (length, width, allowed block kinds, max count)
    5: (176, 100, ("res", "tech", "shekou"), 4),      # running track with pitch
    0: (104, 68, ("park", "res", "tech", "shekou"), 8),      # football pitch
    1: (60, 40, ("park", "res", "shekou", "tech", "cbd"), 18),  # small pitch
    4: (34, 18, ("res", "park", "tech", "shekou", "cbd"), 30),  # tennis (with margin)
    2: (30, 17, ("res", "village", "shekou", "park", "tech"), 70),  # basketball
    3: (31, 16, ("res", "cbd", "shekou"), 55),                # pool with deck
    6: (46, 32, ("res", "tech", "shekou", "cbd"), 70),        # surface car park
}
featmask = np.zeros((N, N), np.uint8)
features = []
blk_big = {}
base_free = ((land > 0) & (roadmask == 0) & (bocc == 0)).astype(np.uint8)
for kind in (5, 0, 1, 6, 4, 2, 3):
    L, Wd, kinds, cap = FEAT[kind]
    fr = (base_free & (featmask == 0)).astype(np.uint8)
    dt = cv2.distanceTransform(fr, cv2.DIST_L2, 5) * RES
    need = Wd / 2 + 2
    ys, xs = np.nonzero(dt[::5, ::5] >= need)
    order = rng.permutation(len(ys))
    placed = 0
    for k in order:
        if placed >= cap:
            break
        i, j = ys[k] * 5, xs[k] * 5
        bl = blab[i, j]
        if bl <= 0 or blk_kind[bl] not in kinds:
            continue
        if kind in (5, 0, 1) and blk_big.get(bl, 0) >= (2 if blk_kind[bl] == "park" else 1):
            continue
        x, z = j * RES - R, i * RES - R
        if math.hypot(x, z) > 2700:
            continue
        a = blk_ang[bl]
        for aa in (a, a + math.pi / 2):
            ux, uz = math.cos(aa), math.sin(aa)
            cs = [(x + ux * p - uz * q, z + uz * p + ux * q) for p, q in [(-L / 2 - 2, -Wd / 2 - 2), (L / 2 + 2, -Wd / 2 - 2), (L / 2 + 2, Wd / 2 + 2), (-L / 2 - 2, Wd / 2 + 2)]]
            m = np.zeros((N, N), np.uint8)
            cv2.fillPoly(m, [np.round(poly_px(cs) * 8).astype(np.int32)], 1, shift=3)
            cnt = int(m.sum())
            if cnt and int((m & fr).sum()) >= cnt * 0.99:
                featmask |= cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)))
                features.append([kind, round(x, 1), round(z, 1), round(math.degrees(aa), 1)])
                if kind in (5, 0, 1): blk_big[bl] = blk_big.get(bl, 0) + 1
                placed += 1
                break
print("features:", {k: sum(1 for f in features if f[0] == k) for k in FEAT})
bocc = bocc | (featmask * 255)
free = (land > 0) & (carriage == 0) & (bocc == 0) & (footc == 0)
near_w2 = cv2.dilate(water, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * 30 + 1,) * 2))  # 120 m
trees_round, trees_palm = [], []
def ok_px(x, z):
    i, j = int((z + R) / RES), int((x + R) / RES)
    return 0 <= i < N and 0 <= j < N and free[i, j], i, j
# parks: jittered grid
step = 11.0
for gz in np.arange(-R + 4, R - 4, step):
    for gx in np.arange(-R + 4, R - 4, step):
        x = gx + rng.uniform(-4, 4); z = gz + rng.uniform(-4, 4)
        good, i, j = ok_px(x, z)
        if not good or not park_mask[i, j]:
            continue
        if rng.random() < 0.5:
            (trees_palm if near_w2[i, j] and rng.random() < 0.6 else trees_round).append((x, z))
# street trees on both sides of bigger roads
for rd in veh:
    if rd["fc"] not in ("trunk", "primary", "secondary", "tertiary", "residential") or rd["bridge"]:
        continue
    off = VEH_W[rd["fc"]] / 2 + 2.2
    acc = rng.uniform(0, 9)
    p = rd["pts"]
    for k in range(len(p) - 1):
        ax, az = p[k]; bx, bz = p[k + 1]
        L = math.hypot(bx - ax, bz - az)
        if L < 0.1:
            continue
        nx, nz = -(bz - az) / L, (bx - ax) / L
        t = acc
        while t < L:
            f = t / L
            for sgn in (1, -1):
                x = ax + (bx - ax) * f + nx * off * sgn; z = az + (bz - az) * f + nz * off * sgn
                good, i, j = ok_px(x, z)
                if good:
                    trees_round.append((x, z))
            t += 10.5
        acc = t - L
# a few trees inside built blocks
for gz in np.arange(-R + 4, R - 4, 17.0):
    for gx in np.arange(-R + 4, R - 4, 17.0):
        x = gx + rng.uniform(-6, 6); z = gz + rng.uniform(-6, 6)
        good, i, j = ok_px(x, z)
        if good and not park_mask[i, j] and blab[i, j] > 0 and rng.random() < 0.35:
            trees_round.append((x, z))
# thin out duplicates on a 4 m grid
def dedupe(lst):
    seen, out = set(), []
    for x, z in lst:
        key = (int(x // 4), int(z // 4))
        if key in seen:
            continue
        seen.add(key); out.append((x, z))
    return out
trees_round = dedupe(trees_round); trees_palm = dedupe(trees_palm)
MAXT = 26000
if len(trees_round) > MAXT:
    idx = rng.choice(len(trees_round), MAXT, replace=False); trees_round = [trees_round[i] for i in sorted(idx)]
print("trees:", len(trees_round), "palms:", len(trees_palm))

def png_b64(arr):
    im = Image.fromarray(arr)
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


# ---------------------------------------------------------------- land-use texture: zone + distance to nearest building
ZCODE = {"": 0, "cbd": 1, "tech": 2, "res": 3, "village": 4, "shekou": 5, "park": 6}
zone_img = np.zeros((N, N), np.uint8)
lut = np.array([ZCODE.get(k, 0) for k in blk_kind], np.uint8)
zone_img = lut[blab]
zone_img[park_mask > 0] = 6
foot_only = np.zeros((N, N), np.uint8)
for b in buildings:
    px, pz, bw, bd, ang, hh, zn = b
    a = math.radians(ang); ux, uz = math.cos(a), math.sin(a)
    corners = [(px + ux * a1 - uz * a2, pz + uz * a1 + ux * a2) for a1, a2 in [(-bw / 2, -bd / 2), (bw / 2, -bd / 2), (bw / 2, bd / 2), (-bw / 2, bd / 2)]]
    cv2.fillPoly(foot_only, [np.round(poly_px(corners) * 8).astype(np.int32)], 255, shift=3)
foot_only |= lm_clear
bdist = cv2.distanceTransform((foot_only == 0).astype(np.uint8), cv2.DIST_L2, 5) * RES
lu = np.zeros((N, N, 3), np.uint8)
lu[..., 0] = zone_img.astype(np.uint16) * 30
lu[..., 1] = np.clip(np.round(bdist * 8), 0, 255).astype(np.uint8)
lu_png = png_b64(lu)
print("landuse png:", len(lu_png) / 1e6, "MB")

# ---------------------------------------------------------------- outputs
def png_b64(arr):
    im = Image.fromarray(arr)
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


mask = np.zeros((N, N, 3), np.uint8)       # R = water, G = green
mask[..., 0] = (land == 0) * 255
mask[..., 1] = park_mask
mask_png = png_b64(mask)

cls_idx = {c: i for i, c in enumerate(CLASS_ORDER)}
names = []
name_idx = {}
road_out = []
for rd in roads:
    if rd["tunnel"]:
        continue
    nm = rd["name"]
    if nm not in name_idx:
        name_idx[nm] = len(names)
        names.append(nm)
    flat = []
    for x, z in rd["pts"]:
        flat += [round(x, 1), round(z, 1)]
    road_out.append([cls_idx[rd["fc"]], 1 if rd["bridge"] else 0, 1 if rd["ow"] == "T" else 0, name_idx[nm], flat])

LABELS = [
    ("深圳湾", 113.9600, 22.4985, "sea"),
    ("后海", 113.9370, 22.5230, "area"),
    ("蛇口", 113.9160, 22.4880, "area"),
    ("科技园", 113.9480, 22.5400, "area"),
    ("深圳湾公园", 113.9520, 22.5085, "park"),
    ("南山", 113.9230, 22.5330, "area"),
]
labels = []
for n, lon, lat, k in LABELS:
    x, z = to_xz(lon, lat)
    if k == "park":   # snap onto the nearest generated green area
        ys, xs = np.nonzero(park_mask[::4, ::4])
        px, py = (x + R) / RES / 4, (z + R) / RES / 4
        j = int(np.argmin((xs - px) ** 2 + (ys - py) ** 2))
        x, z = xs[j] * 4 * RES - R, ys[j] * 4 * RES - R
    if abs(x) < R and abs(z) < R:
        labels.append({"n": n, "x": round(x), "z": round(z), "k": k})

data = {
    "center": [LAT0, LON0], "R": R, "res": RES,
    "classes": CLASS_ORDER, "names": names, "roads": road_out,
    "mask": mask_png, "buildings": buildings, "landmarks": lm_out, "labels": labels,
    "zones": list(ZONES.keys()),
    "trees": [v for x, z in trees_round for v in (int(round(x)), int(round(z)))],
    "palms": [v for x, z in trees_palm for v in (int(round(x)), int(round(z)))],
    "features": features,
    "lu": lu_png,
}
for b in data["buildings"]:
    b[6] = data["zones"].index(b[6])
with open(OUT + "/szbay.json", "w") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
print("json size:", len(json.dumps(data, ensure_ascii=False, separators=(",", ":"))) / 1e6, "MB")

# ---------------------------------------------------------------- debug image
dbg = np.zeros((N, N, 3), np.uint8)
dbg[:] = (60, 110, 140)
dbg[land > 0] = (215, 210, 200)
dbg[park_mask > 0] = (120, 170, 110)
draw_lines(dbg, [rd for rd in surface if rd["fc"] in VEH_W], lambda rd: VEH_W[rd["fc"]], (255, 255, 255))
for b in buildings:
    px, pz, bw, bd, ang, hh, zn = b
    a = math.radians(ang)
    ux, uz = math.cos(a), math.sin(a)
    corners = [(px + ux * a1 - uz * a2, pz + uz * a1 + ux * a2) for a1, a2 in [(-bw / 2, -bd / 2), (bw / 2, -bd / 2), (bw / 2, bd / 2), (-bw / 2, bd / 2)]]
    col = {0: (40, 40, 160), 1: (40, 120, 160), 2: (90, 60, 40), 3: (70, 70, 70), 4: (120, 80, 80)}[zn]
    cv2.fillPoly(dbg, [np.round(poly_px(corners) * 8).astype(np.int32)], col, shift=3)
for lm in lm_out:
    cv2.fillPoly(dbg, [np.round(poly_px(lm["r"]) * 8).astype(np.int32)], (220, 60, 30), shift=3)
Image.fromarray(dbg).resize((1200, 1200), Image.LANCZOS).save(OUT + "/debug.png")
