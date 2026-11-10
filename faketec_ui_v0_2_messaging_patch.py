#!/usr/bin/env python3
"""FakeTec UI v0.2 messaging add-on for MeshCore 1.18 + tested v0.1 menu.

Target: MeshCore commit 81dbae592ffad40b4212bc0b37e82b38da08f4bc,
with the v0.1 patch previously applied. Never flashes devices.

Changes: 12-message RAM inbox, explicit channel picker, canned messages,
contextual direct/channel replies, and second-hold send confirmation.
"""
from pathlib import Path
import sys
import shutil

root = Path.home() / 'faketec-ui' / 'MeshCore'
cpp = root / 'examples/companion_radio/ui-new/UITask.cpp'
hdr = root / 'examples/companion_radio/ui-new/UITask.h'
marker = 'FAKETEC_UI_V02_MESSAGING'
if not cpp.is_file() or not hdr.is_file():
    sys.exit('ERROR: MeshCore source not found at '+str(root))
s = cpp.read_text()
h = hdr.read_text()
if marker in s or marker in h:
    sys.exit('Already applied. No files changed.')
if 'FAKETEC_UI_V01_MENU' not in s:
    sys.exit('ERROR: v0.1 menu missing. Apply v0.1 first.')
if (root / '.git').exists():
    import subprocess
    branch = subprocess.run(['git','branch','--show-current'], cwd=root,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            universal_newlines=True)
    if branch.returncode or branch.stdout.strip() != 'feature/faketec-ui-v0.1':
        sys.exit('ERROR: expected branch feature/faketec-ui-v0.1. Current branch: '+branch.stdout.strip())


def rep(source, old, new, description):
    count = source.count(old)
    if count != 1:
        raise RuntimeError('Anchor mismatch (' + description + '): expected 1, found ' + str(count))
    return source.replace(old, new, 1)

try:
    h = rep(h, '  UIScreen* msg_preview;\n',
        '  UIScreen* msg_preview;\n  UIScreen* quick_messages;  // FAKETEC_UI_V02_MESSAGING\n', 'header pointer')
    h = rep(h, '  void gotoHomeScreen() { setCurrScreen(home); }\n',
        '  void gotoHomeScreen() { setCurrScreen(home); }\n'
        '  void openInbox();\n'
        '  void openCanned();\n', 'header public methods')

    s = rep(s,
'''    if (recent_menu_open) {
      const char* items[] = {"Find repeaters", "Advertise", "Back"};
      display.setTextSize(1);
      display.setColor(UIColor::primary_txt);
      display.drawTextCentered(display.width() / 2, 19, "RECENT OPTIONS");
      for (uint8_t i = 0; i < 3; ++i) {
        display.setCursor(4, 30 + 11 * i);
        display.print(i == recent_menu_selection ? "> " : "  ");
        display.print(items[i]);
      }
      return 1000;
    }
''',
'''    if (recent_menu_open) {
      // FAKETEC_UI_V02_MESSAGING: three visible lines, scroll through five actions.
      const char* items[] = {"Inbox", "Canned msgs", "Find repeaters", "Advertise", "Back"};
      display.setTextSize(1);
      display.setColor(UIColor::primary_txt);
      display.drawTextCentered(display.width() / 2, 19, "QUICK ACTIONS");
      uint8_t first = recent_menu_selection < 3 ? 0 : 2;
      for (uint8_t i = 0; i < 3; ++i) {
        uint8_t entry = first + i;
        display.setCursor(4, 30 + 11 * i);
        display.print(entry == recent_menu_selection ? "> " : "  ");
        display.print(items[entry]);
      }
      return 1000;
    }
''', 'v0.1 menu render')

    s = rep(s,'recent_menu_selection = (recent_menu_selection + 1) % 3;',
              'recent_menu_selection = (recent_menu_selection + 1) % 5;', 'menu cycling')

    s = rep(s,
'''        if (recent_menu_selection == 0) {
#if UI_DISCOVER_SCREEN
          _page = HomePage::DISCOVERY;
          _task->showAlert("Hold to scan", 1200);
#else
          _task->showAlert("Scan unavailable", 1200);
#endif
        } else if (recent_menu_selection == 1) {
          _page = HomePage::ADVERT;
          _task->showAlert("Hold to advertise", 1200);
        }
''',
'''        if (recent_menu_selection == 0) {
          _task->openInbox();
        } else if (recent_menu_selection == 1) {
          _task->openCanned();
        } else if (recent_menu_selection == 2) {
#if UI_DISCOVER_SCREEN
          _page = HomePage::DISCOVERY;
          _task->showAlert("Hold to scan", 1200);
#else
          _task->showAlert("Scan unavailable", 1200);
#endif
        } else if (recent_menu_selection == 3) {
          _page = HomePage::ADVERT;
          _task->showAlert("Hold to advertise", 1200);
        }
''', 'v0.1 menu actions')

    s = rep(s,'    if (c == KEY_ENTER && _page == HomePage::RECENT) {\n',
        '    if (c == KEY_ENTER && (_page == HomePage::RECENT || _page == HomePage::FIRST)) {\n',
        'open menu from Home as well')

    s = rep(s,'void UITask::begin(DisplayDriver* display, SensorManager* sensors, NodePrefs* node_prefs) {',
'''// FAKETEC_UI_V02_MESSAGING: lightweight, volatile inbox and deliberate message sending.
// No keys or messages written to flash. Stock BLE protocol remains unchanged.
class QuickMessagesScreen : public UIScreen {
  enum Mode { INBOX, CHANNELS, PRESETS, CONFIRM };
  enum { HISTORY = 12, PRESET_COUNT = 10 };
  struct Entry {
    char from[32];
    char text[96];
    uint8_t pubkey[PUB_KEY_SIZE];
    uint8_t channel_secret[16];
    int8_t channel_idx;
    bool is_channel;
  };

  UITask* task;
  Entry items[HISTORY];
  uint8_t count = 0;
  uint8_t head = HISTORY - 1;
  uint8_t age = 0;                // 0 = newest message
  uint8_t preset = 0;
  int channel_idx = -1;
  uint8_t selected_channel_secret[16] = {0};
  bool reply_mode = false;
  Mode mode = INBOX;

  static const char* presetText(uint8_t i) {
    // Edit these strings to customize all four family devices.
    static const char* const presets[PRESET_COUNT] = {
      "OK", "Yes", "No", "Will reply in app later",
      "I'm safe", "Need assistance", "On my way",
      "Where are you?", "Please repeat",
      "CQ CQ CQ - anyone copying?"
    };
    return presets[i % PRESET_COUNT];
  }

  Entry* selected() {
    if (count == 0) return NULL;
    return &items[(head + HISTORY - age) % HISTORY];
  }

  int nextChannel(int after) const {
    // Only configured channels are eligible. User must choose one explicitly.
    for (int n = 1; n <= MAX_GROUP_CHANNELS; ++n) {
      int index = (after + n) % MAX_GROUP_CHANNELS;
      ChannelDetails ch;
      if (the_mesh.getChannel(index, ch) && ch.name[0]) return index;
    }
    return -1;
  }

  bool replyAvailable() {
    Entry* e = selected();
    if (!e) return false;
    if (e->is_channel) {
      ChannelDetails current;
      return e->channel_idx >= 0 &&
             the_mesh.getChannel(e->channel_idx, current) && current.name[0] &&
             memcmp(e->channel_secret, current.channel.secret, 16) == 0;
    }
    return the_mesh.lookupContactByPubKey(e->pubkey, PUB_KEY_SIZE) != NULL;
  }

  void sendSelected() {
    const char* message = presetText(preset);
    uint32_t timestamp = the_mesh.getRTCClock()->getCurrentTimeUnique();
    bool queued = false;
    if (reply_mode) {
      Entry* e = selected();
      if (e && replyAvailable()) {
        if (e->is_channel) {
          ChannelDetails ch;
          if (the_mesh.getChannel(e->channel_idx, ch)) {
            queued = the_mesh.sendGroupMessage(timestamp, ch.channel,
                    the_mesh.getNodeName(), message, strlen(message));
          }
        } else {
          ContactInfo* recipient = the_mesh.lookupContactByPubKey(e->pubkey, PUB_KEY_SIZE);
          if (recipient) {
            uint32_t expected_ack = 0, timeout = 0;
            queued = the_mesh.sendMessage(*recipient, timestamp, 0, message,
                                            expected_ack, timeout) != MSG_SEND_FAILED;
          }
        }
      }
    } else if (channel_idx >= 0) {
      ChannelDetails ch;
      if (the_mesh.getChannel(channel_idx, ch) && ch.name[0] &&
          memcmp(selected_channel_secret, ch.channel.secret, 16) == 0) {
        queued = the_mesh.sendGroupMessage(timestamp, ch.channel,
                    the_mesh.getNodeName(), message, strlen(message));
      }
    }
    task->showAlert(queued ? "Queued (not delivered)" : "Send failed", 1800);
    // End confirmation workflow even on failure: repeat requires deliberate re-selection.
    task->gotoHomeScreen();
    mode = INBOX;
  }

public:
  explicit QuickMessagesScreen(UITask* owner) : task(owner) { }

  void addDirect(const ContactInfo& from, const char* text) {
    head = (head + 1) % HISTORY;
    if (count < HISTORY) ++count;
    Entry& e = items[head];
    StrHelper::strncpy(e.from, from.name, sizeof(e.from));
    StrHelper::strncpy(e.text, text, sizeof(e.text));
    memcpy(e.pubkey, from.id.pub_key, PUB_KEY_SIZE);
    memset(e.channel_secret, 0, sizeof(e.channel_secret));
    e.channel_idx = -1;
    e.is_channel = false;
  }

  void addChannel(const ChannelDetails& from, const char* text) {
    head = (head + 1) % HISTORY;
    if (count < HISTORY) ++count;
    Entry& e = items[head];
    StrHelper::strncpy(e.from, from.name, sizeof(e.from));
    StrHelper::strncpy(e.text, text, sizeof(e.text));
    memcpy(e.channel_secret, from.channel.secret, sizeof(e.channel_secret));
    memset(e.pubkey, 0, sizeof(e.pubkey));
    e.channel_idx = the_mesh.findChannelIdx(from.channel);
    e.is_channel = true;
  }

  void openInbox() {
    mode = INBOX;
    age = 0;
    reply_mode = true;
  }

  void openCanned() {
    // Display the channel picker before allowing selection of any text.
    mode = CHANNELS;
    reply_mode = false;
    channel_idx = nextChannel(-1);
    preset = 0;
  }

  int render(DisplayDriver& display) override {
    display.setTextSize(1);
    display.setColor(UIColor::primary_txt);
    if (mode == INBOX) {
      display.setCursor(0, 1);
      display.print("INBOX");
      if (count == 0) {
        display.drawTextCentered(display.width()/2, 27, "No messages yet");
        display.drawTextCentered(display.width()/2, 50, "2 clicks: Back");
        return 1000;
      }
      Entry* e = selected();
      char label[22];
      snprintf(label, sizeof(label), "%u/%u %s", (unsigned)(age+1),
               (unsigned)count, e->is_channel ? "CH" : "DM");
      display.setCursor(display.width() - display.getTextWidth(label), 1);
      display.print(label);
      display.setCursor(0, 13);
      display.print(e->from);
      // Keep text within the three lines above the fixed bottom hint.
      // Long messages remain in the RAM entry but need phone app for full reading.
      char snippet[55];
      StrHelper::strncpy(snippet, e->text, sizeof(snippet));
      if (strlen(e->text) >= sizeof(snippet)) {
        snippet[50] = '.';
        snippet[51] = '.';
        snippet[52] = '.';
        snippet[53] = 0;
      }
      display.setCursor(0, 25);
      display.printWordWrap(snippet, display.width());
      display.setCursor(0, 55);
      display.print("Hold: Reply");
    } else if (mode == CHANNELS) {
      display.setCursor(0, 0);
      display.print("CHOOSE CHANNEL");
      if (channel_idx < 0) {
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
    } else if (mode == PRESETS) {
      display.setCursor(0, 0);
      display.print(reply_mode ? "QUICK REPLY" : "CANNED MESSAGE");
      char label[20];
      snprintf(label, sizeof(label), "%u/%u", (unsigned)(preset+1),
               (unsigned)PRESET_COUNT);
      display.setCursor(display.width() - display.getTextWidth(label), 0);
      display.print(label);
      display.setCursor(0, 17);
      display.printWordWrap(presetText(preset), display.width());
      display.setCursor(0, 54);
      display.print("Hold: Confirm");
    } else {  // CONFIRM
      display.setCursor(0, 0);
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
    }
    return 1000;
  }

  bool handleInput(char c) override {
    if (c == KEY_PREV || c == KEY_LEFT) {
      // Double click backs out; it never sends.
      if (mode == CONFIRM) mode = PRESETS;
      else if (mode == PRESETS) mode = reply_mode ? INBOX : CHANNELS;
      else task->gotoHomeScreen();
      return true;
    }
    if (c == KEY_NEXT || c == KEY_RIGHT) {
      if (mode == INBOX && count) age = (age + 1) % count;
      else if (mode == CHANNELS) channel_idx = nextChannel(channel_idx);
      else if (mode == PRESETS) preset = (preset + 1) % PRESET_COUNT;
      return true;
    }
    if (c == KEY_ENTER) {
      if (mode == INBOX) {
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
      return true;
    }
    return false;
  }
};

void UITask::openInbox() {
  ((QuickMessagesScreen*) quick_messages)->openInbox();
  setCurrScreen(quick_messages);
}

void UITask::openCanned() {
  ((QuickMessagesScreen*) quick_messages)->openCanned();
  setCurrScreen(quick_messages);
}

void UITask::begin(DisplayDriver* display, SensorManager* sensors, NodePrefs* node_prefs) {''',
    'insert messaging screen')

    s = rep(s,'  msg_preview = new MsgPreviewScreen(this, &rtc_clock);\n',
        '  msg_preview = new MsgPreviewScreen(this, &rtc_clock);\n'
        '  quick_messages = new QuickMessagesScreen(this);\n', 'initialize message screen')
    s = rep(s,'  ((MsgPreviewScreen *) msg_preview)->addPreview(path_len, from.name, text);\n',
        '  ((MsgPreviewScreen *) msg_preview)->addPreview(path_len, from.name, text);\n'
        '  ((QuickMessagesScreen *) quick_messages)->addDirect(from, text);\n', 'save direct message')
    s = rep(s,'  ((MsgPreviewScreen *) msg_preview)->addPreview(path_len, channel_details.name, text);\n',
        '  ((MsgPreviewScreen *) msg_preview)->addPreview(path_len, channel_details.name, text);\n'
        '  ((QuickMessagesScreen *) quick_messages)->addChannel(channel_details, text);\n', 'save channel message')
except RuntimeError as ex:
    sys.exit('ERROR: no files changed: ' + str(ex))

backup_cpp = cpp.with_suffix('.cpp.v02-backup')
backup_hdr = hdr.with_suffix('.h.v02-backup')
if backup_cpp.exists() or backup_hdr.exists():
    sys.exit('ERROR: existing v0.2 backup found; no files changed')
shutil.copy2(cpp, backup_cpp)
shutil.copy2(hdr, backup_hdr)
try:
    cpp.write_text(s)
    hdr.write_text(h)
except Exception:
    shutil.copy2(backup_cpp, cpp)
    shutil.copy2(backup_hdr, hdr)
    raise
print('Applied FakeTec UI v0.2 messaging patch.')
print('Modified:', cpp)
print('Modified:', hdr)
print('Backups:', backup_cpp.name, backup_hdr.name)
print('Next: git diff --check && python -m platformio run -e ProMicro_companion_radio_ble')
