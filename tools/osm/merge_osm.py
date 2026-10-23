#!/usr/bin/env python3
"""Merge the real OSM buildings (data/osm/buildings.json, from fetch_osm.py bake) into what the page draws.

usage: python3 tools/osm/merge_osm.py [data/szbay.json] [data/osm/buildings.json] [web/data/osm-buildings.json]

Rules (docs/handoff.md, phase 2):
  * only buildings on the island (centroid inside isleR − 10 m);
  * the 11 landmarks stay hand-made, but are moved onto their real footprint when OSM has it (a building within
    SNAP metres whose height is within 8 % of the landmark's; towers of 150 m and more only — Wikipedia coordinates are often 50–100 m off); then
    OSM footprints overlapping a landmark are dropped;
  * a building outline that has building:part pieces inside it is dropped (the parts carry the real heights);
  * generated buildings give way: one is dropped when a real footprint overlaps it or a real building stands within
    FILL_CLEAR metres, so generated ones only fill streets OSM has no buildings for.
Output (compact, coordinates in decimetres):
  { "b": [[ring dm (x0,z0,x1,z1,…), h, min_h, src, name, kind], …],   src: "h" height tag, "l" levels, "e" estimated
    "drop": [index into szbay.json "buildings", …], "lm_move": {landmark index: [dx, dz] metres}, "stats": {…} }
"""
import json
import math
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SZ = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "szbay.json")
OSM = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "data", "osm", "buildings.json")
OUT = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, "web", "data", "osm-buildings.json")
FILL_CLEAR = 45.0
SNAP = 120.0

D = json.load(open(SZ, encoding="utf-8"))
O = json.load(open(OSM, encoding="utf-8"))

# island outline: same as web/src/world.js isleR (keep in sync)
R0, WAVES, LOBE_W, SOFT = 2850.0, [(0.05, 3, 1), (0.035, 5, 2), (0.02, 9, 0.5), (0.012, 17, 3.1)], 0.16, 60.0
hk = next(l for l in D["landmarks"] if l["k"] == "hanking")
TH_H, LOBE = math.atan2(hk["c"][1], hk["c"][0]), math.hypot(*hk["c"]) + 75


def isle_r(th):
    b = R0 * (1 + sum(a * math.sin(f * th + p) for a, f, p in WAVES))
    d = (th - TH_H + math.pi) % (2 * math.pi) - math.pi
    lo = LOBE * math.exp(-(d / LOBE_W) ** 2)
    m = max(b, lo)
    return m + SOFT * math.log(math.exp((b - m) / SOFT) + math.exp((lo - m) / SOFT))


def in_isle(x, z, margin=0.0):
    return math.hypot(x, z) < isle_r(math.atan2(z, x)) - margin


def ring_of(flat):
    return [(flat[i], flat[i + 1]) for i in range(0, len(flat), 2)]


def area(r):
    return sum(r[i][0] * r[(i + 1) % len(r)][1] - r[(i + 1) % len(r)][0] * r[i][1] for i in range(len(r))) / 2


def centroid(r):
    a = area(r)
    if abs(a) < 1e-6:
        return sum(p[0] for p in r) / len(r), sum(p[1] for p in r) / len(r)
    cx = cz = 0.0
    for i in range(len(r)):
        x0, z0 = r[i]; x1, z1 = r[(i + 1) % len(r)]
        k = x0 * z1 - x1 * z0
        cx += (x0 + x1) * k; cz += (z0 + z1) * k
    return cx / (6 * a), cz / (6 * a)


def inside(p, r):
    x, z = p; c = False
    for i in range(len(r)):
        x0, z0 = r[i]; x1, z1 = r[(i + 1) % len(r)]
        if (z0 > z) != (z1 > z) and x < (x1 - x0) * (z - z0) / (z1 - z0) + x0:
            c = not c
    return c


def rect_ring(x, z, w, d, ang):
    c, s = math.cos(ang), math.sin(ang)
    return [(x + c * u - s * v, z + s * u + c * v) for u, v in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2))]


def overlaps(a, b):
    """Rough polygon overlap: a vertex or the centroid of one inside the other."""
    return any(inside(p, b) for p in a) or any(inside(p, a) for p in b) or inside(centroid(a), b) or inside(centroid(b), a)


# ---- real buildings on the island
rows = []
for e in O["b"]:
    bid, flat, (h, mh, src, name, kind) = e[0], e[1:-5], e[-5:]
    r = ring_of(flat)
    if len(r) < 3:
        continue
    cx, cz = centroid(r)
    if not in_isle(cx, cz, 10):
        continue
    rows.append({"id": bid, "r": r, "c": (cx, cz), "h": h, "mh": mh, "src": src, "name": name, "kind": kind, "part": kind == "part"})
stats = {"osm_on_island": len(rows)}

# landmarks stay hand-made, moved onto their real footprint when OSM has it
lms, moves = [], {}
for i, l in enumerate(D["landmarks"]):
    r = [tuple(p) for p in l["r"]]
    # (only towers: low landmarks have too many look-alikes nearby)
    cand = [b for b in rows if l["h"] >= 150 and math.hypot(b["c"][0] - l["c"][0], b["c"][1] - l["c"][1]) < SNAP and abs(b["h"] - l["h"]) < 0.08 * l["h"]]
    if cand:
        b = min(cand, key=lambda b: math.hypot(b["c"][0] - l["c"][0], b["c"][1] - l["c"][1]))
        dx, dz = round(b["c"][0] - l["c"][0], 1), round(b["c"][1] - l["c"][1], 1)
        moves[i] = [dx, dz]
        r = [(x + dx, z + dz) for x, z in r]
    lms.append(r)
stats["landmarks_moved"] = {D["landmarks"][i]["n"]: m for i, m in moves.items()}
keep = [b for b in rows if not any(overlaps(b["r"], L) for L in lms)]
stats["dropped_landmark_overlap"] = len(rows) - len(keep)

# outlines that contain parts: the parts carry the heights
parts = [b for b in keep if b["part"]]
before = len(keep)
keep = [b for b in keep if b["part"] or not any(inside(p["c"], b["r"]) for p in parts)]
stats["dropped_outlines_with_parts"] = before - len(keep)

# generated buildings give way to real ones
grid = {}
for k, b in enumerate(keep):
    grid.setdefault((int(b["c"][0] // 100), int(b["c"][1] // 100)), []).append(k)
drop = []
for i, (x, z, w, d, ang, h, zi) in enumerate(D["buildings"]):
    gr = rect_ring(x, z, w, d, math.radians(ang))
    near = [keep[k] for gx in range(int(x // 100) - 1, int(x // 100) + 2) for gz in range(int(z // 100) - 1, int(z // 100) + 2) for k in grid.get((gx, gz), [])]
    if any(math.hypot(b["c"][0] - x, b["c"][1] - z) < FILL_CLEAR + max(w, d) / 2 or overlaps(gr, b["r"]) for b in near):
        drop.append(i)
stats["generated_total"] = len(D["buildings"]); stats["generated_dropped"] = len(drop)
stats["kept"] = len(keep)
stats["src"] = {s: sum(1 for b in keep if b["src"] == s) for s in "hle"}

out = {"b": [[[round(v * 10) for p in b["r"] for v in p], b["h"], b["mh"], b["src"], b["name"], b["kind"]] for b in keep],
       "drop": drop, "lm_move": moves, "stats": stats,
       "note": "Real building footprints © OpenStreetMap contributors (ODbL). Coordinates in decimetres, page frame (CLAUDE.md)."}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
print(json.dumps(stats, ensure_ascii=False), f"-> {OUT} ({os.path.getsize(OUT) / 1e6:.2f} MB)")
