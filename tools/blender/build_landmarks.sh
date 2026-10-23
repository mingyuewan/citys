#!/usr/bin/env bash
# Rebuild web/assets/landmarks.glb (Spring Bamboo, Spring Cocoon): Blender (tools/blender/model_landmarks.py), then
# gltfpack as for the island (meshopt, 16-bit, names and extras kept).
set -euo pipefail
cd "$(dirname "$0")/../.."
BLENDER="${BLENDER:-$HOME/.cache/codex-tools/blender-volume/Blender.app/Contents/MacOS/Blender}"
mkdir -p build
"$BLENDER" -b --factory-startup --python tools/blender/model_landmarks.py -- data/szbay.json build/landmarks.raw.glb --blend build/landmarks.blend
npx --yes gltfpack@1.3.0 -i build/landmarks.raw.glb -o web/assets/landmarks.glb -cc -kv -kn -km -ke -vp 16 -vt 16
ls -la build/landmarks.raw.glb web/assets/landmarks.glb
