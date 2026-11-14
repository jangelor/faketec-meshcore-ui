#!/usr/bin/env python3
"""FakeTec UI v0.5.1 follow-on: on-device DM ACK + voltage in OLED headers.

Requires prior v0.5.1 UX patch and target MeshCore 1.18 (pinned revision).
Source-only: no flashing, configuration, secrets or network transmissions.
"""
import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

MARKER = 'FAKETEC_UI_V051_ACK_VOLTAGE'


def once(src, old, new, label):
    found = src.count(old)
    if found != 1:
        raise ValueError('%s: expected 1 anchor, got %d' % (label, found))
    return src.replace(old, new, 1)


def patch_cpp(src):
    if MARKER in src:
        return src
    if 'FAKETEC_UI_V051_UX' not in src or 'FAKETEC_UI_V02_MESSAGING' not in src:
        raise ValueError('Requires v0.5.1 messaging source, not stock MeshCore')

    # The original HomeScreen battery indicator is shared across ALL Home pages,
    # including the radio page and Link Check result overlay. Preserve the
    # independent charging and mute indicators without retaining the battery icon.
    indicator_start = '  void renderBatteryIndicator(DisplayDriver& display, uint16_t batteryMilliVolts) {'
    indicator_end = '\n  CayenneLPP sensors_lpp;'
    if src.count(indicator_start) != 1 or src.count(indicator_end) != 1:
        raise ValueError('HomeScreen battery indicator anchors absent')
    head, rest = src.split(indicator_start, 1)
    old_method, tail = rest.split(indicator_end, 1)
    if 'display.drawRect(iconX, iconY, iconWidth, iconHeight)' not in old_method:
        raise ValueError('Unexpected battery icon layout, refusing to replace')
    new_method = '''  // FAKETEC_UI_V051_ACK_VOLTAGE: actual ADC-derived battery volts, not %.
  void renderBatteryIndicator(DisplayDriver& display, uint16_t batteryMilliVolts) {
    char voltage[10];
    if (batteryMilliVolts == 0) {
      snprintf(voltage, sizeof(voltage), "--.--V");
    } else {
      snprintf(voltage, sizeof(voltage), "%.2fV", (float)batteryMilliVolts / 1000.0f);
    }
    display.setTextSize(1);
    display.setColor(UIColor::title_txt);
    const int x = display.width() - display.getTextWidth(voltage) - 2;
    display.setCursor(x, 2);
    display.print(voltage);
    const bool charging = board.isExternalPowered();
    if (charging) {
      display.drawXbm(x - 11, 2, charging_icon, 8, 8);
    }
#ifdef PIN_BUZZER
    if (_task->isBuzzerQuiet()) {
      display.setColor(UIColor::warning_txt);
      display.drawXbm(x - (charging ? 21 : 11), 2, muted_icon, 8, 8);
    }
#endif
  }
'''
    src = head + new_method + indicator_end + tail
    src = once(src,
        '''    display.setCursor(0, 2);
    display.print(filtered_name);
''',
        '''    // Reserve header space for voltage, charging and mute symbols.
    display.drawTextEllipsized(0, 2, display.width() - 54, filtered_name);
''', 'header node-name collision guard')

    # The stock message preview also occupies its own screen, independent of
    # HomeScreen, and therefore needs an explicit voltage readout.
    src = once(src,
        '''    display.setCursor(display.width() - display.getTextWidth(tmp) - 2, 0);
    display.print(tmp);

    display.drawRect(0, 11, display.width(), 1);''',
        '''    display.setCursor(60, 0);  // message age, between count and voltage
    display.print(tmp);
    char preview_voltage[10];
    const uint16_t preview_mv = _task->getBattMilliVolts();
    if (preview_mv) snprintf(preview_voltage, sizeof(preview_voltage), "%.2fV", (float)preview_mv / 1000.0f);
    else snprintf(preview_voltage, sizeof(preview_voltage), "--.--V");
    display.setCursor(display.width() - display.getTextWidth(preview_voltage) - 1, 0);
    display.print(preview_voltage);

    display.drawRect(0, 11, display.width(), 1);''', 'message preview voltage header')

    src = once(src,
        '''  uint8_t confirm_choice = 0;  // 0=SEND, 1=tag toggle, 2=CANCEL
''',
        '''  uint8_t confirm_choice = 0;  // 0=SEND, 1=tag toggle, 2=CANCEL
  // Up to 4 recently sent on-device DMs can await ACK independently.
  // These are ACK tokens, not message contents or keys, and remain in RAM.
  uint32_t pending_dm_ack[4] = {0, 0, 0, 0};
  uint32_t pending_dm_at_ms[4] = {0, 0, 0, 0};
  uint8_t next_ack_slot = 0;

  void renderVoltage(DisplayDriver& display) const {
    char voltage[10];
    const uint16_t mv = task->getBattMilliVolts();
    if (mv) snprintf(voltage, sizeof(voltage), "%.2fV", (float)mv / 1000.0f);
    else snprintf(voltage, sizeof(voltage), "--.--V");
    display.setTextSize(1);
    display.setColor(UIColor::primary_txt);
    display.setCursor(display.width() - display.getTextWidth(voltage) - 1, 0);
    display.print(voltage);
  }
''', 'ACK tracker and per-screen voltage helper')

    src = once(src,
        '''    uint32_t timestamp = the_mesh.getRTCClock()->getCurrentTimeUnique();
    bool queued = false;
''',
        '''    uint32_t timestamp = the_mesh.getRTCClock()->getCurrentTimeUnique();
    bool queued = false;
    uint32_t direct_expected_ack = 0;
''', 'prepare expected ACK tracking')
    src = once(src,
        '''            queued = the_mesh.sendMessage(*recipient, timestamp, 0, message,
                                            expected_ack, timeout) != MSG_SEND_FAILED;
''',
        '''            queued = the_mesh.sendMessage(*recipient, timestamp, 0, message,
                                            expected_ack, timeout) != MSG_SEND_FAILED;
            if (queued) direct_expected_ack = expected_ack;
''', 'capture direct-message ACK token')
    src = once(src,
        '''    task->showAlert(queued ? "Queued (not delivered)" : "Send failed", 1800);
    // End confirmation workflow even on failure: repeat requires deliberate re-selection.
''',
        '''    if (queued && direct_expected_ack != 0) {
      pending_dm_ack[next_ack_slot] = direct_expected_ack;
      pending_dm_at_ms[next_ack_slot] = millis();
      next_ack_slot = (next_ack_slot + 1) % 4;
    }
    task->showAlert(!queued ? "Send failed" :
                    direct_expected_ack ? "DM: awaiting ACK" :
                    "Queued (not delivered)", 1800);
    // End confirmation workflow even on failure: repeat requires deliberate re-selection.
''', 'display ACK-pending status and store token')
    src = once(src,
        '''  void addDirect(const ContactInfo& from, const char* text) {
''',
        '''  void noteAck(uint32_t ack_crc) {
    if (!ack_crc) return;
    for (int i = 0; i < 4; ++i) {
      if (pending_dm_ack[i] == ack_crc &&
          (uint32_t)(millis() - pending_dm_at_ms[i]) <= 300000UL) {
        pending_dm_ack[i] = 0; // prevents duplicate ACK popups
        task->showAlert("DM ACK received", 2200);
        return;
      }
    }
  }

  void addDirect(const ContactInfo& from, const char* text) {
''', 'matching direct ACK status')

    # The on-device inbox, channel picker, preset selector, and send-confirm
    # screens all show voltage. Reposition only the counters / confirmation
    # content that previously used the upper-right corner.
    src = once(src,
        '''        display.drawTextCentered(display.width()/2, 50, "Hold: Back");
        return 1000;
''',
        '''        display.drawTextCentered(display.width()/2, 50, "Hold: Back");
        renderVoltage(display);
        return 1000;
''', 'empty inbox voltage')
    src = once(src,
        '''      display.setCursor(display.width() - display.getTextWidth(label), 1);
      display.print(label);
''',
        '''      display.setCursor(36, 1); // leave right corner for voltage
      display.print(label);
''', 'inbox count relocation')
    src = once(src,
        '''      display.setCursor(display.width() - display.getTextWidth(label), 0);
      display.print(label);
''',
        '''      display.setCursor(66, 0); // fits beside QUICK REPLY + voltage
      display.print(label);
''', 'preset count relocation')
    src = once(src,
        '''      display.setCursor(0, 0);
      display.print("TO:");
      display.print(destination);
      char preview[21];
''',
        '''      display.setCursor(0, 0);
      display.print("TO:");
      display.setCursor(0, 10);
      display.print(destination);
      char preview[21];
''', 'confirm destination second line')
    src = once(src,
        '''      display.setCursor(0, 11);
      display.print(preview);
      display.setCursor(0, 28);
      display.print(confirm_choice == 0 ? "> SEND" : "  SEND");
      display.setCursor(0, 40);
''',
        '''      display.setCursor(0, 20);
      display.print(preview);
      display.setCursor(0, 30);
      display.print(confirm_choice == 0 ? "> SEND" : "  SEND");
      display.setCursor(0, 41);
''', 'confirm OLED layout 1')
    src = once(src,
        '''      display.setCursor(0, 52);
      display.print(confirm_choice == 2 ? "> CANCEL" : "  CANCEL");
    }
    return 1000;
''',
        '''      display.setCursor(0, 52);
      display.print(confirm_choice == 2 ? "> CANCEL" : "  CANCEL");
    }
    renderVoltage(display); // every Quick Msg screen
    return 1000;
''', 'confirm OLED layout 2 and voltage')

    # Reclaim duplicated battery-voltage text from Home page body now that
    # actual voltage is always in the upper-right corner.
    src = once(src,
        '"PIN:%06lu B:%.2fV", (unsigned long)pin,\n                   (float)_task->getBattMilliVolts() / 1000.0f',
        '"PIN:%06lu BLE:OFF", (unsigned long)pin', 'disconnected pairing pin row')
    src = once(src,
        '''"BLE:WAIT B:%.2fV",
                   (float)_task->getBattMilliVolts() / 1000.0f''',
        '''"BLE:WAIT"''', 'BLE wait without duplicate voltage')
    src = once(src,
        '''"BLE:ON B:%.2fV",
                   (float)_task->getBattMilliVolts() / 1000.0f''',
        '''"BLE:ON"''', 'BLE connected without duplicate voltage')

    src = once(src,
        '''void UITask::onQueueSizeChanged(int msgcount) {''',
        '''void UITask::onACKRecv(uint32_t ack_crc) {
  // MyMesh invokes this listener for received ACKs even without a phone.
  if (quick_messages) ((QuickMessagesScreen*)quick_messages)->noteAck(ack_crc);
}

void UITask::onQueueSizeChanged(int msgcount) {''', 'register ACK listener')
    if src.count(MARKER) != 1:
        raise ValueError('v0.5.1 ACK/voltage marker invariant failed')
    return src


def patch_header(hdr):
    if '  void onACKRecv(uint32_t ack_crc) override;' in hdr:
        return hdr
    return once(hdr,
        '  void onQueueSizeChanged(int offline_queue_size) override;',
        '  void onQueueSizeChanged(int offline_queue_size) override;\n  void onACKRecv(uint32_t ack_crc) override;  // FAKETEC_UI_V051_ACK_VOLTAGE',
        'UITask ACK callback declaration')


def atomic_write(path, content):
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '.v051volt.', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root', type=Path, default=Path.home() / 'faketec-ui' / 'MeshCore')
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    cpp = args.source_root / 'examples/companion_radio/ui-new/UITask.cpp'
    hdr = args.source_root / 'examples/companion_radio/ui-new/UITask.h'
    try:
        s = cpp.read_text(encoding='utf-8')
        h = hdr.read_text(encoding='utf-8')
        ns = patch_cpp(s)
        nh = patch_header(h)
    except (OSError, ValueError) as e:
        sys.exit('ERROR: no files saved: %s' % e)
    if args.check:
        print('Dry-run OK: replace battery icon with voltage across UI; track direct ACKs.')
        return
    if ns == s and nh == h:
        print('ACK/voltage patch already applied; no changes needed.')
        return
    for path in (cpp, hdr):
        backup = path.with_name(path.name + '.v051-ack-voltage-backup')
        if not backup.exists():
            shutil.copy2(path, backup)
    atomic_write(cpp, ns)
    atomic_write(hdr, nh)
    print('Applied ACK/voltage patch; no firmware compiled or flashed.')


if __name__ == '__main__':
    main()
