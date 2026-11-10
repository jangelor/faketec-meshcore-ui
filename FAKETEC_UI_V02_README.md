# FakeTec UI v0.2 Messaging (experimental)

**Target:** MeshCore 1.18 commit `81dbae592ffad40b4212bc0b37e82b38da08f4bc`, branch `feature/faketec-ui-v0.1` with `faketec_ui_v0_1_patch.py` already applied. Tested on neither a physical FakeTec nor in PlatformIO as part of this package; it must first be compiled and reviewed on the user's Mac. The v0.1 menu was reported working on the user's FakeTec. **This is a source-code patch, not ready-to-flash firmware.**

## What changes

- Upgrades the existing v0.1 long-press menu to **Inbox, Canned msgs, Find repeaters, Advertise, Back**. Available from Home or Recent Adverts. Only three items appear at a time; short press cycles and scrolls.
- **Inbox:** keeps the 12 newest direct/channel text messages in RAM, with the newest at position 1. Messages disappear on power cycle. Text is stored up to 95 characters but the OLED displays a shorter preview, and the original stock message preview still appears on arrival.
- **Quick replies:** open an inbox entry, select one preset, and reply to the **original direct contact or channel**, if still configured.
- **Canned channel messages:** select a configured channel explicitly, choose a preset, then confirm transmission. It does not automatically select Public for transmission.
- **Second confirmation:** selecting a preset first opens a summary containing **HOLD TO SEND**. Double-click cancels or navigates back. A successful transmit call displays **Queued (not delivered)**; it does not prove RF reception or message acknowledgement.

Presets in code (editable in `QuickMessagesScreen::presetText`):

1. OK
2. Yes
3. No
4. Will reply in app later
5. I'm safe
6. Need assistance
7. On my way
8. Where are you?
9. Please repeat
10. CQ CQ CQ - anyone copying?

## Install source patch only

Save `faketec_ui_v0_2_messaging_patch.py` in `~/Downloads` on the Mac.

```bash
source ~/meshcore-flash/bin/activate
cd ~/faketec-ui/MeshCore
git switch feature/faketec-ui-v0.1
python ~/Downloads/faketec_ui_v0_2_messaging_patch.py
git diff --check
git diff --stat
python -m platformio run -e ProMicro_companion_radio_ble
```

The script is idempotent (refuses to run twice), checks version anchors, and backs up both edited source files to `.v02-backup`. It does not flash hardware. Do not generate a UF2 or flash unless compilation succeeds and the intended hardware target is confirmed.

If compilation succeeds, generate a UF2 using:

```bash
python -m platformio run -e ProMicro_companion_radio_ble -t create_uf2
ls -lh .pio/build/ProMicro_companion_radio_ble/firmware.uf2
```

Do **not** distribute or flash all four units yet. Back up each device's MeshCore identity, and flash only one after checking the known-working stock target and bootloader.

## How to use

- On **Home** or **Recent Adverts**, hold User (~1 second) to open **Quick Actions**. The first 8 seconds after boot retain MeshCore's CLI/rescue behavior.
- **Short press** moves through menu items, channels, messages, or presets.
- **Long press** selects the highlighted item or enters a further menu. When you see **HOLD TO SEND**, holding again requests transmission.
- **Double press** goes back or cancels. The Reset button remains dedicated to reset/bootloader functions.
- **Inbox** shows newest first; short press browses stored messages; long press opens quick replies; double press exits.
- **Canned msgs** displays configured channels first, then presets, then a confirmation screen.

## Limitations and safety

- Sender identification is saved in RAM and replies use the currently configured contact/channel at transmission time. A deleted contact or changed channel prevents the reply.
- Messages are volatile, with a 12-message FIFO. Long messages are truncated in RAM after 95 characters and displayed as a shorter preview on OLED. Use the phone app for full messages and long-term history.
- The direct-send method reports a packet accepted into the firmware send path, not a delivery acknowledgment. Do not rely on this as a guaranteed emergency messaging system.
- The patch does not change radio defaults, BLE configuration, flash partitions, keys, or saved channels.
- The source is experimental, untested on FakeTec hardware in v0.2. Validation of UI behavior, RF transmit/receive, and recovery is required before family distribution.

## Revert v0.2 while keeping v0.1

```bash
cd ~/faketec-ui/MeshCore
cp examples/companion_radio/ui-new/UITask.cpp.v02-backup examples/companion_radio/ui-new/UITask.cpp
cp examples/companion_radio/ui-new/UITask.h.v02-backup examples/companion_radio/ui-new/UITask.h
python -m platformio run -e ProMicro_companion_radio_ble
```

These restore the source files to the tested v0.1 state. Reflashing a previously working v0.1 UF2 is a separate device operation.
