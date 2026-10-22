#!/usr/bin/env bash
# Rebuild data and the page.
#   1) get the Shenzhen OSM road shapefile (once):
#      git clone --depth 1 --filter=blob:none --sparse https://github.com/ni1o1/pygeo-tutorial /tmp/pygeo
#      git -C /tmp/pygeo sparse-checkout set --no-cone 'shapefile/shenzhen_osmroad.*'
#   2) bash tools/build.sh /tmp/pygeo/shapefile
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "${1:-}" != "" ]; then python3 tools/build_data.py "$1" data; fi
python3 tools/assemble3.py src/city.src.html data/szbay.json build/artifact.html index.html
