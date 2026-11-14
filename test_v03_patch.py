#!/usr/bin/env python3
"""Offline fixture tests against the real v0.2 QuickMessagesScreen insertion."""
import ast
import json
import subprocess
import sys
import tempfile
from pathlib import Path

base = Path(__file__).resolve().parent
src = (base / 'faketec_ui_v0_2_messaging_patch.py').read_text()
constants = [n.value for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Constant)
             and isinstance(n.value, str) and 'class QuickMessagesScreen' in n.value]
assert len(constants) == 1, 'Could not recover v0.2 source block'
script = base / 'faketec_ui_v0_3_presets_patch.py'
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    cpp = root / 'examples/companion_radio/ui-new/UITask.cpp'
    cpp.parent.mkdir(parents=True)
    cpp.write_text('#include <stdint.h>\n' + constants[0])
    def run(*opts, expect=0):
        p = subprocess.run([sys.executable, str(script), '--source-root', str(root),
                            '--config', str(base / 'faketec_presets_v03.json'), *opts],
                           text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert p.returncode == expect, p.stdout
        return p.stdout
    source = cpp.read_text()
    assert 'PRESET_COUNT = 10' in source
    run('--check')
    assert cpp.read_text() == source, 'Dry-run modified the source!'
    run()
    new = cpp.read_text()
    assert 'PRESET_COUNT = 15' in new
    assert new.count('FAKETEC_UI_V03_PRESETS') == 1
    assert new.count('FAKETEC_UI_V03_SEND_MARKER') == 1
    assert "Please reply to confirm you've read this" in new
    assert 'static constexpr bool kAppendPresetMarker = true;' in new
    assert cpp.with_suffix('.cpp.v03-backup').read_text() == source
    assert 'Already up to date' in run()
    assert cpp.read_text() == new
    config = json.loads((base / 'faketec_presets_v03.json').read_text())
    config['append_preset_marker'] = False
    config['presets'][1] = 'Yes, received'
    other = root / 'other.json'
    other.write_text(json.dumps(config))
    p = subprocess.run([sys.executable, str(script), '--source-root', str(root),
                        '--config', str(other)], text=True, capture_output=True)
    assert p.returncode == 0, p.stdout + p.stderr
    assert 'static constexpr bool kAppendPresetMarker = false;' in cpp.read_text()
    assert 'Yes, received' in cpp.read_text()
    assert cpp.with_suffix('.cpp.v03-backup').read_text() == source
    assert cpp.read_text().count('FAKETEC_UI_V03_PRESETS') == 1
print('PASS: v0.2 fixture, dry-run, 15 presets, TX marker, idempotence, reconfigure, original backup')
