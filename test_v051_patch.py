"""Offline v0.5.1 patch regression tests, including all earlier UI patches.

No firmware compilation, RF operations, or hardware flashing.
"""
import importlib.util
import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
v05_source = runpy.run_path(str(HERE / 'test_v05_patch.py'))['patched']
spec = importlib.util.spec_from_file_location('v051', HERE / 'faketec_ui_v0_5_1_ux_patch.py')
v051 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v051)

patched = v051.patch_cpp(v05_source)
assert patched != v05_source
assert v051.patch_cpp(patched) == patched, 'not idempotent'
assert patched.count(v051.MARKER) == 1
assert 'const char* items[] = {"Link Check", "Inbox", "Quick Msgs"' in patched
assert patched.count('startLinkCheck();') == 2, 'menu trigger plus overlay recheck'
assert 'now - link_check_attempt_ms' not in patched
assert 'link_check_rate_limited' not in patched
assert 'Cooldown' not in patched
assert 'startLinkCheck();\n      } else if (c == KEY_NEXT' in patched
assert 'Tap:Back Hold:Scan' in patched
assert 'RPT FOUND:%u' in patched and 'HEARD:%u' in patched
assert 'BEST: %.14s' in patched and 'SEEN: %.14s' in patched
assert 'd.snr_in < d.snr_out' in patched, 'best must prefer weaker of two directions'
assert 'if (!_task->hasConnection()) {' in patched
assert 'PIN:%06lu B:%.2fV' in patched and 'the_mesh.getBLEPin()' in patched
assert 'BLE:WAIT' in patched and 'BLE:ON' in patched
assert 'uint8_t confirm_choice = 0;  // 0=SEND, 1=tag toggle, 2=CANCEL' in patched
assert 'display.print(confirm_choice == 0 ? "> SEND" : "  SEND");' in patched
assert 'display.print(confirm_choice == 1 ? "> " : "  ");' in patched
assert 'if (confirm_choice == 0) sendSelected();' in patched
assert 'else if (confirm_choice == 1) append_marker = !append_marker;' in patched
assert 'confirm_choice = (confirm_choice + 1) % 3' in patched
assert '          confirm_choice = 0;\n          mode = CONFIRM;' in patched
assert 'static constexpr bool kAppendPresetMarker = true;' in patched
assert 'display.print(append_marker ? "[Quick Msg] ON" : "[Quick Msg] OFF");' in patched
# A drifted or incompletely patched ancestor must fail closed.
try:
    v051.patch_cpp(v05_source.replace('FAKETEC_UI_V05_LINK_CHECK', 'MISSING'))
    raise AssertionError('patch applied to unsupported source')
except ValueError:
    pass
try:
    v051.patch_cpp(v05_source.replace('if (confirm_choice == 1) sendSelected();',
                                       'if (confirm_choice == 1) sendWrongMessage();'))
    raise AssertionError('button mapping drift not detected')
except ValueError:
    pass
print('PASS: v0.5.1 SEND-first, one-click tag, no cooldown, rescan-on-hold, PIN restoration, new counters')
