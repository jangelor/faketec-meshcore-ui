"""FakeTec v0.5 offline source-patch regression tests, no hardware/compile."""
import ast
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / ('faketec_ui_' + name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def replacement(label):
    tree = ast.parse((HERE / 'faketec_ui_v0_2_messaging_patch.py').read_text())
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == 'rep' and len(node.args) >= 4):
            try:
                if ast.literal_eval(node.args[3]) == label:
                    return ast.literal_eval(node.args[2])
            except ValueError:
                pass
    raise RuntimeError('v0.2 source insert not found: ' + label)


v03 = load('v0_3_presets_patch')
v04 = load('v0_4_toggle_patch')
v041 = load('v0_4_1_status_patch')
v05 = load('v0_5_dashboard_patch')
config = v03.read_config(HERE / 'faketec_presets_v03.json')
menu = replacement('v0.1 menu render')
actions = replacement('v0.1 menu actions')
gate = replacement('open menu from Home as well')
messages = replacement('insert messaging screen')
menu_button = '''    if (recent_menu_open) {
      if (c == KEY_NEXT || c == KEY_RIGHT) {
        recent_menu_selection = (recent_menu_selection + 1) % 5;
        return true;
      }
      if (c == KEY_PREV || c == KEY_LEFT) {
        recent_menu_open = false;
        return true;
      }
      if (c == KEY_ENTER) {
        recent_menu_open = false;
''' + actions + '''        return true;
      }
      return true;
    }
'''
# Include specific MeshCore HomeScreen anchors, alongside v0.2 inserted UI.
mock = '''class HomeScreen : public UIScreen {
  AdvertPath recent[UI_RECENT_LIST_SIZE];
''' + menu + '''\n  void poll() override {
    if (_shutdown_init && !_task->isButtonPressed()) { _task->shutdown(); }
  }
  int render(DisplayDriver& display) override {
''' + menu + '''\n    if (_page == HomePage::FIRST) {
      display.print("MSG: 0");
    } else if (_page == HomePage::RECENT) {
      display.print("Recent");
    }
  }
  bool handleInput(char c) override {
''' + menu_button + gate + '''
  }
};
''' + messages
# The synthetic source must contain the menu render once only.
mock = mock.replace(menu + '\n  void poll()', '  void poll()', 1)
assert mock.count('const char* items[]') == 1
mock = v03.apply_patch(mock, config)
mock = v04.patch_source(mock)
mock = v041.patch_cpp(mock)
patched = v05.patch_cpp(mock)
assert patched != mock
assert v05.patch_cpp(patched) == patched
assert patched.count(v05.MARKER) == 1
assert '"Link Check", "Inbox", "Quick Msgs", "Find repeaters", "Advertise", "Back"' in patched
assert 'recent_menu_selection = (recent_menu_selection + 1) % 6;' in patched
assert patched.count('recent_menu_selection = (recent_menu_selection + 1) % 6;') == 2
assert 'if (recent_menu_selection == 0) {\n          startLinkCheck();' in patched
assert patched.count('startLinkCheck();') == 1
assert 'link_check_open = true;' in patched
assert 'link_check_tx_ok = sendDiscoverRequest();' in patched
assert 'link_check_rate_limited = true;' in patched
assert 'now - link_check_attempt_ms) < 60000UL' in patched
assert 'bestLinkIndex() const' in patched and 'd.snr_in < d.snr_out' in patched
assert 'ADV_TYPE_REPEATER' in patched and 'a.path_len != 0' in patched
assert 'now - a.recv_timestamp > 1800UL' in patched
assert '_task->getMsgCount()' in patched
assert '_task->getBattMilliVolts()' in patched
assert '_task->hasConnection()' in patched
assert 'recent_menu_selection == 2' in patched and '_task->openQuickMsgs()' in patched
assert 'recent_menu_selection == 4' in patched and 'HomePage::ADVERT' in patched
assert 'recent_menu_open = false;' in patched
assert 'if (link_check_open) {' in patched
assert 'if (c == KEY_ENTER || c == KEY_NEXT' in patched
assert 'd.name[0] ? d.name : "Unnamed"' in patched
# Fail safely if patch order is wrong or the previous menu changed.
try:
    v05.patch_cpp(mock.replace('FAKETEC_UI_V041_STATUS_MENU', 'REMOVED'))
    raise AssertionError('missing predecessor should fail')
except ValueError:
    pass
try:
    v05.patch_cpp(mock.replace('"Inbox", "Quick Msgs", "Find repeaters"',
                                '"Inbox", "Broken", "Find repeaters"'))
    raise AssertionError('drifted menu should fail')
except ValueError:
    pass
print('PASS: FakeTec UI v0.5 offline patch, first option, link check cooldown, dashboard, backwards compatibility')
