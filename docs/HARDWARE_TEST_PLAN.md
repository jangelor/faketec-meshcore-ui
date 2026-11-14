# FakeTec UI v0.5.1 device validation

Record board revision, OLED variant, bootloader details, builder environment, date, and UF2 SHA-256. Keep identities/keys private.

- [ ] Back up the known-good v0.4.1 UF2 and device identity/settings.
- [ ] Build `ProMicro_companion_radio_ble` successfully; test one device first.
- [ ] On Home, hold User to open Quick Actions with **Link Check** initially selected.
- [ ] Hold again to start Link Check. Confirm on-device results display, with no switch to the other discovery page.
- [ ] On results screen, hold to scan again without a 60-second cooldown. Short press returns Home without transmitting.
- [ ] With no repeaters responding, verify the absence of invented SNR or a false successful link.
- [ ] Validate `HEARD` (recent direct advertisements) separately from `RPT FOUND` (discovery responses). Both may differ.
- [ ] Test several scan results and ensure best responder uses weaker-direction SNR.
- [ ] Verify stale status after a scan ages out and after the device is restarted.
- [ ] Disconnect phone. Confirm pairing PIN on Home when `getBLEPin()` is nonzero; when zero, do not display a fake PIN.
- [ ] Reconnect BLE. Confirm SNR or connected-state row; verify battery display/icon.
- [ ] Select Quick Msg. Confirm order SEND, `[Quick Msg]` ON/OFF, CANCEL, with SEND highlighted initially.
- [ ] Short-press once from SEND and long-hold. Verify it toggles the marker, **without transmitting**.
- [ ] Check marker ON after reboot, because compile-time default is ON. Toggle OFF and confirm the untagged message.
- [ ] Confirm SEND requires deliberate hold, CANCEL does not transmit, rapid/double clicks cannot accidentally exit or send.
- [ ] Confirm message routing, inbox, direct replies, and configured-channel replies are preserved.
- [ ] Confirm existing Find repeaters page still operates independently.
- [ ] Test local packet behavior and BLE reconnection with intended apps, and retain a recovery path.

Repeatable Link Check generates radio traffic on each hold. Use responsibly and comply with local airtime/regulatory rules. Success of an RF discovery response does not establish message acknowledgment.

## ACK and voltage checks (v0.5.1)

Confirm that voltage appears in place of the battery icon on Home/Recent/Radio/Link Check and also in Inbox, Quick Msgs, confirmation and notification preview. Compare voltage with the companion app and a calibrated meter when available; the ADC may need board-specific calibration. Send an on-device quick direct reply and confirm its pending status. Verify that a corresponding peer ACK produces the `DM ACK received` alert, and that a channel preset does not produce an ACK claim. Test with BLE disconnected. Do not interpret ACK as read receipt or assume any fixed number of repeaters forwarded a message.
