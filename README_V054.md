# FakeTec v0.5.4 ad hoc relay preview

Target an OLED FakeTec with a compatible nRF52840 ProMicro and UF2 bootloader. The PlatformIO environment is `ProMicro_companion_radio_ble` and the MeshCore 1.18 base is `81dbae592ffad40b4212bc0b37e82b38da08f4bc`.

## OLED controls

From Home, Recent Adverts, or Radio Status, hold the user button to open **Quick Actions**. Tap to highlight **Ad hoc relay OFF**, then hold to enable it. The Home pages display **RLY** while the local toggle is on. Select the same row to turn it off. The OLED relay toggle starts off on every boot.

The radio uses the active frequency, bandwidth, spreading factor, and coding rate to forward eligible MeshCore packets. Quick Messages, room posting, and app messaging can be used while forwarding. The OLED toggle operates independently of the app's Off-grid Repeat Mode. `RELAY SEEN` still reports a matching rebroadcast of an outgoing Quick Msg.

## Build

Use the established checkout at `~/faketec-ui/MeshCore` or set `FAKETEC_MESHCORE_ROOT` to a local checkout. A fresh checkout needs the pinned MeshCore commit and a local `feature/faketec-ui-v0.1` branch so the existing v0.2 patch can apply. A checkout already prepared with v0.5.3 can be used directly. Use a Python environment with PlatformIO installed.

```sh
bash build-faketec-v054.sh
```

Pass `--prepare-only` to apply the patches without compiling. The build copies the application UF2 and its SHA-256 to `~/Downloads/faketec-release/`, or the path in `FAKETEC_RELEASE_DIR`.

## Bench test

Use one matching FakeTec first. Confirm OLED navigation, BLE, and Quick Messages. With the app's Off-grid Repeat Mode off, place two other companions out of direct range and verify that a packet and DM acknowledgment can traverse the FakeTec with the OLED relay on. Check the route with the toggle off and confirm that it returns to off after reboot. Use the hardware results to qualify any public release.
