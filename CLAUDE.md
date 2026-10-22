# 深圳湾 · 空中之岛

A floating-island 3D city of Shenzhen Bay (Houhai, Nanshan) rendered in the browser with a hand-written WebGL2 engine (no libraries). One self-contained HTML page with the data embedded.

## Files

- `src/city.src.html` – page source. Contains `/*__SZDATA__*/` where the dataset is injected. Edit this, not `index.html`.
- `data/szbay.json` – dataset built by `tools/build_data.py` (roads, land/water mask PNG, land-use PNG, generated buildings, landmarks, trees, sports fields/pools/car parks).
- `index.html` – assembled page (open directly in a browser). Rebuild with `bash tools/build.sh` after editing the source; `bash tools/build.sh <shapefile_dir>` also rebuilds the data.
- `tools/build_data.py` – data pipeline. Input: OSM road shapefile of Shenzhen from `github.com/ni1o1/pygeo-tutorial` (`shapefile/shenzhen_osmroad.*`). See README for how to fetch it.
- `tools/assemble3.py` – writes `build/artifact.html` (no html/head/body wrapper, for claude.ai artifacts) and `index.html`.
- `tools/record.py` – frame-by-frame demo video recorder (Playwright + headless Chromium, fake clock). Encode frames with ffmpeg.
- `tools/patches/` – historical patch scripts from development (reference only, not needed to build).

## Coordinate system (shared by the page and any Blender assets)

- Origin: 22.5150°N, 113.9420°E. Units: metres.
- Page/world: x = east, z = south, y = up. (glTF is y-up; Blender is z-up with -y = north, so Blender (X, Y, Z) → page (x, y, z) = (X, Z, -Y) — the glTF exporter's "+Y up" option does this.)
- `lon → x = (lon - 113.9420) * 111320 * cos(22.515°)`, `lat → z = (22.5150 - lat) * 110574`.
- Island outline: `isleR(theta)` in the page (base radius 2850 m, plus a lobe toward the Hanking Center). Ground level y = 0, cloud sea at y = -1900.

## Landmarks (Wikipedia coordinates / heights)

China Resources HQ 392.5 m (22.51694, 113.94167) · One Shenzhen Bay T7 341.4 m · Zhongzhou Holdings Financial Center 300.8 m · Tencent Binhai Mansion 248 m / 194 m · Shenzhen Bay ITC T1 311.1 m / T2 247.2 m · Hanking Center 358.9 m · Huiyun Center 359.2 m · Shenzhen Bay Sports Center (cocoon) · Shenzhen Bay Cultural Plaza. See `LANDMARKS` in `tools/build_data.py`.

## Next step planned: Blender modelling → glb → page

1. In Blender (scripted with bpy, `blender -b -P script.py`): model the landmarks precisely, sculpt the island rock body, model low-poly props (trees, cars, boats); optionally import real OSM building footprints (BlenderGIS) to replace the generated buildings. Bake AO / lighting into textures. Export `.glb` (+Y up, metres, origin as above). Keep total assets under ~15 MB.
2. In the page: add a GLB loader (parse the binary glTF chunk, POSITION/NORMAL/TEXCOORD_0/indices, baseColor texture) and swap in loaded meshes where present, falling back to the procedural versions.

## Notes

- Data honesty: roads and 11 landmarks are real; coastline and green areas are inferred from the road network; other buildings, sports fields, car parks, people and parked cars are generated. The page says so in its credits.
- Keep the OSM attribution ("道路 © OpenStreetMap 贡献者").
