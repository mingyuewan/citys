# 深圳湾 · 空中之岛

A floating-island 3D city of Shenzhen Bay (Houhai, Nanshan) rendered in the browser. The current version is a hand-written WebGL2 engine in one self-contained HTML page with the data embedded. **We are migrating to three.js r160 as a multi-file project — read `docs/handoff.md` first; it has the direction, the roadmap, acceptance criteria and the old-code → new-module map.**

## Files

- `src/city.src.html` – page source. Contains `/*__SZDATA__*/` where the dataset is injected. Edit this, not `index.html`.
- `data/szbay.json` – dataset built by `tools/build_data.py` (roads, land/water mask PNG, land-use PNG, generated buildings, landmarks, trees, sports fields/pools/car parks).
- `index.html` – assembled page (open directly in a browser). Rebuild with `bash tools/build.sh` after editing the source; `bash tools/build.sh <shapefile_dir>` also rebuilds the data.
- `tools/build_data.py` – data pipeline. Input: OSM road shapefile of Shenzhen from `github.com/ni1o1/pygeo-tutorial` (`shapefile/shenzhen_osmroad.*`). See README for how to fetch it.
- `tools/assemble3.py` – writes `build/artifact.html` (no html/head/body wrapper, for claude.ai artifacts) and `index.html`.
- `tools/record.py` – frame-by-frame demo video recorder (Playwright + headless Chromium, fake clock). Encode frames with ffmpeg.
- `tools/patches/` – historical patch scripts from development (reference only, not needed to build).
- `tools/osm/fetch_osm.py` – real OSM buildings / coastline / water / green areas: `fetch` (needs network, run locally) then `bake` (offline) → `data/osm/buildings.json`, `data/osm/areas.json`. Bake is tested on a synthetic sample; fetch has not yet been run against live Overpass.
- `tools/blender/`, `blender/`, `renders/` – Blender scene built from the page's real GPU buffers; see `docs/render-notes.md`.
- `tools/webgl_check.py` – smoke tests and A/B frame timing.
- `web/` – three.js r160 port in progress (phase 1, branch `threejs-migration`). Serve the project root and open `/web/index.html`. Shader GLSL in `web/src/materials/` is copied verbatim from `src/city.src.html` into `RawShaderMaterial`s; shared uniforms live in `materials/common.js` (`U`). `web/data/szbay.json` is a symlink to `data/szbay.json`. Ported so far: island body, city mesh, ground/bay, sky, cloud sea, shadows, bloom + composite, camera/tour, UI, picking.
- `tools/compare_views.py` – old page vs `web/` screenshots for the six phase-1 views (`build/compare/*-pair.png`).
- `docs/handoff.md` – handoff: status, direction (art style, flight mode, time presets), phases 1–4, migration plan, test hooks that must be kept.

## Coordinate system (shared by the page and any Blender assets)

- Origin: 22.5150°N, 113.9420°E. Units: metres.
- Page/world: x = east, z = south, y = up. (glTF is y-up; Blender is z-up with -y = north, so Blender (X, Y, Z) → page (x, y, z) = (X, Z, -Y) — the glTF exporter's "+Y up" option does this.)
- `lon → x = (lon - 113.9420) * 111320 * cos(22.515°)`, `lat → z = (22.5150 - lat) * 110574`.
- Island outline: `isleR(theta)` in the page (base radius 2850 m, plus a lobe toward the Hanking Center). Ground level y = 0, cloud sea at y = -1900.

## Landmarks (Wikipedia coordinates / heights)

China Resources HQ 392.5 m (22.51694, 113.94167) · One Shenzhen Bay T7 341.4 m · Zhongzhou Holdings Financial Center 300.8 m · Tencent Binhai Mansion 248 m / 194 m · Shenzhen Bay ITC T1 311.1 m / T2 247.2 m · Hanking Center 358.9 m · Huiyun Center 359.2 m · Shenzhen Bay Sports Center (cocoon) · Shenzhen Bay Cultural Plaza. See `LANDMARKS` in `tools/build_data.py`.

## Next step

Phase 1 of `docs/handoff.md`: migrate to three.js r160 in `web/` on a branch, with visual parity to the current page. Then phase 2 (art style + real OSM buildings via `tools/osm/fetch_osm.py`), phase 3 (Blender landmarks / island as glb, node names `LM_<k>` / `ISLAND_body`), phase 4 (flight mode, time presets, audio, in-page recording).

Keep the test hooks listed in `docs/handoff.md` §4.4 (window.S, setTod, flyTo, VIEWS, startTour, …; time only from performance.now(), loop only via requestAnimationFrame) — `tools/record.py` and `tools/webgl_check.py` depend on them.

## Notes

- Data honesty: roads and 11 landmarks are real; coastline and green areas are inferred from the road network; other buildings, sports fields, car parks, people and parked cars are generated. The page says so in its credits.
- Keep the OSM attribution ("道路 © OpenStreetMap 贡献者").
- Reference project: github.com/Zenojz/shibuya-rain-walk (code MIT). Borrow approaches, not assets: its VRM characters are non-commercial-only and Mixamo animations may not be redistributed.
