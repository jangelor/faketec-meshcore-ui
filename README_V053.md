# FakeTec MeshCore UI v0.5.3 experimental relay echo indicator

Target: FakeTec-compatible **nRF52840 ProMicro MeshCore companion with OLED**. The patch is based on the same pinned MeshCore source (`81dbae592ffad40b4212bc0b37e82b38da08f4bc`) as previous FakeTec UI builds. **Do not flash this on a Heltec V4 or other hardware.**

## New in v0.5.3

For **Quick Msg channel sends**, the FakeTec now watches the exact transmitted radio packet for a returned **on-air retransmission**. This is passive: it does **not** transmit any extra packets, request a network-wide ACK, or require modified repeater firmware.

| OLED | Precise interpretation |
|---|---|
| `Channel: queued` | The packet was formed and placed into the MeshCore send queue, but has not yet been confirmed transmitted by the radio |
| `CH sent; listening` | The local radio has completed transmission; a 60-second period for a matching rebroadcast begins |
| `RELAY SEEN` | The local radio received the same channel packet back over the air with a nonempty relay path, indicating at least one forwarding radio retransmitted it |
| `No echo: unconfirmed` | No matching retransmission was heard within 60 seconds. **This does not mean the outgoing message failed.** |
| `Channel TX failed` | MeshCore reported a local radio transmission failure |
| `Channel TX unknown` | No local radio transmission result was observed before the five-minute queue watchdog expired |

The home screen displays a compact `TX:Q`, `TX:WAIT`, `TX:RELAY`, `TX:NOECHO`, `TX:FAIL`, or `TX:TX?` indication for 120 seconds after the last status event. When a phone is disconnected and a BLE pairing PIN is active, the PIN remains visible. The bottom line temporarily replaces the cached IN/OUT link SNR display; the separate Link Check screen continues to show it.

**Important limitations:** `RELAY SEEN` is *not* a recipient acknowledgement, does not identify or count repeaters, and does not prove the message reached a particular contact. It indicates a retransmission by at least one forwarding radio. The check only succeeds if the FakeTec hears the forwarded copy. Some legitimate forwarding events will not be heard. A normal MeshCore channel does not offer DM-style acknowledgements. DM and Room Server acknowledgement displays remain unchanged.

The watcher follows only the **most recent on-device channel Quick Msg**. This prevents an old message's echo from confirming a newer one. Phone-app messages are not included. Short-click NEXT and double-click PREVIOUS navigation, Room Server targets, the 15 Quick Msg presets, `RPT FOUND`, voltage, BLE PIN, and cooldown-free Link Check are retained.

## One-command build on your Mac

Extract the ZIP so its folder is `~/Downloads/faketec-ui-v053`, then run:

```sh
bash ~/Downloads/faketec-ui-v053/build-faketec-v053.sh
```

The script uses the existing checkout at `~/faketec-ui/MeshCore`, validates and applies earlier patches if required, installs the v0.5.3 three-file relay detector, backs up any existing UF2, and compiles the firmware with PlatformIO. It does **not** flash hardware.

When successful, the ready-to-flash UF2 is copied to:

```text
~/Downloads/faketec-release/faketec-meshcore-ui-v0.5.3-relay-echo-test.uf2
```

The script also creates a `.sha256` file. It leaves your current radio identity, contacts, and key data untouched because it does not connect to a device.

## Test procedure

1. Test on one matching FakeTec. Verify the UI remains functional, including room targets and DM ACK indications.
2. Use Quick Msgs to post a short preset to a configured channel through a repeater that your FakeTec can also receive directly.
3. Observe `Channel: queued`, then `CH sent; listening`. A valid matching return packet should trigger `RELAY SEEN` and `TX:RELAY` on the home screen.
4. Repeat with the repeater offline or with a poor return link. After 60 seconds, expect `No echo: unconfirmed`. **Do not interpret this as failed delivery.**
5. Check that a nearby unrelated channel packet does not cause a false `RELAY SEEN`, and that successive channel sends watch the latest transmission only.
6. Test with and without the phone connected. Ensure the disconnected BLE PIN and voltage displays remain visible.

## QA scope

The package includes source-patch regression tests and a native C++ mock for the relay state machine. These do not constitute a completed nRF52840 firmware build or hardware validation. The first actual UF2 needs to be compiled on your Mac and field-tested before any GitHub experimental release.
