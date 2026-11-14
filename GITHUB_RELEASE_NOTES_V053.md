# FakeTec MeshCore UI v0.5.3, experimental channel relay detection

- Passive `RELAY SEEN` status for the most recent on-device channel Quick Msg, based on the exact transmitted packet's hash and a returning packet with a nonempty relay path.
- 60-second listening window after successful local transmission. No matching echo gives `UNCONFIRMED`, **not** failed delivery.
- Transient home-screen TX status, preserving the BLE pairing PIN while disconnected.
- No changes to repeater firmware, radio packet format, or acknowledgement traffic.
- Preserves v0.5.2 room destinations, double-click reverse navigation, 15 Quick Msg presets, DM and room ACK indicators, RPT FOUND and voltage display.

**Not a MeshCore channel ACK:** An echo indicates some relay retransmitted the packet. It does not count relays or prove subscriber delivery. No echo may still coincide with successful relay or reception elsewhere.

Install only on a supported FakeTec-compatible nRF52840 ProMicro companion. Source-only kit. Compile with `bash ~/Downloads/faketec-ui-v053/build-faketec-v053.sh`, then field-test the resulting UF2 before attaching it to a GitHub prerelease. The v0.5.3 source has offline patch regression and host-side C++ mock checks, not on-device RF validation.
