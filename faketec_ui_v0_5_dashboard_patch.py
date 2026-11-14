#!/usr/bin/env python3
"""FakeTec UI v0.5 passive dashboard + on-demand repeater link check.

Applies after v0.4.1. Limited to the pinned MeshCore 1.18 ui-new source,
ProMicro_companion_radio_ble target. Preserves the original repeater discover page.
Never flashes or transmits from the patch script. Source compile required.
"""
import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

MARKER = 'FAKETEC_UI_V05_LINK_CHECK'


def once(src, old, new, context):
    matches = src.count(old)
    if matches != 1:
        raise ValueError('%s: expected exactly one anchor, found %d' % (context, matches))
    return src.replace(old, new, 1)


def patch_cpp(src):
    if MARKER in src:
        return src
    if 'FAKETEC_UI_V041_STATUS_MENU' not in src:
        raise ValueError('FakeTec UI v0.4.1 must be applied first')
    src = once(src,
        '  AdvertPath recent[UI_RECENT_LIST_SIZE];\n',
        '''  AdvertPath recent[UI_RECENT_LIST_SIZE];
  // FAKETEC_UI_V05_LINK_CHECK: passive advertisements and manual discovery.
  AdvertPath dashboard_recent[ADVERT_PATH_TABLE_SIZE];
  bool link_check_open = false;
  bool link_check_attempted = false;
  bool link_check_rate_limited = false;
  bool link_check_tx_ok = false;
  uint32_t link_check_attempt_ms = 0;
''', 'dashboard state')

    # Helpers are in HomeScreen and compile independently of the optional
    # existing discovery page. The scan itself is guarded by UI_DISCOVER_SCREEN.
    src = once(src,
        '''  void poll() override {
    if (_shutdown_init && !_task->isButtonPressed())''',
        '''  void startLinkCheck() {
    // The button's explicit HOLD action is the only place that starts a scan.
    // Always display results on the Home/Status screen, not the discovery page.
    _page = HomePage::FIRST;
    link_check_open = true;
    uint32_t now = millis();
    if (link_check_attempted && (uint32_t)(now - link_check_attempt_ms) < 60000UL) {
      link_check_rate_limited = true;
      return; // Never retransmit during the one-minute cooldown.
    }
    link_check_rate_limited = false;
    link_check_attempted = true;
    link_check_attempt_ms = now;
#if UI_DISCOVER_SCREEN
    link_check_tx_ok = sendDiscoverRequest(); // exactly one zero-hop request
#else
    link_check_tx_ok = false;
#endif
  }

#if UI_DISCOVER_SCREEN
  int bestLinkIndex() const {
    int best = -1;
    float best_score = -1000.0f;
    // The reported outgoing and locally measured incoming SNR are both useful.
    // Rank by the weaker direction, not by a single strong receive value.
    for (uint32_t i = 0; i < disc_nodes_count; ++i) {
      const DiscoveredNode& d = discovered[i];
      if (d.type != ADV_TYPE_REPEATER) continue;
      float score = d.snr_in < d.snr_out ? d.snr_in : d.snr_out;
      if (score > best_score) { best_score = score; best = (int)i; }
    }
    return best;
  }

  unsigned respondingRepeaters() const {
    unsigned count = 0;
    for (uint32_t i = 0; i < disc_nodes_count; ++i)
      if (discovered[i].type == ADV_TYPE_REPEATER) ++count;
    return count;
  }
#endif

  void poll() override {
    if (_shutdown_init && !_task->isButtonPressed())''', 'HomeScreen poll insertion')

    # Reuse the unchanged MeshCore discovery request and response handler.
    src = once(src,
        'const char* items[] = {"Inbox", "Quick Msgs", "Find repeaters", "Advertise", "Back"};',
        'const char* items[] = {"Link Check", "Inbox", "Quick Msgs", "Find repeaters", "Advertise", "Back"};',
        'Quick Actions first item')
    src = once(src,
        'uint8_t first = recent_menu_selection < 3 ? 0 : 2;',
        'uint8_t first = recent_menu_selection < 3 ? 0 : recent_menu_selection - 2;',
        'three-line menu window supports sixth item')
    # There are two handlers: short press and protected double-press.
    if src.count('recent_menu_selection = (recent_menu_selection + 1) % 5;') != 2:
        raise ValueError('expected two Quick Actions cycle expressions from v0.4.1')
    src = src.replace('recent_menu_selection = (recent_menu_selection + 1) % 5;',
                      'recent_menu_selection = (recent_menu_selection + 1) % 6;')

    src = once(src,
        '''        if (recent_menu_selection == 0) {
          _task->openInbox();
        } else if (recent_menu_selection == 1) {
          _task->openQuickMsgs();
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
''',
        '''        if (recent_menu_selection == 0) {
          startLinkCheck(); // on-device results appear in Home/Status overlay
        } else if (recent_menu_selection == 1) {
          _task->openInbox();
        } else if (recent_menu_selection == 2) {
          _task->openQuickMsgs();
        } else if (recent_menu_selection == 3) {
#if UI_DISCOVER_SCREEN
          _page = HomePage::DISCOVERY;
          _task->showAlert("Hold to scan", 1200);
#else
          _task->showAlert("Scan unavailable", 1200);
#endif
        } else if (recent_menu_selection == 4) {
          _page = HomePage::ADVERT;
          _task->showAlert("Hold to advertise", 1200);
        }
''', 'Quick Actions dispatch')

    src = once(src,
        '''  bool handleInput(char c) override {
    if (recent_menu_open) {
''',
        '''  bool handleInput(char c) override {
    if (link_check_open) {
      // A single short click or hold dismisses the on-device result overlay.
      // Neither event resends the discovery request.
      if (c == KEY_ENTER || c == KEY_NEXT || c == KEY_RIGHT ||
          c == KEY_PREV || c == KEY_LEFT) {
        link_check_open = false;
        _page = HomePage::FIRST;
      }
      return true;
    }
    if (recent_menu_open) {
''', 'link-check input priority')

    # Add an independent result overlay ahead of the standard HomeScreen FIRST
    # page. Result data remains in the existing discovery array.
    src = once(src,
        '''    if (_page == HomePage::FIRST) {
''',
        '''    if (link_check_open) {
      display.setColor(UIColor::primary_txt);
      display.setTextSize(1);
      display.setCursor(0, 20);
      display.print("LINK CHECK");
#if UI_DISCOVER_SCREEN
      const int best = bestLinkIndex();
      const unsigned responded = respondingRepeaters();
      if (link_check_rate_limited) {
        uint32_t elapsed = (uint32_t)(millis() - link_check_attempt_ms);
        unsigned secs = (elapsed < 60000UL) ? (unsigned)((60000UL - elapsed + 999UL) / 1000UL) : 0;
        snprintf(tmp, sizeof(tmp), "Cooldown %us", secs);
        display.setCursor(0, 31);
        display.print(tmp);
        display.setCursor(0, 42);
        display.print("Previous scan kept");
      } else if (!link_check_tx_ok) {
        display.setCursor(0, 31);
        display.print("Request not sent");
      } else if ((uint32_t)(millis() - discovery_req_time) < 7000UL) {
        display.setCursor(0, 31);
        snprintf(tmp, sizeof(tmp), "Checking... %u RPT", responded);
        display.print(tmp);
      } else if (best < 0) {
        display.setCursor(0, 31);
        display.print("No rpt replies");
        display.setCursor(0, 42);
        display.print("Check RF/settings");
      }
      if (best >= 0 && link_check_tx_ok &&
          (uint32_t)(millis() - discovery_req_time) >= 7000UL) {
        const DiscoveredNode& d = discovered[best];
        display.setCursor(0, 31);
        snprintf(tmp, sizeof(tmp), "%u RPT  %.12s", responded,
                 d.name[0] ? d.name : "Unnamed");
        display.print(tmp);
        display.setCursor(0, 42);
        snprintf(tmp, sizeof(tmp), "IN:%+.1f OUT:%+.1f", d.snr_in, d.snr_out);
        display.print(tmp);
      }
#else
      display.setCursor(0, 31);
      display.print("Discovery disabled");
#endif
      display.setCursor(0, 54);
      display.print("Click/Hold: Home");
      return 1000;
    }

    if (_page == HomePage::FIRST) {
''', 'result overlay ahead of first page')

    start = src.index('    if (_page == HomePage::FIRST) {\n')
    end = src.index('    } else if (_page == HomePage::RECENT) {', start)
    dashboard = '''    if (_page == HomePage::FIRST) {
      // Passive, zero-transmit monitoring. Only directly heard repeaters
      // advertised in the past 30 minutes contribute to this count.
      display.setColor(UIColor::primary_txt);
      display.setTextSize(1);
      the_mesh.getRecentlyHeard(dashboard_recent, ADVERT_PATH_TABLE_SIZE);
      const uint32_t now = _rtc->getCurrentTime();
      unsigned repeater_count = 0;
      const AdvertPath* latest = NULL;
      for (int i = 0; i < ADVERT_PATH_TABLE_SIZE; ++i) {
        const AdvertPath& a = dashboard_recent[i];
        if (!a.name[0] || !a.recv_timestamp || a.path_len != 0 ||
            now < a.recv_timestamp || now - a.recv_timestamp > 1800UL) continue;
        ContactInfo* contact = the_mesh.lookupContactByPubKey(
            a.pubkey_prefix, sizeof(a.pubkey_prefix));
        if (!contact || contact->type != ADV_TYPE_REPEATER) continue;
        ++repeater_count;
        if (!latest || a.recv_timestamp > latest->recv_timestamp) latest = &a;
      }
      snprintf(tmp, sizeof(tmp), "MSG:%u  RPT:%u", (unsigned)_task->getMsgCount(), repeater_count);
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
'''
    src = src[:start] + dashboard + src[end:]
    if src.count(MARKER) != 1:
        raise ValueError('incorrect source marker count')
    if src.count('startLinkCheck();') != 1:
        raise ValueError('link check must only be invoked by the menu')
    return src


def atomic_write(path, content):
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '.v05.', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(content)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=Path.home() / 'faketec-ui' / 'MeshCore')
    parser.add_argument('--check', action='store_true', help='validate without writing')
    args = parser.parse_args()
    cpp = args.source_root / 'examples/companion_radio/ui-new/UITask.cpp'
    try:
        original = cpp.read_text(encoding='utf-8')
        updated = patch_cpp(original)
    except (ValueError, OSError) as exc:
        sys.exit('ERROR: no changes saved: %s' % exc)
    if original == updated:
        print('FakeTec UI v0.5 already applied; no changes needed.')
        return
    if args.check:
        print('Dry-run OK. Passive status + first-menu Link Check ready to apply.')
        return
    backup = cpp.with_suffix('.cpp.v05-backup')
    if not backup.exists():
        shutil.copy2(cpp, backup)
    atomic_write(cpp, updated)
    print('Updated ' + str(cpp))
    print('Backup: ' + str(backup))
    print('Next: compile and test on one FakeTec; no flashing was performed.')


if __name__ == '__main__':
    main()
