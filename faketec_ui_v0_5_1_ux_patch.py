#!/usr/bin/env python3
"""FakeTec UI v0.5.1: quicker confirmation, repeatable Link Check, clear dashboard.

Applies ONLY after the pinned v0.5 dashboard patch. No RF transmissions or
flashing are performed by this script. Builds must be tested on hardware.
"""
import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

MARKER = 'FAKETEC_UI_V051_UX'


def once(source, old, new, description):
    count = source.count(old)
    if count != 1:
        raise ValueError('%s: expected 1 exact anchor, got %d' % (description, count))
    return source.replace(old, new, 1)


def patch_cpp(source):
    if MARKER in source:
        return source
    if 'FAKETEC_UI_V05_LINK_CHECK' not in source or 'FAKETEC_UI_V04_SAFE_BUTTONS' not in source:
        raise ValueError('Requires existing FakeTec v0.5 after v0.4 safe button patch')
    if 'FAKETEC_UI_V041_STATUS_MENU' not in source:
        raise ValueError('Requires the v0.4.1 status menu')

    # Reorder confirmation menu to SEND, tag toggle, CANCEL. SEND starts
    # selected, and a single short click goes straight to the tag toggle.
    source = once(source,
        '  uint8_t confirm_choice = 0;  // 0=tag toggle, 1=SEND, 2=CANCEL',
        '  // FAKETEC_UI_V051_UX: SEND selected first, tag one click away.\n'
        '  uint8_t confirm_choice = 0;  // 0=SEND, 1=tag toggle, 2=CANCEL',
        'confirmation choice mapping')
    if source.count('\n    confirm_choice = 0;\n') != 2 or source.count('          confirm_choice = 0;\n          mode = CONFIRM;') != 1:
        raise ValueError('Unexpected confirmation choice reset sites')
    source = once(source,
        '''      display.setCursor(0, 28);
      display.print(confirm_choice == 0 ? "> " : "  ");
      display.print(append_marker ? "[Quick Msg] ON" : "[Quick Msg] OFF");
      display.setCursor(0, 40);
      display.print(confirm_choice == 1 ? "> SEND" : "  SEND");
      display.setCursor(0, 52);
      display.print(confirm_choice == 2 ? "> CANCEL" : "  CANCEL");
''',
        '''      display.setCursor(0, 28);
      display.print(confirm_choice == 0 ? "> SEND" : "  SEND");
      display.setCursor(0, 40);
      display.print(confirm_choice == 1 ? "> " : "  ");
      display.print(append_marker ? "[Quick Msg] ON" : "[Quick Msg] OFF");
      display.setCursor(0, 52);
      display.print(confirm_choice == 2 ? "> CANCEL" : "  CANCEL");
''', 'send first confirmation display')
    source = once(source,
        '''        if (confirm_choice == 0) append_marker = !append_marker;
        else if (confirm_choice == 1) sendSelected();
        else mode = PRESETS;  // deliberate CANCEL; no transmit
''',
        '''        if (confirm_choice == 0) sendSelected();
        else if (confirm_choice == 1) append_marker = !append_marker;
        else mode = PRESETS;  // deliberate CANCEL; no transmit
''', 'send first confirmation action mapping')

    # Remove the artificial Link Check cooldown. The radio's own airtime and
    # packet-queue limits still apply; a new explicit hold sends one request.
    source = once(source,
        '''  bool link_check_attempted = false;
  bool link_check_rate_limited = false;
  bool link_check_tx_ok = false;
  uint32_t link_check_attempt_ms = 0;
''',
        '''  bool link_check_tx_ok = false;
''', 'remove cooldown and unused state fields')
    source = once(source,
        '''    uint32_t now = millis();
    if (link_check_attempted && (uint32_t)(now - link_check_attempt_ms) < 60000UL) {
      link_check_rate_limited = true;
      return; // Never retransmit during the one-minute cooldown.
    }
    link_check_rate_limited = false;
    link_check_attempted = true;
    link_check_attempt_ms = now;
''',
        '''    // No artificial cooldown: each deliberate HOLD requests a fresh scan.
''', 'remove 60s cooldown')

    source = once(source,
        '''    if (link_check_open) {
      // A single short click or hold dismisses the on-device result overlay.
      // Neither event resends the discovery request.
      if (c == KEY_ENTER || c == KEY_NEXT || c == KEY_RIGHT ||
          c == KEY_PREV || c == KEY_LEFT) {
        link_check_open = false;
        _page = HomePage::FIRST;
      }
      return true;
    }
''',
        '''    if (link_check_open) {
      // On-device workflow for coverage hunting: HOLD immediately rechecks.
      // A short/double click returns to the dashboard without transmitting.
      if (c == KEY_ENTER) {
        startLinkCheck();
      } else if (c == KEY_NEXT || c == KEY_RIGHT ||
                 c == KEY_PREV || c == KEY_LEFT) {
        link_check_open = false;
        _page = HomePage::FIRST;
      }
      return true;
    }
''', 'overlay input behavior')

    source = once(source,
        '''      if (link_check_rate_limited) {
        uint32_t elapsed = (uint32_t)(millis() - link_check_attempt_ms);
        unsigned secs = (elapsed < 60000UL) ? (unsigned)((60000UL - elapsed + 999UL) / 1000UL) : 0;
        snprintf(tmp, sizeof(tmp), "Cooldown %us", secs);
        display.setCursor(0, 31);
        display.print(tmp);
        display.setCursor(0, 42);
        display.print("Previous scan kept");
      } else if (!link_check_tx_ok) {
''',
        '''      if (!link_check_tx_ok) {
''', 'overlay remove cooldown label')
    source = once(source,
        '      display.print("Click/Hold: Home");',
        '      display.print("Tap:Back Hold:Scan");', 'overlay control hint')

    # Rename ambiguous RPT and LAST; show successful discoveries separately
    # from passive directly-heard advertisements, which are different data.
    # Display dimensions: 128x64, four 11-pixel text rows at 20/31/42/53.
    source = once(source,
        '''      snprintf(tmp, sizeof(tmp), "MSG:%u  RPT:%u", (unsigned)_task->getMsgCount(), repeater_count);
      display.setCursor(0, 20);
      display.print(tmp);
      display.setCursor(0, 31);
      if (latest) {
        snprintf(tmp, sizeof(tmp), "LAST: %.15s", latest->name);
        display.print(tmp);
      } else {
        display.print("LAST: none heard");
      }
      display.setCursor(0, 42);
#if UI_DISCOVER_SCREEN
      const int best_link = bestLinkIndex();
      if (link_check_attempted && link_check_tx_ok && best_link >= 0 &&
          (uint32_t)(millis() - discovery_req_time) < 600000UL) {
        const DiscoveredNode& d = discovered[best_link];
        snprintf(tmp, sizeof(tmp), "LINK:%+.1f/%+.1fdB", d.snr_in, d.snr_out);
        display.print(tmp);
      } else {
        display.print("LINK: check in menu");
      }
#else
      display.print("LINK: unavailable");
#endif
      display.setCursor(0, 53);
      snprintf(tmp, sizeof(tmp), "BLE:%s  BAT:%.2fV",
               _task->hasConnection() ? "ON" : "OFF", (float)_task->getBattMilliVolts() / 1000.0f);
      display.print(tmp);
''',
        '''      snprintf(tmp, sizeof(tmp), "MSG:%u HEARD:%u", (unsigned)_task->getMsgCount(), repeater_count);
      display.setCursor(0, 20);
      display.print(tmp);
      display.setCursor(0, 31);
#if UI_DISCOVER_SCREEN
      // The built-in Find repeaters page and Link Check share a discovery
      // cache. RPT FOUND counts responses to the last discovery on either page.
      const bool checked = discovery_req_time != 0;
      const uint32_t check_age_ms = checked ? (uint32_t)(millis() - discovery_req_time) : 0;
      const bool fresh = checked && check_age_ms < 600000UL;
      const unsigned replies = checked ? respondingRepeaters() : 0;
      const int best_link = fresh ? bestLinkIndex() : -1;
      if (!checked) {
        display.print("RPT FOUND:--");
      } else if (!fresh) {
        snprintf(tmp, sizeof(tmp), "RPT FOUND:%u old", replies);
        display.print(tmp);
      } else {
        snprintf(tmp, sizeof(tmp), "RPT FOUND:%u %lum", replies,
                 (unsigned long)(check_age_ms / 60000UL));
        display.print(tmp);
      }
#else
      display.print("RPT FOUND:N/A");
#endif
      display.setCursor(0, 42);
#if UI_DISCOVER_SCREEN
      if (best_link >= 0) {
        const DiscoveredNode& d = discovered[best_link];
        snprintf(tmp, sizeof(tmp), "BEST: %.14s", d.name[0] ? d.name : "Unnamed");
        display.print(tmp);
      } else
#endif
      if (latest) {
        // Passive advertiser, NOT a confirmed responding repeater.
        snprintf(tmp, sizeof(tmp), "SEEN: %.14s", latest->name);
        display.print(tmp);
      } else {
        display.print("BEST: no recent link");
      }
      display.setCursor(0, 53);
      // Preserve the original pairing-PIN behavior when the phone is absent.
      if (!_task->hasConnection()) {
        const uint32_t pin = the_mesh.getBLEPin();
        if (pin) {
          snprintf(tmp, sizeof(tmp), "PIN:%06lu B:%.2fV", (unsigned long)pin,
                   (float)_task->getBattMilliVolts() / 1000.0f);
        } else {
          snprintf(tmp, sizeof(tmp), "BLE:WAIT B:%.2fV",
                   (float)_task->getBattMilliVolts() / 1000.0f);
        }
      } else {
#if UI_DISCOVER_SCREEN
        if (best_link >= 0) {
          const DiscoveredNode& d = discovered[best_link];
          snprintf(tmp, sizeof(tmp), "I:%+.1f O:%+.1fdB", d.snr_in, d.snr_out);
        } else
#endif
        {
          snprintf(tmp, sizeof(tmp), "BLE:ON B:%.2fV",
                   (float)_task->getBattMilliVolts() / 1000.0f);
        }
      }
      display.print(tmp);
''', 'relabel passive vs discovery counts and restore pin')

    if source.count(MARKER) != 1 or 'link_check_rate_limited' in source:
        raise ValueError('Post-patch invariants failed')
    return source


def atomic_write(path, content):
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '.v051.', dir=str(path.parent))
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
    p.add_argument('--check', action='store_true', help='validate without writing')
    args = p.parse_args()
    cpp = args.source_root / 'examples/companion_radio/ui-new/UITask.cpp'
    try:
        old = cpp.read_text(encoding='utf-8')
        new = patch_cpp(old)
    except (ValueError, OSError) as ex:
        sys.exit('ERROR: no changes made: %s' % ex)
    if old == new:
        print('FakeTec UI v0.5.1 already installed; no changes needed.')
        return
    if args.check:
        print('Dry-run OK. v0.5.1 dashboard, recheck, PIN and SEND-first patch ready.')
        return
    backup = cpp.with_suffix('.cpp.v051-backup')
    if not backup.exists():
        shutil.copy2(cpp, backup)
    atomic_write(cpp, new)
    print('Updated:', cpp)
    print('Previous v0.5 source backed up as:', backup)
    print('No firmware compiled or flashed. Build target: ProMicro_companion_radio_ble')


if __name__ == '__main__':
    main()
