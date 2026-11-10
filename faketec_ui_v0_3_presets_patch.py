#!/usr/bin/env python3
"""FakeTec UI v0.3: update v0.2 QuickMessagesScreen with configurable presets.

Targets MeshCore 1.18, ProMicro_companion_radio_ble, on top of the v0.1 and
v0.2 source patches. It only edits the source file; never flashes any device.

Python 3.8+ required. Customize faketec_presets_v03.json and rerun this script
before building the firmware. The source includes the presets at compile time;
this is not a BLE/on-device runtime configuration interface.
"""
import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

V02 = 'FAKETEC_UI_V02_MESSAGING'
V03 = 'FAKETEC_UI_V03_PRESETS'
SEND_MARKER = 'FAKETEC_UI_V03_SEND_MARKER'


def read_config(path):
    with path.open('r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError('Configuration must be a JSON object')
    presets = data.get('presets')
    if not isinstance(presets, list) or not (1 <= len(presets) <= 32):
        raise ValueError('presets must contain 1 to 32 strings')
    for index, msg in enumerate(presets, 1):
        if not isinstance(msg, str) or not (1 <= len(msg.encode('utf-8')) <= 100):
            raise ValueError('Preset %d must be 1 to 100 UTF-8 bytes' % index)
        if any(ord(c) < 32 or ord(c) > 126 for c in msg):
            raise ValueError('Preset %d must contain printable ASCII only' % index)
    if not isinstance(data.get('append_preset_marker'), bool):
        raise ValueError('append_preset_marker must be true or false')
    marker = data.get('preset_marker')
    if not isinstance(marker, str) or len(marker) > 24 or any(ord(c) < 32 or ord(c) > 126 for c in marker):
        raise ValueError('preset_marker must be printable ASCII, at most 24 characters')
    for index, msg in enumerate(presets, 1):
        if len((msg + marker).encode('utf-8')) > 120:
            raise ValueError('Preset %d and marker exceed 120-byte transmit buffer' % index)
    return data


def c_string(s):
    return json.dumps(s, ensure_ascii=True)


def make_method(data):
    messages = data['presets']
    lines = [
        '  // ' + V03 + ': generated from faketec_presets_v03.json.',
        '  // Re-run the v0.3 patch after editing the JSON, then rebuild/reflash.',
        '  static const char* presetText(uint8_t i) {',
        '    static const char* const presets[PRESET_COUNT] = {',
    ]
    for index, msg in enumerate(messages):
        ending = ',' if index < len(messages) - 1 else ''
        lines.append('      ' + c_string(msg) + ending)
    lines += [
        '    };',
        '    return presets[i % PRESET_COUNT];',
        '  }',
        '',
        '  static constexpr bool kAppendPresetMarker = ' + ('true' if data['append_preset_marker'] else 'false') + ';',
        '  static const char* presetMarker() { return ' + c_string(data['preset_marker']) + '; }',
        '',
    ]
    return '\n'.join(lines)


def apply_patch(source, data):
    if V02 not in source or 'class QuickMessagesScreen' not in source:
        raise ValueError('Missing FakeTec v0.2 messaging UI. Apply v0.1 then v0.2 first.')
    count_pattern = r'  enum \{ HISTORY = 12, PRESET_COUNT = \d+ \};'
    source, count = re.subn(count_pattern, '  enum { HISTORY = 12, PRESET_COUNT = %d };' % len(data['presets']), source)
    if count != 1:
        raise ValueError('Expected exactly one PRESET_COUNT definition, found %d' % count)

    # Replace only the entire preset method and its v0.3 options, stopping at
    # the next existing member method. This handles both v0.2 and v0.3 input.
    first = source.find('  static const char* presetText(uint8_t i) {')
    if first < 0:
        raise ValueError('Cannot locate QuickMessagesScreen::presetText')
    start_marker = source.rfind('  // ' + V03, 0, first)
    if start_marker >= 0 and first - start_marker < 200:
        first = start_marker
    next_method = source.find('  Entry* selected() {', first)
    if next_method < 0 or next_method - first > 5000:
        raise ValueError('Cannot locate the preset method boundary')
    # Do not preserve an earlier v0.2 comment that belongs to the old method.
    source = source[:first] + make_method(data) + source[next_method:]

    if SEND_MARKER not in source:
        old = '  void sendSelected() {\n    const char* message = presetText(preset);\n'
        new = '''  void sendSelected() {
    // FAKETEC_UI_V03_SEND_MARKER: optional preset label is applied only at TX.
    const char* message = presetText(preset);
    char tagged_message[128];
    if (kAppendPresetMarker) {
      int written = snprintf(tagged_message, sizeof(tagged_message),
                             "%s%s", message, presetMarker());
      if (written < 0 || written >= (int)sizeof(tagged_message)) {
        task->showAlert("Preset too long", 1800);
        return;
      }
      message = tagged_message;
    }
'''
        if source.count(old) != 1:
            raise ValueError('Missing or duplicated sendSelected anchor; no changes saved')
        source = source.replace(old, new, 1)
    elif source.count(SEND_MARKER) != 1:
        raise ValueError('Unexpected number of v0.3 transmit markers')

    if source.count(V03) != 1:
        raise ValueError('Unexpected number of v0.3 preset markers')
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path,
                        default=Path.home() / 'faketec-ui' / 'MeshCore',
                        help='MeshCore source checkout, including v0.1 and v0.2 patches')
    parser.add_argument('--config', type=Path,
                        default=Path(__file__).resolve().with_name('faketec_presets_v03.json'))
    parser.add_argument('--check', action='store_true',
                        help='Verify applicability and show planned changes without writing')
    args = parser.parse_args()

    cpp = args.source_root / 'examples/companion_radio/ui-new/UITask.cpp'
    if not cpp.is_file():
        sys.exit('ERROR: source file missing: ' + str(cpp))
    try:
        data = read_config(args.config)
        old = cpp.read_text(encoding='utf-8')
        new = apply_patch(old, data)
    except (ValueError, OSError) as e:
        sys.exit('ERROR: no source changes saved: ' + str(e))

    if old == new:
        print('Already up to date; no changes needed.')
        return
    print('Configuration valid: %d presets; preset marker %s' % (
        len(data['presets']), 'ON' if data['append_preset_marker'] else 'OFF'))
    if args.check:
        print('Dry-run OK. Target source: ' + str(cpp))
        return

    backup = cpp.with_suffix('.cpp.v03-backup')
    if not backup.exists():
        shutil.copy2(cpp, backup)
    # Atomic replace: do not leave a half-written source file on failure.
    fd, tmpname = tempfile.mkstemp(prefix='.UITask.v03.', suffix='.cpp', dir=str(cpp.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            f.write(new)
        os.replace(tmpname, cpp)
    finally:
        if os.path.exists(tmpname):
            os.unlink(tmpname)
    print('Updated ' + str(cpp))
    print('Original v0.2 source backup: ' + str(backup))
    print('Next: python -m platformio run -e ProMicro_companion_radio_ble')


if __name__ == '__main__':
    main()
