## v0.5.3 (experimental, source-only)

- Detect a matching forwarded copy of the last Quick Msg channel transmission, using a packet hash observed in the pre-duplicate-filter receive hook. No repeater ACK or extra RF traffic.
- OLED indications distinguish queued, transmitted/listening, relay seen, unconfirmed, and local transmit failure. Compact home status preserves disconnected BLE PIN.
- Retains v0.5.2 saved room destinations and backward navigation.

# Changelog

## v0.5.2 (source preview, requires compilation and hardware testing)

- Combined Quick Msg destination selector for configured channels and saved room contacts.
- A room post is sent as an encrypted contact message to the selected room public key, rather than a channel broadcast.
- Room send pending and matched ACK status distinguish room posting from direct messages. Login is handled by phone apps, not by the on-radio interface.
- One short click advances, a double-click goes to the previous item in destinations, preset messages, inbox, and confirmation. Hold selects the current item, with explicit Back rows.
- Exactly 15 updated Quick Msg presets from the user's approved list, default `[Quick Msg]` ON.
- New one-command build script copies the compiled UF2 to `~/Downloads/faketec-release/`.

## v0.5.1 (source preview)

- Confirmation order SEND, marker toggle, CANCEL. SEND initially selected.
- One short press from SEND reaches `[Quick Msg]` toggle.
- Preset suffix ON by default after boot (JSON configuration).
- No Link Check cooldown; holding the result screen runs a fresh check.
- Home dashboard distinguishes passive HEARD and active RPT FOUND, shows age and best responsive repeater.
- Restores BLE pairing PIN to Home when disconnected and a nonzero PIN is active.
- Existing messaging, radio settings, and discovery page remain unchanged.

## v0.5 (source preview)

- Home network dashboard and first-menu Link Check.

## v0.4.1 (hardware-tested source/binary release)

- Status-screen Quick Actions access, Quick Msgs rename, safer navigation.

Additional v0.5.1 improvements:

- Battery icon/percentage replaced by measured battery voltage throughout regular OLED screens (status, radio, Link Check, inbox, preview, confirmation).
- Quick direct replies indicate ACK pending and briefly notify on a matching received ACK. This is a recipient-device ACK, not a read receipt.
- Relay-forwarding counts are not available from normal outbound messages. Received hop count, when provided, does not identify every repeater that transmitted the packet.

- Fixed rebuilds of previously patched v0.5.1 source so the legacy `REPLY` label is migrated to `RPT FOUND`; added a regression test.
