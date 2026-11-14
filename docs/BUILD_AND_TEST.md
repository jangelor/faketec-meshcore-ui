# Building FakeTec UI v0.5.1

Download and unpack the source or build-kit package into `~/Downloads/faketec-meshcore-ui-v051` or `~/Downloads/faketec-ui-v051`.

```bash
cd ~/Downloads/faketec-meshcore-ui-v051  # or faketec-ui-v051
python3 test_v03_patch.py
python3 test_v04_patch.py
python3 test_v041_patch.py
python3 test_v05_patch.py
python3 test_v051_patch.py
bash build-faketec-v051.sh
```

The source tree should be `~/faketec-ui/MeshCore`, on the established MeshCore 1.18 commit and appropriate patch branch. A custom `FAKETEC_MESHCORE_ROOT` is supported only when v0.1 and v0.2 are already installed there, because the earliest patches have a fixed default root. Use your known-working Python/PlatformIO environment. The builder backs up the previous UF2 to `~/faketec-ui/backups`, deletes the old output, then rebuilds and regenerates `firmware.uf2`.

```text
~/faketec-ui/MeshCore/.pio/build/ProMicro_companion_radio_ble/firmware.uf2
```

The script does not flash hardware, does not edit bootloader/partitions/keys, and does not guarantee the board revision. Review the emitted SHA-256 hash and run the hardware test plan before uploading any UF2 to a public release.

## ACK and voltage checks (v0.5.1)

Confirm that voltage appears in place of the battery icon on Home/Recent/Radio/Link Check and also in Inbox, Quick Msgs, confirmation and notification preview. Compare voltage with the companion app and a calibrated meter when available; the ADC may need board-specific calibration. Send an on-device quick direct reply and confirm its pending status. Verify that a corresponding peer ACK produces the `DM ACK received` alert, and that a channel preset does not produce an ACK claim. Test with BLE disconnected. Do not interpret ACK as read receipt or assume any fixed number of repeaters forwarded a message.
