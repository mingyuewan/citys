import base64, json, os, sys
src = open(sys.argv[1], encoding="utf-8").read()
data = open(sys.argv[2], encoding="utf-8").read().replace("</", "<\\/")
body = src.replace("/*__SZDATA__*/", data)
# GPT Image textures (downscaled by tools/make_web_textures.py) embedded as data URIs → page stays a single offline file
web = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "web")
tex = {}
for key, fn in (("rock", "island-rock.webp"), ("facade", "tower-facade.webp"), ("cloud", "cloud-puff.webp")):
    p = os.path.join(web, fn)
    if os.path.exists(p): tex[key] = "data:image/webp;base64," + base64.b64encode(open(p, "rb").read()).decode()
body = body.replace("/*__SZTEX__*/", json.dumps(tex))
import os; os.makedirs(os.path.dirname(sys.argv[3]) or ".", exist_ok=True); open(sys.argv[3], "w", encoding="utf-8").write(body)   # artifact version (no html/head/body wrapper)
head_end = body.index("</style>") + len("</style>")
local = ('<!doctype html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n'
         '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
         + body[:head_end] + "\n</head>\n<body>\n" + body[head_end:] + "\n</body>\n</html>\n")
open(sys.argv[4], "w", encoding="utf-8").write(local)
print(len(body) / 1e6, "MB")
