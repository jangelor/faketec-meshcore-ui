# Changelog

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
