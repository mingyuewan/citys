"""Minimal ESRI shapefile + dbf reader (polyline/polygon/point), no deps."""
import struct


def read_dbf(path, encoding="utf-8"):
    with open(path, "rb") as f:
        data = f.read()
    nrec, hlen, rlen = struct.unpack("<IHH", data[4:12])
    fields = []
    off = 32
    while data[off] != 0x0D:
        name = data[off:off + 11].split(b"\0")[0].decode("ascii", "replace")
        ftype = chr(data[off + 11])
        flen = data[off + 16]
        fields.append((name, ftype, flen))
        off += 32
    recs = []
    for i in range(nrec):
        base = hlen + i * rlen + 1
        rec = {}
        p = base
        for name, ftype, flen in fields:
            raw = data[p:p + flen]
            p += flen
            try:
                s = raw.decode(encoding).strip()
            except UnicodeDecodeError:
                s = raw.decode("gbk", "replace").strip()
            rec[name] = s
        recs.append(rec)
    return fields, recs


def read_shp(path):
    with open(path, "rb") as f:
        data = f.read()
    shape_type = struct.unpack("<i", data[32:36])[0]
    bbox = struct.unpack("<4d", data[36:68])
    shapes = []
    off = 100
    n = len(data)
    while off + 8 <= n:
        _, clen = struct.unpack(">ii", data[off:off + 8])
        off += 8
        end = off + clen * 2
        st = struct.unpack("<i", data[off:off + 4])[0]
        if st == 0:
            shapes.append(None)
        elif st in (1, 11, 21):
            x, y = struct.unpack("<2d", data[off + 4:off + 20])
            shapes.append({"type": "point", "pts": [(x, y)]})
        elif st in (3, 5, 13, 15, 23, 25):
            sb = struct.unpack("<4d", data[off + 4:off + 36])
            nparts, npts = struct.unpack("<ii", data[off + 36:off + 44])
            parts = list(struct.unpack("<%di" % nparts, data[off + 44:off + 44 + 4 * nparts]))
            po = off + 44 + 4 * nparts
            coords = struct.unpack("<%dd" % (2 * npts), data[po:po + 16 * npts])
            pts = [(coords[2 * i], coords[2 * i + 1]) for i in range(npts)]
            parts.append(npts)
            rings = [pts[parts[i]:parts[i + 1]] for i in range(nparts)]
            shapes.append({"type": "line" if st in (3, 13, 23) else "poly", "bbox": sb, "parts": rings})
        else:
            shapes.append(None)
        off = end
    return shape_type, bbox, shapes
