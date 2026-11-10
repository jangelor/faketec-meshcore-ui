#!/bin/bash
# Build FakeTec UI v0.4.1 for the nRF52840 ProMicro companion board.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${FAKETEC_MESHCORE_ROOT:-$HOME/faketec-ui/MeshCore}"
CPP="$ROOT/examples/companion_radio/ui-new/UITask.cpp"
if [ -f "$HOME/meshcore-flash/bin/activate" ]; then
  . "$HOME/meshcore-flash/bin/activate"
fi
if [ ! -f "$CPP" ]; then
  echo "ERROR: MeshCore source missing: $CPP" >&2
  exit 1
fi
# v0.1 and v0.2 original patches use an absolute default source location.
if [ "$ROOT" != "$HOME/faketec-ui/MeshCore" ] && ! grep -q 'FAKETEC_UI_V02_MESSAGING' "$CPP"; then
  echo 'ERROR: custom source root requires v0.1/v0.2 already applied.' >&2
  exit 1
fi
cd "$ROOT"
if ! grep -q 'FAKETEC_UI_V01_MENU' "$CPP"; then
  python "$HERE/faketec_ui_v0_1_patch.py"
fi
if ! grep -q 'FAKETEC_UI_V02_MESSAGING' "$CPP"; then
  python "$HERE/faketec_ui_v0_2_messaging_patch.py"
fi
# The v0.3 script is deliberately rerunnable and leaves v0.4 unchanged if
# the preset JSON has not changed. This ensures presets remain editable.
python "$HERE/faketec_ui_v0_3_presets_patch.py" --source-root "$ROOT" --config "$HERE/faketec_presets_v03.json" --check
python "$HERE/faketec_ui_v0_3_presets_patch.py" --source-root "$ROOT" --config "$HERE/faketec_presets_v03.json"
python "$HERE/faketec_ui_v0_4_toggle_patch.py" --source-root "$ROOT" --check
python "$HERE/faketec_ui_v0_4_toggle_patch.py" --source-root "$ROOT"
python "$HERE/faketec_ui_v0_4_1_status_patch.py" --source-root "$ROOT" --check
python "$HERE/faketec_ui_v0_4_1_status_patch.py" --source-root "$ROOT"
if [ -d .git ]; then
  git diff --check
  git diff --stat
fi
python -m platformio --version
OUTPUT="$ROOT/.pio/build/ProMicro_companion_radio_ble/firmware.uf2"
if [ -s "$OUTPUT" ]; then
  BACKUPS="$HOME/faketec-ui/backups"
  mkdir -p "$BACKUPS"
  SAVED="$BACKUPS/firmware-before-v041-$(date +%Y%m%d-%H%M%S).uf2"
  cp "$OUTPUT" "$SAVED"
  echo "Preserved previous UF2 at $SAVED"
fi
rm -f "$OUTPUT"
python -m platformio run -e ProMicro_companion_radio_ble
python -m platformio run -e ProMicro_companion_radio_ble -t create_uf2
if [ ! -s "$OUTPUT" ]; then
  echo "ERROR: No v0.4.1 UF2 generated at $OUTPUT" >&2
  exit 1
fi
ls -lh "$OUTPUT"
shasum -a 256 "$OUTPUT"
echo 'v0.4.1 UF2 built; no hardware flashed. Test only one FakeTec first.'
