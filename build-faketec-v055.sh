#!/bin/bash
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
SOURCE_ROOT="${FAKETEC_MESHCORE_ROOT:-$HOME/faketec-ui/MeshCore}"
ROOT="$(cd "$SOURCE_ROOT" && pwd)"

export FAKETEC_MESHCORE_ROOT="$ROOT"

if [ -f "$HOME/meshcore-flash/bin/activate" ]; then
  . "$HOME/meshcore-flash/bin/activate"
fi

if ! grep -q 'FAKETEC_RELAY_PERSIST_V055' \
  "$ROOT/examples/companion_radio/MyMesh.cpp"; then

  bash "$HERE/build-faketec-v054.sh" --prepare-only

  python "$HERE/faketec_v055_patch.py" "$ROOT"
fi

cd "$ROOT"

OUT="${FAKETEC_RELEASE_DIR:-$HOME/Downloads/faketec-v055-release}"

mkdir -p "$OUT"

NAME="faketec-meshcore-ui-v0.5.5-relay-persistence.uf2"

UF2_FILE_PATH="$OUT/$NAME" \
python -m platformio run \
  -e ProMicro_companion_radio_ble \
  -t create_uf2

cd "$OUT"

test -s "$NAME"

shasum -a 256 "$NAME" | tee "$NAME.sha256"

echo "SUCCESS: FakeTec v0.5.5 compiled."
echo "No device flashed."
