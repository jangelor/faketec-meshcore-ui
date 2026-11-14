# FakeTec MeshCore UI v0.5.1 — Source preview

This experimental **source-only** preview adds a repeatable on-device repeater Link Check and simplifies Quick Msg confirmation.

- Confirmation screen defaults to SEND. One short press selects `[Quick Msg]` ON/OFF, and a further short press selects CANCEL. A hold is required to activate the selected choice.
- `[Quick Msg]` suffix is ON by default after boot and can be toggled for the session.
- Link Check remains first in Quick Actions. No artificial cooldown. Hold from the result screen to repeat discovery, or tap to return Home.
- Home distinguishes passive `HEARD` advertisements from active `RPT FOUND` results, displays the best responding repeater when fresh, and labels stale discoveries.
- A pairing PIN appears on Home when BLE is disconnected and a nonzero PIN is available.

**Target:** FakeTec-compatible nRF52840 ProMicro MeshCore companion with matching OLED/UF2 bootloader, not Heltec V4. MeshCore 1.18 pinned commit `81dbae592ffad40b4212bc0b37e82b38da08f4bc`.

**Build status:** Offline patch tests pass. This v0.5.1 release does not include a compiled UF2, and the v0.4.1 release's firmware must not be redistributed under this version number. Build and test on one matching board before publishing a binary asset. A successful discovery response is not proof of delivery.

Additional v0.5.1 improvements:

- Battery icon/percentage replaced by measured battery voltage throughout regular OLED screens (status, radio, Link Check, inbox, preview, confirmation).
- Quick direct replies indicate ACK pending and briefly notify on a matching received ACK. This is a recipient-device ACK, not a read receipt.
- Relay-forwarding counts are not available from normal outbound messages. Received hop count, when provided, does not identify every repeater that transmitted the packet.
