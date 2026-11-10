"""Offline FakeTec UI v0.4.1 patch mechanics tests (no compilation or hardware)."""
import ast
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def replacement(label):
    tree = ast.parse((HERE / 'faketec_ui_v0_2_messaging_patch.py').read_text())
    for c in ast.walk(tree):
        if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == 'rep' and len(c.args) >= 4:
            try:
                if ast.literal_eval(c.args[3]) == label:
                    return ast.literal_eval(c.args[2])
            except ValueError:
                pass
    raise ValueError('missing v0.2 source: ' + label)


v03 = load('v03', HERE / 'faketec_ui_v0_3_presets_patch.py')
v04 = load('v04', HERE / 'faketec_ui_v0_4_toggle_patch.py')
v041 = load('v041', HERE / 'faketec_ui_v0_4_1_status_patch.py')
config = v03.read_config(HERE / 'faketec_presets_v03.json')
assert config['preset_marker'] == ' [Quick Msg]'
assert len(config['presets']) == 15

# Construct the code segments v0.2 actually inserts and the v0.1 part it retains.
menu = replacement('v0.1 menu render')
actions = replacement('v0.1 menu actions')
gate = replacement('open menu from Home as well')
msg_screen = replacement('insert messaging screen')
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
base_cpp = menu + gate + menu_button + msg_screen
base_hdr = '  UIScreen* quick_messages; // FAKETEC_UI_V02_MESSAGING\n  void openCanned();\n'
assert base_cpp.count('openCanned') == 4, base_cpp.count('openCanned')
cpp03 = v03.apply_patch(base_cpp, config)
cpp04 = v04.patch_source(cpp03)
cpp041 = v041.patch_cpp(cpp04)
hdr041 = v041.patch_header(base_hdr)

assert '"Quick Msgs"' in cpp041
assert '"Canned msgs"' not in cpp041
assert '"QUICK MSGS"' in cpp041
assert '"CANNED MESSAGE"' not in cpp041
assert 'HomePage::RADIO' in cpp041
assert 'HomePage::FIRST' in cpp041 and 'HomePage::RECENT' in cpp041
assert cpp041.count('FAKETEC_UI_V041_STATUS_MENU') == 1
assert 'recent_menu_selection = (recent_menu_selection + 1) % 5;' in cpp041
assert 'recent_menu_open = false;\n        return true;' not in cpp041.split('if (c == KEY_PREV || c == KEY_LEFT) {', 1)[1].split('}', 1)[0]
assert cpp041.count('openQuickMsgs') == 4 and 'openCanned' not in cpp041
assert 'void openQuickMsgs();' in hdr041 and 'openCanned' not in hdr041
assert 'if (append_marker)' in cpp041
assert 'else if (confirm_choice == 1) sendSelected();' in cpp041
assert v041.patch_cpp(cpp041) == cpp041
assert v041.patch_header(hdr041) == hdr041
assert v03.apply_patch(cpp041, config) == cpp041
assert v04.patch_source(cpp041) == cpp041
assert v041.patch_cpp(v04.patch_source(v03.apply_patch(cpp041, config))) == cpp041

# Fail safely on a wrong version or altered anchor.
try:
    v041.patch_cpp(cpp03)
    raise AssertionError('v0.4.1 patch must reject v0.3 code')
except ValueError:
    pass
try:
    v041.patch_cpp(cpp04.replace('"Canned msgs"', '"Unknown msgs"'))
    raise AssertionError('v0.4.1 patch must reject drifted menu')
except ValueError:
    pass

print('PASS: v0.4.1 offline patch, status access, Quick Msgs rename, safe navigation, idempotence')
