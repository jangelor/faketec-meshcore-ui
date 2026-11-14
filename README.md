# FakeTec MeshCore UI v0.5.1

**Status:** Source-only, experimental build kit. This version has passed offline patch checks but **has not been compiled or hardware-tested here**. The previously published v0.4.1 UF2 must not be relabeled as v0.5.1.

**Target:** FakeTec-compatible nRF52840 ProMicro companion board, matching OLED and UF2 bootloader. Upstream MeshCore 1.18, pinned commit `81dbae592ffad40b4212bc0b37e82b38da08f4bc`. PlatformIO target `ProMicro_companion_radio_ble`. Not for Heltec V4.

## What's new

- **SEND comes first:** the confirmation screen now lists **SEND → `[Quick Msg]` ON/OFF → CANCEL**. On entering confirmation, SEND is selected. One short press selects the marker toggle; hold to toggle it. A deliberate hold on SEND remains necessary to transmit.
- **Marker defaults ON:** `faketec_presets_v03.json` now sets `append_preset_marker: true`. The setting can be changed for the current device session using the confirmation menu; on reboot it returns to the compiled default.
- **No Link Check cooldown:** the one-minute UI cooldown is removed. From Home, Recent Adverts, or Radio Status, hold to open Quick Actions; **Link Check** is the first selected row, so hold again to start discovery. On the results screen, **hold to run another check**, or short press to return to Home. Checks are user-initiated and one request is sent per deliberate hold. MeshCore's own airtime/queue limits remain applicable.
- **Less ambiguous Home dashboard:** `MSG` (unread), `HEARD` (direct repeater advertisements received during the last 30 minutes, limited cache), and `RPT FOUND` (repeaters responding to the last active discovery, including scans from the dedicated Find repeaters page). Results have an age and become stale after 10 minutes. `BEST` names the responder ranked by the weaker of its incoming/outgoing SNR; when there is no fresh responding repeater, `SEEN` names the last directly advertised repeater when available.
- **Voltage in place of the battery icon:** The top-right of the Home, Radio Status, Recent Adverts, Link Check, message-preview, Inbox, Quick Msgs, and confirmation screens shows the measured voltage (for example `3.91V`). USB charging and muted-buzzer symbols remain on Home pages. A `--.--V` placeholder appears if the board reports zero millivolts. The battery percent is removed from the OLED header. This uses the board ADC and depends on its calibration, not a dedicated fuel gauge.
- **Direct-message ACK indication:** When sending an on-device preset as a direct reply, the radio shows `DM: awaiting ACK`. When the MeshCore listener receives the matching ACK token, it briefly shows `DM ACK received`, including with the phone disconnected. It tracks up to four recent direct sends in RAM for five minutes, without persistent message history. Channel messages do not have these per-recipient ACKs. No forwarded-repeater count is claimed.
- **BLE PIN restored:** if no phone is connected and a nonzero pairing PIN is active, the last Home row shows `PIN:XXXXXX` and the battery voltage. Otherwise, it shows BLE connection status and battery voltage, or fresh SNR readings if connected. The measured voltage replaces the battery icon throughout the regular OLED UI.

## Home-screen layout

On the 128×64 OLED, the four body rows are approximately:

```
MSG:0 HEARD:0
RPT FOUND:2 0m
BEST: Antipolo RPT
I:+8.0 O:+5.0dB
```

When disconnected with a pairing PIN available, the last row is replaced by a display such as `PIN:123456 B:3.90V`. The PIN is displayed **only on the user's device**. It is not uploaded or sent to GitHub. The name, counts, and readings are examples; live figures come from MeshCore's local state.

`HEARD:0` can coexist with `RPT FOUND:2`, because passive advertisements and active discovery responses are different measurements. `BEST` is a *radio-link* ranking, not a distance estimate or proof that messages were delivered.

## Build on macOS

Download and extract the v0.5.1 build kit (`~/Downloads/faketec-ui-v051`) or GitHub source package (`~/Downloads/faketec-meshcore-ui-v051`). On the Mac with the existing MeshCore checkout at `~/faketec-ui/MeshCore`:

```bash
cd ~/Downloads/faketec-meshcore-ui-v051  # or ~/Downloads/faketec-ui-v051
python3 test_v03_patch.py
python3 test_v04_patch.py
python3 test_v041_patch.py
python3 test_v05_patch.py
python3 test_v051_patch.py
python3 test_v051_ack_voltage_patch.py
bash build-faketec-v051.sh
```

The builder also migrates an existing v0.5.1 tree that still displays `REPLY` to `RPT FOUND`, so rebuilding against previously patched sources is safe. It applies/checks patches in order v0.1 → v0.2 → v0.3 → v0.4 → v0.4.1 → v0.5 → v0.5.1 UX → ACK/voltage, backs up any previous UF2, compiles for `ProMicro_companion_radio_ble`, and creates `~/faketec-ui/MeshCore/.pio/build/ProMicro_companion_radio_ble/firmware.uf2` only when compilation succeeds. It does **not** flash the radio.

If you previously customized `faketec_presets_v03.json` in another folder, merge your custom messages into this package's JSON first. The included configuration will be applied to the source during the build.

## Field tests before public binary release

Test on one matching FakeTec: normal status startup, Link Check twice consecutively (no 60-second cooldown), discovery responses and no-reply case, HOME counts and stale behavior, PIN visibility with phone disconnected, BLE reconnect, voltage across all screens, direct-send ACK pending and matching ACK alerts with/without phone, Quick Msg ON/OFF and startup default after reboot, SEND-first selection, CANCEL behavior, and safe short/double presses. Preserve a known-good firmware and identity/settings backup. Do not publish any device private keys or backups.

Based on open-source MeshCore; independent AI-assisted modification. Source build kit and documentation are provided for inspection and community testing.
