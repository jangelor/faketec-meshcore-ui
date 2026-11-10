# FakeTec MeshCore UI v0.4.1 (experimental source)

This version adds a Quick Actions entry point from the radio-status page and renames **Canned msgs** to **Quick Msgs** throughout the visible UI and C++ method names. The Quick Actions menu now treats an accidental double-click as Next rather than Back; users exit by selecting the explicit Back row with a long hold.

Based on the earlier v0.4 feature set: a RAM inbox, reply-to-contact/channel flow, 15 configurable Quick Msgs, channel selection, confirmation before sending, optional `[Quick Msg]` marker toggle, and safe Next handling in messaging screens.

**Release status:** Source patch validated offline, not compiled or flashed in this workspace. Firmware must be built on a matching nRF52840 ProMicro checkout and tested on one device. Do not publish a UF2 as verified without a successful build and hardware test. The marker toggle is RAM-only and resets to the configured default on reboot.

Intended MeshCore baseline: `81dbae592ffad40b4212bc0b37e82b38da08f4bc`. Build environment: `ProMicro_companion_radio_ble`. No protocol/RF/keys/bootloader modifications. No delivery guarantee.
