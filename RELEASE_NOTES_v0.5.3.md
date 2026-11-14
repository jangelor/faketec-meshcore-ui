# FakeTec MeshCore UI v0.5.3 experimental release

For **FakeTec-compatible nRF52840 ProMicro MeshCore companions with OLED**. This is **not** for Heltec ESP32-S3 radios, repeaters, or room servers.

## Updates since v0.5.1

- **v0.5.2:** Room Server contacts as Quick Msg destinations, plus one-click next and two-click previous navigation in long message lists. A room must already be authorized; its ACK is distinct from channel relay observation.
- **v0.5.2:** Updated 15 Quick Message presets, with optional `[Quick Msg]` suffix enabled by default.
- **v0.5.3:** Passive **`RELAY SEEN`** feedback after on-device channel Quick Msg sends. The radio compares the returning channel packet to the exact outgoing packet and requires a nonempty forwarding path.
- Displays `Channel: queued`, `CH sent; listening`, `RELAY SEEN`, or `No echo: unconfirmed` with a 60-second listening window. No additional packet is transmitted for this check.
- Preserves repeatable Link Check, `RPT FOUND` display, bidirectional SNR, BLE PIN when disconnected, numerical battery voltage, DM and room ACK indications, and previous Quick Msg functions.

**Interpretation:** `RELAY SEEN` indicates that the radio heard a forwarding copy of a matching channel message. It does not identify the repeater, count how many repeaters forwarded, or confirm delivery to recipients. `UNCONFIRMED` after the timeout is *not* proof of failed delivery.

## Installation

Download the **`.uf2`** asset for this release, verify its SHA-256 checksum against `SHA256SUMS.txt`, and install it using the normal nRF52840 UF2 bootloader procedure for your exact FakeTec-compatible board. Do **not** flash the UF2 onto a Heltec V4.

This build has passed source regression and native mock tests, and the contributor has reported successful on-device use of the new feature. It remains a community **experimental** release pending wider testing.

## Source

The source patch kit is attached as `faketec-ui-v053-relay-echo.zip`, with the one-command Mac build script `build-faketec-v053.sh` and tests. The same changes are maintained in branch `preview/v0.5.3`.

This independent community firmware is based on MeshCore; it is not an official MeshCore release.
