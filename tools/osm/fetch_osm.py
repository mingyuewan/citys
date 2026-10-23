#!/usr/bin/env python3
"""Fetch and bake real OpenStreetMap data for the island (stdlib only).

Step 1 – fetch (needs network to an Overpass server; run on your own machine):
    python3 tools/osm/fetch_osm.py fetch            # -> data/osm/raw.json
Step 2 – bake (offline):
    python3 tools/osm/fetch_osm.py bake             # -> data/osm/buildings.json, data/osm/areas.json

Coordinates follow CLAUDE.md: origin 22.5150N 113.9420E, metres, x = east, z = south.

buildings.json
  { "origin": [lat, lon], "count": N,
    "b": [ [osmType+id, x0,z0,x1,z1,...(outer ring, CCW in x/z, no repeated last point),
            height_m, min_height_m, height_source, name, kind], ... ],
    "holes": { "<id>": [[x,z,...], ...] } }
  height_source: "h" = height tag, "l" = building:levels, "e" = estimated from kind/area
areas.json
  { "coast": [[x,z,...], ...]  (open polylines, land on the left as in OSM),
    "water": [ring, ...], "green": [ring, ...], "pitch": [ring, ...] }
"""
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

LAT0, LON0 = 22.5150, 113.9420
KY = 110574.0
KX = 111320.0 * math.cos(math.radians(LAT0))
RADIUS = 3500          # metres around the origin (island outline reaches ~3400 m toward Hanking Center)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "data", "osm")
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]


def bbox():
    d_lat, d_lon = RADIUS / KY, RADIUS / KX
    return LAT0 - d_lat, LON0 - d_lon, LAT0 + d_lat, LON0 + d_lon


def query():
    s, w, n, e = bbox()
    bb = f"({s:.5f},{w:.5f},{n:.5f},{e:.5f})"
    return f"""[out:json][timeout:240];
(
  way["building"]{bb};
  relation["building"]["type"="multipolygon"]{bb};
  way["building:part"]{bb};
  way["natural"="coastline"]{bb};
  way["natural"="water"]{bb};
  relation["natural"="water"]{bb};
  way["waterway"="riverbank"]{bb};
  way["leisure"~"^(park|garden|golf_course|nature_reserve|pitch|playground)$"]{bb};
  relation["leisure"~"^(park|nature_reserve)$"]{bb};
  way["landuse"~"^(grass|forest|recreation_ground|meadow|village_green)$"]{bb};
  way["natural"~"^(wood|scrub|wetland|grassland|beach)$"]{bb};
);
out geom qt;"""


def fetch():
    os.makedirs(OUT, exist_ok=True)
    body = urllib.parse.urlencode({"data": query()}).encode()
    last = None
    for url in ENDPOINTS:
        try:
            print("POST", url, flush=True)
            t0 = time.time()
            req = urllib.request.Request(url, data=body, headers={"User-Agent": "citys-floating-island/1.0"})
            with urllib.request.urlopen(req, timeout=300) as r:
                raw = r.read()
            data = json.loads(raw)
            if not data.get("elements"):
                raise RuntimeError("empty response: " + str(data.get("remark", ""))[:200])
            path = os.path.join(OUT, "raw.json")
            with open(path, "wb") as f:
                f.write(raw)
            print(f"ok: {len(data['elements'])} elements, {len(raw) / 1e6:.1f} MB, {time.time() - t0:.0f}s -> {path}")
            return
        except Exception as ex:  # noqa: BLE001 - try the next mirror
            last = ex
            print("  failed:", ex, flush=True)
    sys.exit(f"all Overpass endpoints failed ({last}). You can also run the query printed by `python3 {__file__} query` on overpass-turbo.eu and save the raw JSON as data/osm/raw.json")


# ---------------------------------------------------------------- bake helpers
def xz(p):
    return (round((p["lon"] - LON0) * KX, 1), round((LAT0 - p["lat"]) * KY, 1))


def area(r):
    a = 0.0
    for i in range(len(r)):
        x0, z0 = r[i]
        x1, z1 = r[(i + 1) % len(r)]
        a += x0 * z1 - x1 * z0
    return a / 2


def close_ring(r):
    if len(r) > 2 and r[0] == r[-1]:
        r = r[:-1]
    return r


def join_ways(segs):
    """Join open member ways into closed rings by matching endpoints."""
    segs = [s[:] for s in segs if len(s) > 1]
    rings = []
    while segs:
        cur = segs.pop(0)
        guard = 0
        while cur[0] != cur[-1] and guard < 10000:
            guard += 1
            end = cur[-1]
            k = next((i for i, s in enumerate(segs) if s[0] == end or s[-1] == end), -1)
            if k < 0:
                break
            s = segs.pop(k)
            if s[0] != end:
                s.reverse()
            cur += s[1:]
        rings.append(cur)
    return rings


def num(v):
    if v is None:
        return None
    try:
        return float(str(v).replace(",", ".").replace("m", "").strip().split(";")[0])
    except ValueError:
        return None


KIND_H = {"house": 9, "detached": 9, "residential": 30, "apartments": 60, "dormitory": 30, "commercial": 24, "office": 60,
          "retail": 12, "industrial": 15, "warehouse": 12, "school": 18, "university": 24, "college": 24, "hospital": 30,
          "hotel": 60, "roof": 6, "construction": 30, "garage": 4, "garages": 4, "service": 5, "kiosk": 4, "shed": 4,
          "hut": 4, "train_station": 15, "transportation": 12, "stadium": 35, "sports_centre": 24, "public": 20,
          "government": 30, "civic": 24, "church": 18, "temple": 10}


def height_of(tags, a):
    h = num(tags.get("height"))
    mh = num(tags.get("min_height"))
    lv = num(tags.get("building:levels"))
    mlv = num(tags.get("building:min_level"))
    if mh is None and mlv is not None:
        mh = mlv * 3.2
    mh = mh or 0.0
    if h is not None and h > 0:
        return h, mh, "h"
    if lv is not None and lv > 0:
        return lv * 3.2 + (num(tags.get("roof:levels")) or 0) * 3.0, mh, "l"
    k = tags.get("building") or tags.get("building:part") or "yes"
    if k in KIND_H:
        return float(KIND_H[k]), mh, "e"
    # unknown kind: small footprints are low, big footprints are mid-rise (Shenzhen default)
    return (8.0 if a < 150 else 18.0 if a < 600 else 36.0), mh, "e"


def bake():
    path = os.path.join(OUT, "raw.json")
    data = json.load(open(path, encoding="utf-8"))
    B, holes = [], {}
    areas = {"coast": [], "water": [], "green": [], "pitch": []}
    stats = {"h": 0, "l": 0, "e": 0, "skipped": 0}
    for el in data["elements"]:
        t = el.get("tags", {})
        outers, inners = [], []
        if el["type"] == "way" and el.get("geometry"):
            pts = [xz(p) for p in el["geometry"] if p]
            if t.get("natural") == "coastline":
                areas["coast"].append([v for p in pts for v in p])
                continue
            outers = [pts]
        elif el["type"] == "relation":
            o = [[xz(p) for p in m["geometry"] if p] for m in el.get("members", []) if m.get("type") == "way" and m.get("geometry") and m.get("role") != "inner"]
            i = [[xz(p) for p in m["geometry"] if p] for m in el.get("members", []) if m.get("type") == "way" and m.get("geometry") and m.get("role") == "inner"]
            outers, inners = join_ways(o), join_ways(i)
        else:
            continue
        outers = [close_ring(r) for r in outers]
        outers = [r for r in outers if len(r) >= 3]
        if not outers:
            continue
        flat = lambda r: [v for p in r for v in p]  # noqa: E731
        if t.get("building") or t.get("building:part"):
            if t.get("building") == "no":
                continue
            for r in outers:
                a = area(r)
                if abs(a) < 12:
                    stats["skipped"] += 1
                    continue
                if a < 0:
                    r = r[::-1]
                h, mh, src = height_of(t, abs(a))
                stats[src] += 1
                bid = el["type"][0] + str(el["id"])
                name = t.get("name:zh") or t.get("name") or t.get("name:en") or ""
                kind = t.get("building") or ("part" if t.get("building:part") else "yes")
                B.append([bid] + flat(r) + [round(h, 1), round(mh, 1), src, name, kind])
                if inners:
                    holes[bid] = [flat(close_ring(x)) for x in inners if len(x) >= 3]
        elif t.get("natural") == "water" or t.get("waterway") == "riverbank":
            areas["water"] += [flat(r) for r in outers]
        elif t.get("leisure") == "pitch":
            areas["pitch"] += [flat(r) for r in outers]
        else:
            areas["green"] += [flat(r) for r in outers]
    with open(os.path.join(OUT, "buildings.json"), "w", encoding="utf-8") as f:
        json.dump({"origin": [LAT0, LON0], "count": len(B), "b": B, "holes": holes}, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(OUT, "areas.json"), "w", encoding="utf-8") as f:
        json.dump(areas, f, separators=(",", ":"))
    print(f"buildings: {len(B)}  (height tag {stats['h']}, levels {stats['l']}, estimated {stats['e']}, tiny skipped {stats['skipped']})")
    print("areas:", {k: len(v) for k, v in areas.items()})
    named = sorted((b for b in B if b[-2]), key=lambda b: -b[-5])[:15]
    for b in named:
        print(f"  {b[-2]}  {b[-5]} m ({b[-3]})")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "fetch":
        fetch()
    elif cmd == "bake":
        bake()
    elif cmd == "query":
        print(query())
    else:
        sys.exit(__doc__)
