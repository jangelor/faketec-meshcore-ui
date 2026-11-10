# FakeTec MeshCore UI v0.4.1 build kit

**Target:** FakeTec-compatible nRF52840 ProMicro MeshCore companion board (NOT Heltec V4), MeshCore 1.18 commit `81dbae592ffad40b4212bc0b37e82b38da08f4bc`, PlatformIO environment `ProMicro_companion_radio_ble`.

**Status:** Offline patch tests pass. Firmware has **not** been compiled here, and v0.4.1 has **not** been tested on a physical FakeTec. This package is a source build kit, not a UF2 image. Confirm hardware, bootloader, and a valid backup before flashing one test unit.

## Changes in v0.4.1

- **Status screen access:** long-hold User on the radio-status page (frequency, spreading factor, TX power, noise floor) to open the **Quick Actions** menu. It continues to work from the main/home and recent-adverts pages.
- **Rename:** the menu item `Canned msgs` is now `Quick Msgs`; the preset screen heading is `QUICK MSGS`. The C++ method was renamed from `openCanned()` to `openQuickMsgs()`, including declaration and call sites.
- **Safety in Quick Actions:** a double-click/previous-key event advances the menu selection instead of exiting. Long-hold the explicit **Back** row to exit without sending.
- All existing v0.4 behavior remains: 15 customizable presets, 12-message RAM inbox, contextual replies, explicit channel picker, optional ` [Quick Msg]` suffix, and hold-to-select SEND/CANCEL. No automatic transmissions occur when opening or navigating menus.

## Controls

From **Home, Recent Adverts, or Radio Status**, long-hold User to open Quick Actions. Short-press cycles: `Inbox` → `Quick Msgs` → `Find repeaters` → `Advertise` → `Back`. Long-hold selects. Double-click is treated as Next while in Quick Actions rather than exiting.

Within Quick Msgs, choose the desired configured channel, select a message, and review the confirmation screen. The first choice toggles the `[Quick Msg]` marker, the second is **SEND**, and the third is **CANCEL**. Short-press moves between choices; long-hold activates the highlighted choice. Only a deliberate long-hold of **SEND** requests transmission. CANCEL returns to the preset picker.

The `[Quick Msg]` suffix defaults to OFF at each boot, as defined in `faketec_presets_v03.json`. Switching it ON or OFF using the device lasts for the current power session. The change **does not persist across reboots**. Altering the presets still requires rebuilding firmware.

Messages queued to MeshCore are not necessarily delivered or read. The firmware reports queue acceptance, not human acknowledgment.

## Build on macOS

The script uses your already working checkout at `~/faketec-ui/MeshCore`. Unzip this package into `~/Downloads/faketec-ui-v041`, then run:

```bash
cd ~/Downloads/faketec-ui-v041
python3 test_v04_patch.py
python3 test_v041_patch.py
bash build-faketec-v041.sh
```

The builder checks or applies patches in order: **v0.1 → v0.2 → v0.3 → v0.4 → v0.4.1**. Existing v0.4 sources are updated in place, with one-time `.v041-backup` copies of the C++ files. Any existing UF2 is copied into `~/faketec-ui/backups/` before the output is removed and regenerated.

The UF2 is produced only if the build succeeds:

```text
~/faketec-ui/MeshCore/.pio/build/ProMicro_companion_radio_ble/firmware.uf2
```

The build script prints a SHA-256 checksum. **It does not flash the device.** Do not use an older UF2 if compilation fails.

To target an existing alternate checkout *already patched through v0.2*, set `FAKETEC_MESHCORE_ROOT` before invoking the build script. Earlier v0.1/v0.2 patches have a fixed default home path and are not safe to run automatically against another checkout.

## Test one device first

Back up the known-good firmware and device identity/configuration. Verify the nRF52840 bootloader on the actual unit, build the correct target, and flash just one unit. Check status-page access, Home and Recent access, Quick Msgs and inbox, fast taps/double-clicks, Back behavior, `[Quick Msg]` ON/OFF, SEND/CANCEL, BLE reconnection, a direct-message reply, and a configured-channel message. Confirm both sent and received text with another device or app. Do not deploy to all four units until testing passes.

## Files

- `build-faketec-v041.sh` runs the build and protects the previous UF2.
- `faketec_ui_v0_4_1_status_patch.py` implements status access, naming, and Quick Actions protection.
- `test_v041_patch.py` tests source-patch applicability, naming, navigation, and idempotence offline.
- Earlier source patches and configuration are included, so the package can work with the established MeshCore checkout.

This kit does not modify radio parameters, BLE protocol, cryptographic keys, flash partition layout, or the bootloader. It is experimental UI firmware intended for field evaluation, including resilience and emergency communications tests, where packet and application delivery should be verified independently.
