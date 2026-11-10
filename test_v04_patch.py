"""Offline source-patch tests using the exact v0.2 generated C++ screen."""
import ast
import importlib.util
from pathlib import Path
import tempfile

HERE = Path(__file__).resolve().parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

v03 = load('v03', HERE / 'faketec_ui_v0_3_presets_patch.py')
v04 = load('v04', HERE / 'faketec_ui_v0_4_toggle_patch.py')

def get_v02_screen():
    t = ast.parse((HERE / 'faketec_ui_v0_2_messaging_patch.py').read_text())
    for call in ast.walk(t):
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == 'rep' and len(call.args)>=4:
            if isinstance(call.args[3], ast.Constant) and call.args[3].value == 'insert messaging screen':
                return ast.literal_eval(call.args[2])
    raise ValueError('Cannot find v0.2 source insertion')

base = get_v02_screen()
assert 'class QuickMessagesScreen' in base and 'void sendSelected' in base
configuration = v03.read_config(HERE / 'faketec_presets_v03.json')
assert configuration['preset_marker'] == ' [Quick Msg]'
v03src = v03.apply_patch(base,configuration)
assert 'PRESET_COUNT = 15' in v03src
v04src = v04.patch_source(v03src)
assert '[Quick Msg] ON' in v04src
assert 'FAKETEC_UI_V04_SAFE_BUTTONS' in v04src
assert 'if (c == KEY_PREV)' in v04src
assert 'c = KEY_NEXT;' in v04src
assert 'else if (confirm_choice == 1) sendSelected();' in v04src
assert 'else mode = PRESETS;  // deliberate CANCEL; no transmit' in v04src
assert 'preset = (preset + 1) % (PRESET_COUNT + 1)' in v04src
assert 'age = (age + 1) % (count + 1)' in v04src
assert 'append_marker = kAppendPresetMarker' in v04src
assert 'if (append_marker)' in v04src
assert v04.patch_source(v04src) == v04src
assert v03.apply_patch(v04src,configuration) == v04src  # rebuild idempotence
assert v04src.count('FAKETEC_UI_V04_SAFE_BUTTONS') == 1
assert 'if (c == KEY_PREV || c == KEY_LEFT)' not in v04src
with tempfile.TemporaryDirectory() as td:
    p=Path(td)/'examples/companion_radio/ui-new/UITask.cpp'
    p.parent.mkdir(parents=True)
    p.write_text(v03src)
    assert v04.patch_source(p.read_text()) == v04src
print('PASS: 15 presets, renamed label, safe double-click, explicit Back/Cancel, on-device toggle, idempotence')
