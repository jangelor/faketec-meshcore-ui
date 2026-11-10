#!/usr/bin/env python3
"""FakeTec UI v0.4.1 patch on top of the existing v0.4 source.

- Exposes Quick Actions via long-hold on Home, Recent, AND Radio Status.
- Renames the visible "Canned msgs" menu to "Quick Msgs".
- Renames C++ openCanned methods and the Canned Message screen heading.
- Prevents a double-click from accidentally closing the Quick Actions menu.

Targets MeshCore 1.18 (commit 81dbae592ffad40b4212bc0b37e82b38da08f4bc)
with FakeTec UI patches v0.1, v0.2, v0.3, and v0.4 applied. No flashing.
"""
import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

MARKER = 'FAKETEC_UI_V041_STATUS_MENU'


def once(content, old, new, label):
    matches = content.count(old)
    if matches != 1:
        raise ValueError('%s: expected one anchor, found %d' % (label, matches))
    return content.replace(old, new, 1)


def patch_cpp(src):
    if MARKER in src:
        return src
    if 'FAKETEC_UI_V04_SAFE_BUTTONS' not in src or 'FAKETEC_UI_V02_MESSAGING' not in src:
        raise ValueError('UI v0.4 must be applied first')
    src = once(
        src,
        'const char* items[] = {"Inbox", "Canned msgs", "Find repeaters", "Advertise", "Back"};',
        'const char* items[] = {"Inbox", "Quick Msgs", "Find repeaters", "Advertise", "Back"};',
        'Quick Actions menu text',
    )
    src = once(
        src,
        'display.print(reply_mode ? "QUICK REPLY" : "CANNED MESSAGE");',
        'display.print(reply_mode ? "QUICK REPLY" : "QUICK MSGS");',
        'message picker heading',
    )
    if src.count('openCanned') != 4:
        raise ValueError('openCanned references changed: expected 4, found %d' % src.count('openCanned'))
    src = src.replace('openCanned', 'openQuickMsgs')
    src = once(
        src,
        'if (c == KEY_ENTER && (_page == HomePage::RECENT || _page == HomePage::FIRST)) {',
        '// FAKETEC_UI_V041_STATUS_MENU: expose Quick Actions from Radio Status too.\n'
        '    if (c == KEY_ENTER && (_page == HomePage::RECENT ||\n'
        '                           _page == HomePage::FIRST ||\n'
        '                           _page == HomePage::RADIO)) {',
        'status page shortcut',
    )
    src = once(
        src,
        '''      if (c == KEY_PREV || c == KEY_LEFT) {
        recent_menu_open = false;
        return true;
      }
''',
        '''      if (c == KEY_PREV || c == KEY_LEFT) {
        // Some rapid taps register as a double-click. A safe Next cannot exit.
        // Use the explicit Back row with a hold to exit Quick Actions.
        recent_menu_selection = (recent_menu_selection + 1) % 5;
        return true;
      }
''',
        'Quick Actions double-click handling',
    )
    if src.count(MARKER) != 1:
        raise ValueError('incorrect v0.4.1 marker count')
    return src


def patch_header(src):
    if 'void openQuickMsgs();' in src and 'void openCanned();' not in src:
        return src
    if 'FAKETEC_UI_V02_MESSAGING' not in src:
        raise ValueError('expected FakeTec v0.2 header')
    return once(src, '  void openCanned();', '  void openQuickMsgs();', 'UITask header method')


def atomic_write(path, text):
    fd, tmp = tempfile.mkstemp(prefix='.' + path.name + '.v041.', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root', type=Path, default=Path.home() / 'faketec-ui' / 'MeshCore')
    p.add_argument('--check', action='store_true', help='only check anchors and patch applicability')
    args = p.parse_args()
    cpp = args.source_root / 'examples/companion_radio/ui-new/UITask.cpp'
    header = cpp.with_suffix('.h')
    try:
        csrc, hsrc = cpp.read_text(encoding='utf-8'), header.read_text(encoding='utf-8')
        cp, hp = patch_cpp(csrc), patch_header(hsrc)
        if 'openCanned' in cp or 'openCanned' in hp:
            raise ValueError('one or more old method references remain')
        if ('void openQuickMsgs();' not in hp or 'void UITask::openQuickMsgs()' not in cp):
            raise ValueError('declaration/definition mismatch')
    except (ValueError, OSError) as e:
        sys.exit('ERROR: no changes saved: ' + str(e))
    if cp == csrc and hp == hsrc:
        print('FakeTec v0.4.1 already applied; no changes needed')
        return
    if args.check:
        print('Dry-run OK. Ready to add status access, rename Quick Msgs, and protect menu navigation.')
        return
    # Check both files before modifying either. A backup permits recovery if interrupted.
    for path in (cpp, header):
        backup = path.with_suffix(path.suffix + '.v041-backup')
        if not backup.exists():
            shutil.copy2(path, backup)
    try:
        if cp != csrc:
            atomic_write(cpp, cp)
        if hp != hsrc:
            atomic_write(header, hp)
    except Exception:
        shutil.copy2(cpp.with_suffix(cpp.suffix + '.v041-backup'), cpp)
        shutil.copy2(header.with_suffix(header.suffix + '.v041-backup'), header)
        raise
    print('Updated ' + str(cpp))
    print('Updated ' + str(header))
    print('Build with PlatformIO ProMicro_companion_radio_ble after reviewing git diff.')


if __name__ == '__main__':
    main()
