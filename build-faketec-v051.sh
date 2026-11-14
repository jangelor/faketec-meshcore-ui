#!/bin/bash
# Build FakeTec UI v0.5.1 for the nRF52840 ProMicro companion target.
# Compile+UF2 only. Does NOT flash or alter bootloader, keys, or partitions.
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
if [ "$ROOT" != "$HOME/faketec-ui/MeshCore" ] && ! grep -q 'FAKETEC_UI_V02_MESSAGING' "$CPP"; then
  echo 'ERROR: alternate source root requires v0.1 and v0.2 already applied.' >&2
  exit 1
fi
cd "$ROOT"
if ! grep -q 'FAKETEC_UI_V01_MENU' "$CPP"; then
  python "$HERE/faketec_ui_v0_1_patch.py"
fi
if ! grep -q 'FAKETEC_UI_V02_MESSAGING' "$CPP"; then
  python "$HERE/faketec_ui_v0_2_messaging_patch.py"
fi
# Intentional v0.3 rerun updates the build-time default for the Quick Msg tag.
python "$HERE/faketec_ui_v0_3_presets_patch.py" --source-root "$ROOT" --config "$HERE/faketec_presets_v03.json" --check
python "$HERE/faketec_ui_v0_3_presets_patch.py" --source-root "$ROOT" --config "$HERE/faketec_presets_v03.json"
for spec in \
  'faketec_ui_v0_4_toggle_patch.py' \
  'faketec_ui_v0_4_1_status_patch.py' \
  'faketec_ui_v0_5_dashboard_patch.py' \
  'faketec_ui_v0_5_1_ux_patch.py' \
  'faketec_ui_v0_5_1_ack_voltage_patch.py'; do
  python "$HERE/$spec" --source-root "$ROOT" --check
  python "$HERE/$spec" --source-root "$ROOT"
done
# Upgrade v0.5.1 sources already patched with the legacy REPLY label.
# Without this migration, the idempotent UX patch leaves older display text.
python3 "$HERE/faketec_v051_rptfound_migrate.py" "$CPP"
if [ -d .git ]; then
  git diff --check
  git diff --stat
fi
python -m platformio --version
OUTPUT="$ROOT/.pio/build/ProMicro_companion_radio_ble/firmware.uf2"
if [ -s "$OUTPUT" ]; then
  BACKUPS="$HOME/faketec-ui/backups"
  mkdir -p "$BACKUPS"
  SAVED="$BACKUPS/firmware-before-v051-$(date +%Y%m%d-%H%M%S).uf2"
  cp "$OUTPUT" "$SAVED"
  echo "Previous UF2 backed up: $SAVED"
fi
rm -f "$OUTPUT"
python -m platformio run -e ProMicro_companion_radio_ble
python -m platformio run -e ProMicro_companion_radio_ble -t create_uf2
if [ ! -s "$OUTPUT" ]; then
  echo "ERROR: no v0.5.1 UF2 generated at $OUTPUT" >&2
  exit 1
fi
ls -lh "$OUTPUT"
shasum -a 256 "$OUTPUT"
echo 'v0.5.1 UF2 built, no device flashed. Test on one matching FakeTec first.'
