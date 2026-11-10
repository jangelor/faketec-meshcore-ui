#!/usr/bin/env python3
"""FakeTec UI v0.4: safe one-button navigation and [Quick Msg] toggle.

Apply after FakeTec UI v0.1, v0.2, and v0.3 on the pinned MeshCore 1.18
source. Converts unintended double-click Back into a safe Next action, adds
explicit Back choices, and requires long-hold to select SEND or CANCEL.
No RF, BLE, NVS, partition, or bootloader modifications. Does not flash.
"""
import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

MARKER = 'FAKETEC_UI_V04_SAFE_BUTTONS'


def replace_once(s, old, new, label):
    n = s.count(old)
    if n != 1:
        raise ValueError('%s anchor mismatch: expected 1, found %d' % (label, n))
    return s.replace(old, new, 1)


def patch_source(s):
    if MARKER in s:
        return s
    if ('FAKETEC_UI_V02_MESSAGING' not in s or
        'FAKETEC_UI_V03_PRESETS' not in s or
        'FAKETEC_UI_V03_SEND_MARKER' not in s):
        raise ValueError('Requires existing FakeTec UI v0.2 + v0.3 messaging patches')

    s = replace_once(s,
        '''  bool reply_mode = false;
  Mode mode = INBOX;
''',
        '''  bool reply_mode = false;
  Mode mode = INBOX;
  // FAKETEC_UI_V04_SAFE_BUTTONS: no double-click-to-exit in messaging.
  bool append_marker = false;
  bool channel_back_selected = false;
  uint8_t confirm_choice = 0;  // 0=tag toggle, 1=SEND, 2=CANCEL
''', 'new runtime state')

    s = replace_once(s,
        '''    if (count == 0) return NULL;
    return &items[(head + HISTORY - age) % HISTORY];
''',
        '''    if (count == 0 || age >= count) return NULL;  // extra list item is BACK
    return &items[(head + HISTORY - age) % HISTORY];
''', 'safe inbox selection')

    s = replace_once(s,
        '''    if (kAppendPresetMarker) {
''',
        '''    if (append_marker) {
''', 'runtime tag state')

    s = replace_once(s,
        '''  explicit QuickMessagesScreen(UITask* owner) : task(owner) { }''',
        '''  explicit QuickMessagesScreen(UITask* owner) : task(owner) {
    append_marker = kAppendPresetMarker;  // JSON controls startup default
  }''', 'runtime startup default')

    s = replace_once(s,
        '''    age = 0;
    reply_mode = true;
  }

  void openCanned() {''',
        '''    age = 0;
    reply_mode = true;
    confirm_choice = 0;
  }

  void openCanned() {''', 'open inbox')

    s = replace_once(s,
        '''    channel_idx = nextChannel(-1);
    preset = 0;
  }

  int render(DisplayDriver& display) override {''',
        '''    channel_idx = nextChannel(-1);
    channel_back_selected = channel_idx < 0;
    preset = 0;
    confirm_choice = 0;
  }

  int render(DisplayDriver& display) override {''', 'open channels')

    s = replace_once(s,
        '''      if (count == 0) {
        display.drawTextCentered(display.width()/2, 27, "No messages yet");
        display.drawTextCentered(display.width()/2, 50, "2 clicks: Back");
        return 1000;
      }
      Entry* e = selected();
''',
        '''      if (count == 0 || age == count) {
        display.drawTextCentered(display.width()/2, 25,
                                 count == 0 ? "No messages yet" : "< BACK >");
        display.drawTextCentered(display.width()/2, 50, "Hold: Back");
        return 1000;
      }
      Entry* e = selected();
''', 'inbox Back row')

    s = replace_once(s,
        '''      if (channel_idx < 0) {
        display.drawTextCentered(display.width()/2, 29, "No channels set");
      } else {
        ChannelDetails ch;
        if (the_mesh.getChannel(channel_idx, ch)) {
          display.setCursor(0, 22);
          display.print(ch.name);
        }
        display.setCursor(0, 50);
        display.print("Hold: Select");
      }
''',
        '''      if (channel_back_selected || channel_idx < 0) {
        display.drawTextCentered(display.width()/2, 29,
                                 channel_idx < 0 ? "No channels set" : "< BACK >");
        display.setCursor(0, 50);
        display.print("Hold: Back");
      } else {
        ChannelDetails ch;
        if (the_mesh.getChannel(channel_idx, ch)) {
          display.setCursor(0, 22);
          display.print(ch.name);
        }
        display.setCursor(0, 50);
        display.print("Hold: Select");
      }
''', 'channel Back row')

    s = replace_once(s,
        '''      snprintf(label, sizeof(label), "%u/%u", (unsigned)(preset+1),
               (unsigned)PRESET_COUNT);
      display.setCursor(display.width() - display.getTextWidth(label), 0);
      display.print(label);
      display.setCursor(0, 17);
      display.printWordWrap(presetText(preset), display.width());
      display.setCursor(0, 54);
      display.print("Hold: Confirm");
''',
        '''      snprintf(label, sizeof(label), "%u/%u", (unsigned)(preset+1),
               (unsigned)(PRESET_COUNT + 1));
      display.setCursor(display.width() - display.getTextWidth(label), 0);
      display.print(label);
      display.setCursor(0, 17);
      if (preset == PRESET_COUNT) {
        display.drawTextCentered(display.width()/2, 27, "< BACK >");
        display.setCursor(0, 54);
        display.print("Hold: Back");
      } else {
        display.printWordWrap(presetText(preset), display.width());
        display.setCursor(0, 54);
        display.print("Hold: Select");
      }
''', 'preset Back row')

    s = replace_once(s,
        '''      display.setCursor(0, 0);
      display.print("SEND TO:");
      if (reply_mode) {
        Entry* e = selected();
        display.setCursor(0, 12);
        display.print(e ? e->from : "Unknown");
      } else if (channel_idx >= 0) {
        ChannelDetails ch;
        if (the_mesh.getChannel(channel_idx, ch)) {
          display.setCursor(0, 12);
          display.print(ch.name);
        }
      }
      display.setCursor(0, 25);
      display.printWordWrap(presetText(preset), display.width());
      display.setCursor(0, 54);
      display.print("HOLD TO SEND");
''',
        '''      // One-button confirmation menu; only holding SEND actually transmits.
      // Destination is shown for safety before the user selects SEND.
      char destination[19];
      snprintf(destination, sizeof(destination), "%.18s", "Unknown");
      if (reply_mode) {
        Entry* e = selected();
        if (e) snprintf(destination, sizeof(destination), "%.18s", e->from);
      } else if (channel_idx >= 0) {
        ChannelDetails ch;
        if (the_mesh.getChannel(channel_idx, ch))
          snprintf(destination, sizeof(destination), "%.18s", ch.name);
      }
      display.setCursor(0, 0);
      display.print("TO:");
      display.print(destination);
      char preview[21];
      snprintf(preview, sizeof(preview), "%.17s", presetText(preset));
      if (strlen(presetText(preset)) > 17) strcat(preview, "...");
      display.setCursor(0, 11);
      display.print(preview);
      display.setCursor(0, 28);
      display.print(confirm_choice == 0 ? "> " : "  ");
      display.print(append_marker ? "[Quick Msg] ON" : "[Quick Msg] OFF");
      display.setCursor(0, 40);
      display.print(confirm_choice == 1 ? "> SEND" : "  SEND");
      display.setCursor(0, 52);
      display.print(confirm_choice == 2 ? "> CANCEL" : "  CANCEL");
''', 'confirmation menu')

    s = replace_once(s,
        '''    if (c == KEY_PREV || c == KEY_LEFT) {
      // Double click backs out; it never sends.
      if (mode == CONFIRM) mode = PRESETS;
      else if (mode == PRESETS) mode = reply_mode ? INBOX : CHANNELS;
      else task->gotoHomeScreen();
      return true;
    }
''',
        '''    if (c == KEY_PREV) {
      // nRF52840 button driver classifies rapid single taps as a double-click.
      // Treat these as one NEXT, never as an accidental BACK/EXIT.
      c = KEY_NEXT;
    }
    if (c == KEY_LEFT) {
      // Optional non-FakeTec navigation hardware can still move to next.
      c = KEY_NEXT;
    }
''', 'double-click failsafe')

    s = replace_once(s,
        '''      if (mode == INBOX && count) age = (age + 1) % count;
      else if (mode == CHANNELS) channel_idx = nextChannel(channel_idx);
      else if (mode == PRESETS) preset = (preset + 1) % PRESET_COUNT;
      return true;
''',
        '''      if (mode == INBOX) {
        age = (age + 1) % (count + 1);  // final item is BACK
      } else if (mode == CHANNELS) {
        if (channel_back_selected) {
          channel_idx = nextChannel(-1);
          channel_back_selected = channel_idx < 0;
        } else {
          int next = nextChannel(channel_idx);
          if (next < 0 || next <= channel_idx) channel_back_selected = true;
          else channel_idx = next;
        }
      } else if (mode == PRESETS) {
        preset = (preset + 1) % (PRESET_COUNT + 1);  // last is BACK
      } else if (mode == CONFIRM) {
        confirm_choice = (confirm_choice + 1) % 3;
      }
      return true;
''', 'short press semantics')

    s = replace_once(s,
        '''      if (mode == INBOX) {
        if (count == 0) return true;
        if (!replyAvailable()) {
          task->showAlert("Recipient unavailable", 1500);
          return true;
        }
        reply_mode = true;
        preset = 0;
        mode = PRESETS;
      } else if (mode == CHANNELS) {
        if (channel_idx < 0) return true;
        ChannelDetails ch;
        if (!the_mesh.getChannel(channel_idx, ch) || !ch.name[0]) return true;
        memcpy(selected_channel_secret, ch.channel.secret, 16);
        reply_mode = false;
        preset = 0;
        mode = PRESETS;
      } else if (mode == PRESETS) {
        mode = CONFIRM;
      } else if (mode == CONFIRM) {
        sendSelected();
      }
''',
        '''      if (mode == INBOX) {
        if (count == 0 || age == count) {
          task->gotoHomeScreen();
        } else if (!replyAvailable()) {
          task->showAlert("Recipient unavailable", 1500);
        } else {
          reply_mode = true;
          preset = 0;
          mode = PRESETS;
        }
      } else if (mode == CHANNELS) {
        if (channel_back_selected || channel_idx < 0) {
          task->gotoHomeScreen();
        } else {
          ChannelDetails ch;
          if (!the_mesh.getChannel(channel_idx, ch) || !ch.name[0]) return true;
          memcpy(selected_channel_secret, ch.channel.secret, 16);
          reply_mode = false;
          preset = 0;
          mode = PRESETS;
        }
      } else if (mode == PRESETS) {
        if (preset == PRESET_COUNT) mode = reply_mode ? INBOX : CHANNELS;
        else {
          confirm_choice = 0;
          mode = CONFIRM;
        }
      } else if (mode == CONFIRM) {
        if (confirm_choice == 0) append_marker = !append_marker;
        else if (confirm_choice == 1) sendSelected();
        else mode = PRESETS;  // deliberate CANCEL; no transmit
      }
''', 'long press semantics')

    if s.count(MARKER) != 1:
        raise ValueError('v0.4 marker must appear exactly once')
    return s


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path,
                        default=Path.home() / 'faketec-ui' / 'MeshCore')
    parser.add_argument('--check', action='store_true', help='validate patch without writing')
    args = parser.parse_args()
    cpp = args.source_root / 'examples/companion_radio/ui-new/UITask.cpp'
    try:
        old = cpp.read_text(encoding='utf-8')
        new = patch_source(old)
    except (ValueError, OSError) as exc:
        sys.exit('ERROR: no changes made: %s' % exc)
    if old == new:
        print('FakeTec UI v0.4 safe buttons already applied.')
        return
    if args.check:
        print('Dry-run OK: v0.4 can be applied to ' + str(cpp))
        return
    backup = cpp.with_suffix('.cpp.v04-backup')
    if not backup.exists():
        shutil.copy2(cpp, backup)
    fd, tmp = tempfile.mkstemp(prefix='.UITask.v04.', suffix='.cpp', dir=str(cpp.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            f.write(new)
        os.replace(tmp, cpp)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    print('Patched: ' + str(cpp))
    print('One-time source backup: ' + str(backup))
    print('NEXT: build and verify the FakeTec ProMicro BLE firmware target.')


if __name__ == '__main__':
    main()
