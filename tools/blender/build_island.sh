#!/usr/bin/env bash
# Rebuild web/assets/island.glb: model the rock body in Blender (tools/blender/model_island.py), then compress it
# with gltfpack (meshopt, 16-bit positions and texcoords: ~9 cm over the island, no cracks at the rim; node and
# material names kept: the page finds ISLAND_body by name and the material id from "M10_rock").
# env BLENDER = Blender executable (default: the 4.5 build used for this project); needs npx (Node) for gltfpack.
set -euo pipefail
cd "$(dirname "$0")/../.."
BLENDER="${BLENDER:-$HOME/.cache/codex-tools/blender-volume/Blender.app/Contents/MacOS/Blender}"
mkdir -p build
"$BLENDER" -b --factory-startup --python tools/blender/model_island.py -- data/szbay.json build/island.raw.glb --blend build/island.blend
npx --yes gltfpack@1.3.0 -i build/island.raw.glb -o web/assets/island.glb -cc -kv -kn -km -ke -vp 16 -vt 16
ls -la build/island.raw.glb web/assets/island.glb
