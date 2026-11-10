#!/usr/bin/env python3
"""Add a minimal Recent Adverts action menu to MeshCore 1.18 ui-new.

Designed for MeshCore commit 81dbae592ffad40b4212bc0b37e82b38da08f4bc.
No flashing or radio transmission is performed by this script.
"""
from pathlib import Path
import shutil
import sys

root = Path.home() / 'faketec-ui' / 'MeshCore'
source = root / 'examples/companion_radio/ui-new/UITask.cpp'

if not source.is_file():
    sys.exit('ERROR: Missing '+str(source))

s = source.read_text()
if 'FAKETEC_UI_V01_MENU' in s:
    sys.exit('Already patched. No changes made.')

patches = [
    (
        '  AdvertPath recent[UI_RECENT_LIST_SIZE];\n',
        '  AdvertPath recent[UI_RECENT_LIST_SIZE];\n'
        '  // FAKETEC_UI_V01_MENU: one-button contextual actions.\n'
        '  bool recent_menu_open = false;\n'
        '  uint8_t recent_menu_selection = 0;\n',
    ),
    (
        '    if (_page == HomePage::FIRST) {\n',
        '''    // Navigation only. No radio packet is sent merely by opening this menu.
    if (recent_menu_open) {
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

    if (_page == HomePage::FIRST) {
''',
    ),
    (
        '  bool handleInput(char c) override {\n'
        '    if (c == KEY_LEFT || c == KEY_PREV) {\n',
        '''  bool handleInput(char c) override {
    if (recent_menu_open) {
      if (c == KEY_NEXT || c == KEY_RIGHT) {
        recent_menu_selection = (recent_menu_selection + 1) % 3;
        return true;
      }
      if (c == KEY_PREV || c == KEY_LEFT) {
        recent_menu_open = false;
        return true;
      }
      if (c == KEY_ENTER) {
        recent_menu_open = false;
        if (recent_menu_selection == 0) {
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
        return true;
      }
      return true;
    }
    if (c == KEY_ENTER && _page == HomePage::RECENT) {
      recent_menu_open = true;
      recent_menu_selection = 0;
      return true;
    }
    if (c == KEY_LEFT || c == KEY_PREV) {
''',
    ),
]

for old, new in patches:
    count = s.count(old)
    if count != 1:
        sys.exit('ERROR: expected exactly one source anchor, found %d: %r' % (count, old[:90]))
    s = s.replace(old, new, 1)

backup = source.with_suffix('.cpp.v01-backup')
if backup.exists():
    sys.exit('ERROR: Backup already exists: ' + str(backup))
shutil.copy2(source, backup)
source.write_text(s)
print('Patched:', source)
print('Original backup:', backup)
print('Next: python -m platformio run -e ProMicro_companion_radio_ble')
