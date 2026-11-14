# FakeTec UI v0.5.2 experimental Quick Msg room support

Target: FakeTec-compatible **nRF52840 ProMicro companion** with OLED, pinned upstream MeshCore `81dbae592ffad40b4212bc0b37e82b38da08f4bc`. This is not Heltec V4 firmware. No binary is included; compile with the one-step script below.

## Changes from v0.5.1

- **Quick Msg destination list** now includes all configured channels and saved Room Server contacts (`ADV_TYPE_ROOM`), followed by an explicit **Back** option. Choose the destination first, then select a preset, then hold **SEND** at the confirmation screen. Channels and rooms are separately labeled there.
- **Button navigation:** one short click moves **forward** through preset text, destination choices, inbox entries and confirmation options; two quick clicks move **backward**. A deliberate hold selects the highlighted option. A double-click **never sends** or exits the Quick Msg screen. The preset list has an explicit **Back** row.
- **Room messages:** use the same encrypted contact-message transmission mechanism as MeshCore phone apps. Room contact public keys are checked again just before sending, so the recipient cannot silently change when contacts are updated. The user must already have been authenticated to the room using an app and have posting permission. The OLED cannot log in or guarantee the login is active. A queued transmission is **not** proof a room stored it. When the room accepts and ACKs the post, the OLED reports **Room post ACK**. If no ACK arrives, do not assume delivery.
- The 15 requested presets are included exactly in `faketec_presets_v03.json`, with `[Quick Msg]` enabled by default. They are editable before compilation.
- All prior v0.5.1 status features remain in the source, including battery voltage, BLE PIN, Link Check without cooldown, `RPT FOUND`, and DM ACK indicators.

## One-command build on macOS

Extract the ZIP to `~/Downloads/faketec-ui-v052`. From Terminal:

```bash
bash ~/Downloads/faketec-ui-v052/build-faketec-v052.sh
```

The script uses your existing checkout at `~/faketec-ui/MeshCore` and existing PlatformIO environment. It checks and installs earlier patches if missing, applies the 15 presets, applies the room/navigation patch, builds the UF2, then copies it to:

```
~/Downloads/faketec-release/faketec-meshcore-ui-v0.5.2-rooms-nav-test.uf2
```

This build does **not** flash any device. If compilation fails, no new UF2 is copied. Existing compiled UF2 is backed up before rebuilding.

Optional source-only regression checks:

```bash
cd ~/Downloads/faketec-ui-v052
python3 test_v052_rooms_nav_patch.py
```

## Field test sequence

1. Add a Room Server to contacts using MeshCore Open, Kiekr or another compatible app; log in and verify that posting is permitted. Merely seeing the room in the list does not establish an authenticated session.
2. With the phone disconnected, open Quick Msgs and check that **ROOM** and **CHANNEL** choices are labeled clearly. One click should move forward, two clicks backward, including at the 15-preset list. Selecting Back should return without sending.
3. Send a unique preset to the room. Confirm on a second device/identity that the room accepted it. Watch for `Room post ACK`. If the ACK is missing, check login and radio coverage.
4. Verify that normal channel messages and inbox replies still work, that `[Quick Msg]` toggles normally, and that SEND requires an intentional hold.

**Status:** Source patch with offline regression checks. The v0.5.2 binary must be compiled and tested on the user's physical FakeTec before GitHub release. Do not rename an older UF2 to v0.5.2.
