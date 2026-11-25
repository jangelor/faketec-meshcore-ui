#!/bin/bash
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
SOURCE_ROOT="${FAKETEC_MESHCORE_ROOT:-$HOME/faketec-ui/MeshCore}"
ROOT="$(cd "$SOURCE_ROOT" && pwd)"
PATCH="$HERE/patches/faketec-v054-ad-hoc-relay.patch"
export FAKETEC_MESHCORE_ROOT="$ROOT"

case "${1:-}" in
  ''|--prepare-only) ;;
  *) echo 'Usage: bash build-faketec-v054.sh [--prepare-only]' >&2; exit 2 ;;
esac

if [ -f "$HOME/meshcore-flash/bin/activate" ]; then
  . "$HOME/meshcore-flash/bin/activate"
fi

bash "$HERE/build-faketec-v053.sh" --prepare-only
cd "$ROOT"
if ! git apply --reverse --check "$PATCH" 2>/dev/null; then
  git apply --check "$PATCH"
  git apply "$PATCH"
fi
git apply --reverse --check "$PATCH"
git diff --check
echo 'FakeTec v0.5.4 ad hoc relay source is ready.'

if [ "${1:-}" = --prepare-only ]; then
  exit 0
fi

mkdir -p .pio
BUILD_OUTPUT="$(mktemp -d .pio/v054.XXXXXX)"
trap 'rm -rf "$BUILD_OUTPUT"' EXIT
UF2_FILE_PATH="$BUILD_OUTPUT/firmware.uf2" \
  python -m platformio run -e ProMicro_companion_radio_ble -t create_uf2
test -s "$BUILD_OUTPUT/firmware.uf2"

RELEASE_DIR="${FAKETEC_RELEASE_DIR:-$HOME/Downloads/faketec-release}"
NAME='faketec-meshcore-ui-v0.5.4-ad-hoc-relay-UNTESTED.uf2'
mkdir -p "$RELEASE_DIR"
cp "$BUILD_OUTPUT/firmware.uf2" "$RELEASE_DIR/$NAME"
(
  cd "$RELEASE_DIR"
  shasum -a 256 "$NAME" | tee "$NAME.sha256"
)
echo "UF2: $RELEASE_DIR/$NAME"
