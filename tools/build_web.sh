#!/usr/bin/env bash
# Prepare web/ to be served or published as is (GitHub Pages: .github/workflows/pages.yml uploads web/):
#   - copies data/szbay.json into web/data/ (the page loads its data relative to itself)
#   - merges the real OSM buildings → web/data/osm-buildings.json (tools/osm/merge_osm.py; input data/osm/buildings.json,
#     from `python3 tools/osm/fetch_osm.py fetch` then `bake`)
#   - with --models, also rebuilds web/assets/island.glb and landmarks.glb (Blender 4.5 + npx gltfpack)
set -euo pipefail
cd "$(dirname "$0")/.."
cp data/szbay.json web/data/szbay.json
python3 tools/osm/merge_osm.py
if [ "${1:-}" = "--models" ]; then bash tools/blender/build_island.sh; bash tools/blender/build_landmarks.sh; fi
echo "web/ is ready: python3 -m http.server 8765 --bind 127.0.0.1, then http://127.0.0.1:8765/web/"
