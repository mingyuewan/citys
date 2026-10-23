# 深圳湾 · 空中之岛

A floating-island 3D city of Shenzhen Bay (Houhai, Nanshan) rendered in the browser. The page is `web/`: three.js r160, ES modules, no build step (serve the project root, open `/web/`). The earlier hand-written WebGL2 single-file page (`src/city.src.html` → `index.html`) is kept as a reference. Read `docs/handoff.md` for the direction, the roadmap and what each phase delivered (§8).

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
- `tools/blender/model_island.py` + `build_island.sh` – the modelled island rock body (strata, ledges, gullies, spires; colours and occlusion baked into vertex colours) → `web/assets/island.glb` (gltfpack: meshopt + 16-bit quantization, `-kn -km -ke` so node/material names and extras survive). The page loads it in `web/src/models.js`, converts it to its own vertex layout and draws it with the building shader; without the file it falls back to the procedural body. Texcoord u is stored divided by the node's `uScale` extra.
- `tools/webgl_check.py` – smoke tests and A/B frame timing.
- `web/` – three.js r160 version of the page (branch `threejs-migration`). Serve the project root and open `/web/index.html`. Shader GLSL in `web/src/materials/` is copied verbatim from `src/city.src.html` into `RawShaderMaterial`s; shared uniforms live in `materials/common.js` (`U`). `web/data/szbay.json` is a symlink to `data/szbay.json`. Phase 1 is complete: every layer of the old page is ported and matches it in the six comparison views, 20–30 % faster (overview 22 → 15 ms on the 5300M). Differences from the old engine: triangles are oriented by their normals and drawn front-face only (`world.js orient()`); trees and street props are drawn in 400 m cells (`instancing.js`); aircraft/boats/cranes are pooled models moved by transform (`air.js`, `MODEL` define in `materials/building.js`); the static shadow map is redrawn only when sun/focus/extent change, moving casters go into a second map each frame; sky and cloud sea are drawn after the opaque geometry. Art direction from here: style A (miniature diorama).
- `tools/compare_views.py` – old page vs `web/` screenshots for the six phase-1 views (`build/compare/*-pair.png`). `tools/webgl_check.py` takes the `web/` URL too (A/B: pass both URLs); `tools/record.py --page http://127.0.0.1:8765/web/index.html` records the new page (set `CHROME` if Playwright's Chromium isn't installed).
- `docs/handoff.md` – handoff: status, direction (art style, flight mode, time presets), phases 1–4, migration plan, test hooks that must be kept.

## Coordinate system (shared by the page and any Blender assets)

- Origin: 22.5150°N, 113.9420°E. Units: metres.
- Page/world: x = east, z = south, y = up. (glTF is y-up; Blender is z-up with -y = north, so Blender (X, Y, Z) → page (x, y, z) = (X, Z, -Y) — the glTF exporter's "+Y up" option does this.)
- `lon → x = (lon - 113.9420) * 111320 * cos(22.515°)`, `lat → z = (22.5150 - lat) * 110574`.
- Island outline: `isleR(theta)` in the page (base radius 2850 m, plus a lobe toward the Hanking Center). Ground level y = 0, cloud sea at y = -1900.

## Landmarks (Wikipedia coordinates / heights)

China Resources HQ 392.5 m (22.51694, 113.94167) · One Shenzhen Bay T7 341.4 m · Zhongzhou Holdings Financial Center 300.8 m · Tencent Binhai Mansion 248 m / 194 m · Shenzhen Bay ITC T1 311.1 m / T2 247.2 m · Hanking Center 358.9 m · Huiyun Center 359.2 m · Shenzhen Bay Sports Center (cocoon) · Shenzhen Bay Cultural Plaza. See `LANDMARKS` in `tools/build_data.py`.

## Status

Phases 1–4 of `docs/handoff.md` are done (see its §8): the page in `web/` is the deliverable — real OSM buildings, modelled island rock and two landmarks, style A, four time presets, flight mode, synthesized sound, in-page recording, deployable as is (`tools/build_web.sh`, `.github/workflows/pages.yml`). The old single-file page stays as a reference. Open follow-ups are listed at the end of `docs/handoff.md` §8.

Keep the test hooks listed in `docs/handoff.md` §4.4 (window.S, setTod, flyTo, VIEWS, startTour, …; plus choosePreset, startFlight / stopFlight, FLY on the new page; time only from performance.now(), loop only via requestAnimationFrame) — `tools/record.py`, `tools/webgl_check.py`, `tools/shoot_views.py` depend on them. Tools set `window.SZ_TEST`, which skips the start screen and starts on the day preset.

## Notes

- Data honesty: roads, 2,778 OSM building footprints and 11 landmarks are real (8 landmark towers moved onto their OSM footprints); coastline and green areas are inferred from the road network; the remaining 672 buildings, sports fields, car parks, people and parked cars are generated. The page says so in its credits and the info card gives each building's source.
- Keep the OSM attribution ("道路 © OpenStreetMap 贡献者", building footprints ODbL).
- Reference project: github.com/Zenojz/shibuya-rain-walk (code MIT). Borrow approaches, not assets: its VRM characters are non-commercial-only and Mixamo animations may not be redistributed.
