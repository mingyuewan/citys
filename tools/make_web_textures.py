"""Downscale the GPT Image textures in assets/textures/ for the page (embedded into index.html by assemble3.py).
usage: python tools/make_web_textures.py   (needs Pillow)
"""
import os

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "assets", "textures")
DST = os.path.join(ROOT, "assets", "web")
os.makedirs(DST, exist_ok=True)
for name, size, q in (("island-rock", 512, 78), ("tower-facade", 512, 80), ("cloud-puff", 512, 82)):
    im = Image.open(os.path.join(SRC, name + ".webp"))
    w, h = im.size
    s = size / max(w, h)
    im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
    out = os.path.join(DST, name + ".webp")
    im.save(out, "WEBP", quality=q, method=6, exact=im.mode == "RGBA")
    print(out, im.size, im.mode, os.path.getsize(out), "bytes")
