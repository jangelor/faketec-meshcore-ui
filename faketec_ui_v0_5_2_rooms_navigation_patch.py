#!/usr/bin/env python3
"""FakeTec v0.5.2: room destinations and intuitive reverse navigation.

Apply after v0.5.1 ACK/voltage patch. Sends posts to the user's saved
room contact using the existing encrypted DM transmission path. Login and
room permission remain managed by a connected phone app. No secrets stored.
"""
import argparse
import os
import shutil
import tempfile
from pathlib import Path

MARKER = 'FAKETEC_UI_V052_ROOMS_NAV'


def once(src, old, new, name):
    n = src.count(old)
    if n != 1:
        raise ValueError('%s: expected one source anchor, found %d' % (name, n))
    return src.replace(old, new, 1)


def patch_cpp(src):
    if MARKER in src:
        return src
    if 'FAKETEC_UI_V051_ACK_VOLTAGE' not in src or 'FAKETEC_UI_V051_UX' not in src:
        raise ValueError('Requires FakeTec v0.5.1 including ACK/voltage patch')

    src = once(src,
        '''  uint8_t next_ack_slot = 0;

  void renderVoltage''',
        '''  uint8_t next_ack_slot = 0;
  // FAKETEC_UI_V052_ROOMS_NAV: remember whether an ACK is for a room post.
  uint8_t pending_ack_is_room[4] = {0, 0, 0, 0};
  int target_pos = 0;              // explicit list: channels, rooms, Back
  bool sending_to_room = false;
  uint8_t selected_room_pubkey[PUB_KEY_SIZE] = {0};

  void renderVoltage''', 'new room and ACK state')

    src = once(src,
        '''  bool replyAvailable() {
''',
        '''  // Known room contacts are selectable. The companion does not know
  // whether a phone-app login is currently valid; the room will ACK a post
  // only if it has accepted the submission.
  int channelCount() const {
    int count = 0;
    for (int i = 0; i < MAX_GROUP_CHANNELS; ++i) {
      ChannelDetails ch;
      if (the_mesh.getChannel(i, ch) && ch.name[0]) ++count;
    }
    return count;
  }

  bool channelAt(int ordinal, int& index, ChannelDetails& out) const {
    for (int i = 0; i < MAX_GROUP_CHANNELS; ++i) {
      ChannelDetails ch;
      if (the_mesh.getChannel(i, ch) && ch.name[0]) {
        if (ordinal-- == 0) {
          index = i;
          out = ch;
          return true;
        }
      }
    }
    return false;
  }

  int roomCount() const {
    int count = 0;
    ContactInfo contact;
    for (int i = 0; i < the_mesh.getTotalContactSlots(); ++i) {
      if (the_mesh.getContactByIdx(i, contact) &&
          contact.type == ADV_TYPE_ROOM && contact.name[0]) ++count;
    }
    return count;
  }

  bool roomAt(int ordinal, ContactInfo& out) const {
    ContactInfo contact;
    for (int i = 0; i < the_mesh.getTotalContactSlots(); ++i) {
      if (the_mesh.getContactByIdx(i, contact) &&
          contact.type == ADV_TYPE_ROOM && contact.name[0]) {
        if (ordinal-- == 0) {
          out = contact;
          return true;
        }
      }
    }
    return false;
  }

  int targetCount() const { return channelCount() + roomCount(); }

  bool replyAvailable() {
''', 'enumerate saved room contacts and channels')

    src = once(src,
        '''    bool queued = false;
    uint32_t direct_expected_ack = 0;
''',
        '''    bool queued = false;
    uint32_t direct_expected_ack = 0;
    bool direct_is_room = false;
''', 'store ACK destination kind')

    src = once(src,
        '''            if (queued) direct_expected_ack = expected_ack;
''',
        '''            if (queued) {
              direct_expected_ack = expected_ack;
              direct_is_room = (recipient->type == ADV_TYPE_ROOM);
            }
''', 'recognize reply to room')

    src = once(src,
        '''    } else if (channel_idx >= 0) {
      ChannelDetails ch;
      if (the_mesh.getChannel(channel_idx, ch) && ch.name[0] &&
''',
        '''    } else if (sending_to_room) {
      ContactInfo* room = the_mesh.lookupContactByPubKey(selected_room_pubkey, PUB_KEY_SIZE);
      if (room && room->type == ADV_TYPE_ROOM &&
          memcmp(room->id.pub_key, selected_room_pubkey, PUB_KEY_SIZE) == 0) {
        uint32_t expected_ack = 0, timeout = 0;
        queued = the_mesh.sendMessage(*room, timestamp, 0, message,
                                       expected_ack, timeout) != MSG_SEND_FAILED;
        if (queued) {
          direct_expected_ack = expected_ack;
          direct_is_room = true;
        }
      }
    } else if (channel_idx >= 0) {
      ChannelDetails ch;
      if (the_mesh.getChannel(channel_idx, ch) && ch.name[0] &&
''', 'send encrypted room post only to exact saved key')

    src = once(src,
        '''      pending_dm_ack[next_ack_slot] = direct_expected_ack;
      pending_dm_at_ms[next_ack_slot] = millis();
      next_ack_slot = (next_ack_slot + 1) % 4;
    }
    task->showAlert(!queued ? "Send failed" :
                    direct_expected_ack ? "DM: awaiting ACK" :
                    "Queued (not delivered)", 1800);
''',
        '''      pending_dm_ack[next_ack_slot] = direct_expected_ack;
      pending_dm_at_ms[next_ack_slot] = millis();
      pending_ack_is_room[next_ack_slot] = direct_is_room ? 1 : 0;
      next_ack_slot = (next_ack_slot + 1) % 4;
    }
    task->showAlert(!queued ? "Send failed" :
                    direct_expected_ack ? (direct_is_room ? "Room: await ACK" :
                                           "DM: awaiting ACK") :
                    "Queued (not delivered)", 1800);
''', 'room pending alert, not delivery claim')

    src = once(src,
        '''        pending_dm_ack[i] = 0; // prevents duplicate ACK popups
        task->showAlert("DM ACK received", 2200);
''',
        '''        pending_dm_ack[i] = 0; // prevents duplicate ACK popups
        task->showAlert(pending_ack_is_room[i] ? "Room post ACK" :
                        "DM ACK received", 2200);
''', 'distinguish room ACK')

    src = once(src,
        '''    channel_idx = nextChannel(-1);
    channel_back_selected = channel_idx < 0;
    preset = 0;
    confirm_choice = 0;
''',
        '''    channel_idx = -1;
    target_pos = 0;
    sending_to_room = false;
    memset(selected_room_pubkey, 0, sizeof(selected_room_pubkey));
    preset = 0;
    confirm_choice = 0;
''', 'open unified destination picker')

    src = once(src,
        '''    } else if (mode == CHANNELS) {
      display.setCursor(0, 0);
      display.print("CHOOSE CHANNEL");
      if (channel_back_selected || channel_idx < 0) {
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
''',
        '''    } else if (mode == CHANNELS) {
      display.setCursor(0, 0);
      display.print("DESTINATION");
      const int channels = channelCount();
      const int targets = channels + roomCount();
      if (target_pos >= targets) {
        display.drawTextCentered(display.width()/2, 26,
                                 targets == 0 ? "No channels/rooms" : "< BACK >");
        display.setCursor(0, 53);
        display.print("Hold: Back");
      } else if (target_pos < channels) {
        int actual_idx = -1;
        ChannelDetails ch;
        if (channelAt(target_pos, actual_idx, ch)) {
          display.setCursor(0, 17);
          display.print("CHANNEL:");
          display.setCursor(0, 29);
          display.drawTextEllipsized(0, 29, display.width(), ch.name);
        }
        display.setCursor(0, 53);
        display.print("1:> 2:< Hold:OK");
      } else {
        ContactInfo room;
        if (roomAt(target_pos - channels, room)) {
          display.setCursor(0, 17);
          display.print("ROOM (login in app):");
          display.drawTextEllipsized(0, 29, display.width(), room.name);
        }
        display.setCursor(0, 53);
        display.print("1:> 2:< Hold:OK");
      }
''', 'render channel or room in one list')

    src = once(src,
        '''      if (preset == PRESET_COUNT) {
        display.drawTextCentered(display.width()/2, 27, "< BACK >");
        display.setCursor(0, 54);
        display.print("Hold: Back");
      } else {
        display.printWordWrap(presetText(preset), display.width());
        display.setCursor(0, 54);
        display.print("Hold: Select");
      }
''',
        '''      if (preset == PRESET_COUNT) {
        display.drawTextCentered(display.width()/2, 27, "< BACK >");
        display.setCursor(0, 54);
        display.print("1:> 2:< Hold:Back");
      } else {
        display.printWordWrap(presetText(preset), display.width());
        display.setCursor(0, 54);
        display.print("1:> 2:< Hold:OK");
      }
''', 'preset forward and reverse navigation hints')

    src = once(src,
        '''      } else if (channel_idx >= 0) {
        ChannelDetails ch;
        if (the_mesh.getChannel(channel_idx, ch))
          snprintf(destination, sizeof(destination), "%.18s", ch.name);
      }
''',
        '''      } else if (sending_to_room) {
        ContactInfo* room = the_mesh.lookupContactByPubKey(selected_room_pubkey, PUB_KEY_SIZE);
        if (room && room->type == ADV_TYPE_ROOM)
          snprintf(destination, sizeof(destination), "R:%.16s", room->name);
      } else if (channel_idx >= 0) {
        ChannelDetails ch;
        if (the_mesh.getChannel(channel_idx, ch))
          snprintf(destination, sizeof(destination), "C:%.16s", ch.name);
      }
''', 'show room destination before send')

    src = once(src,
        '''    if (c == KEY_PREV) {
      // nRF52840 button driver classifies rapid single taps as a double-click.
      // Treat these as one NEXT, never as an accidental BACK/EXIT.
      c = KEY_NEXT;
    }
    if (c == KEY_LEFT) {
      // Optional non-FakeTec navigation hardware can still move to next.
      c = KEY_NEXT;
    }
''',
        '''    if (c == KEY_LEFT) c = KEY_PREV;
    if (c == KEY_PREV) {
      // A double-click moves PREVIOUS; never exits or transmits.
      if (mode == INBOX) age = (age + count) % (count + 1);
      else if (mode == CHANNELS) {
        const int choices = targetCount() + 1; // includes explicit BACK row
        target_pos = (target_pos + choices - 1) % choices;
      } else if (mode == PRESETS) {
        preset = (preset + PRESET_COUNT) % (PRESET_COUNT + 1);
      } else if (mode == CONFIRM) {
        confirm_choice = (confirm_choice + 2) % 3;
      }
      return true;
    }
''', 'double-click is previous selection')

    src = once(src,
        '''      } else if (mode == CHANNELS) {
        if (channel_back_selected) {
          channel_idx = nextChannel(-1);
          channel_back_selected = channel_idx < 0;
        } else {
          int next = nextChannel(channel_idx);
          if (next < 0 || next <= channel_idx) channel_back_selected = true;
          else channel_idx = next;
        }
''',
        '''      } else if (mode == CHANNELS) {
        target_pos = (target_pos + 1) % (targetCount() + 1);
''', 'single-click next destination')

    src = once(src,
        '''      } else if (mode == CHANNELS) {
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
''',
        '''      } else if (mode == CHANNELS) {
        const int channels = channelCount();
        const int targets = channels + roomCount();
        if (target_pos >= targets) {
          task->gotoHomeScreen();
        } else if (target_pos < channels) {
          ChannelDetails ch;
          int actual_idx = -1;
          if (!channelAt(target_pos, actual_idx, ch)) return true;
          channel_idx = actual_idx;
          memcpy(selected_channel_secret, ch.channel.secret, 16);
          sending_to_room = false;
          reply_mode = false;
          preset = 0;
          mode = PRESETS;
        } else {
          ContactInfo room;
          if (!roomAt(target_pos - channels, room)) return true;
          memcpy(selected_room_pubkey, room.id.pub_key, PUB_KEY_SIZE);
          channel_idx = -1;
          sending_to_room = true;
          reply_mode = false;
          preset = 0;
          mode = PRESETS;
        }
''', 'hold selects exact channel or saved room')

    if src.count(MARKER) != 1:
        raise ValueError('v0.5.2 marker invariant failed')
    return src


def atomic_write(path, value):
    fd, tmp = tempfile.mkstemp(prefix='.UITask.v052.', suffix='.cpp', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            f.write(value)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root', type=Path, default=Path.home() / 'faketec-ui' / 'MeshCore')
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    cpp = args.source_root / 'examples/companion_radio/ui-new/UITask.cpp'
    try:
        old = cpp.read_text(encoding='utf-8')
        new = patch_cpp(old)
    except (OSError, ValueError) as e:
        p.error('no source changed: ' + str(e))
    if args.check:
        print('Dry-run OK: room targets and reverse Quick Msg navigation')
        return
    if new == old:
        print('FakeTec v0.5.2 rooms/navigation already installed.')
        return
    backup = cpp.with_name(cpp.name + '.v051-before-rooms-nav')
    if not backup.exists():
        shutil.copy2(cpp, backup)
    atomic_write(cpp, new)
    print('Applied FakeTec v0.5.2 rooms/navigation. No radio flashed.')


if __name__ == '__main__':
    main()
