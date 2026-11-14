"""Offline v0.5.2 source transformation regression (not a compiled firmware test)."""
import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
upstream = runpy.run_path(str(HERE / 'test_v051_ack_voltage_patch.py'))['patched']
plugin = runpy.run_path(str(HERE / 'faketec_ui_v0_5_2_rooms_navigation_patch.py'))
patch = plugin['patch_cpp']
result = patch(upstream)
assert patch(result) == result, 'idempotence failed'
assert result.count('FAKETEC_UI_V052_ROOMS_NAV') == 1
assert 'ContactInfo* room = the_mesh.lookupContactByPubKey(selected_room_pubkey, PUB_KEY_SIZE);' in result
assert 'contact.type == ADV_TYPE_ROOM' in result
assert 'room->type == ADV_TYPE_ROOM' in result
assert 'sending_to_room = true;' in result
assert 'sendMessage(*room, timestamp, 0, message,' in result
assert 'if (mode == CHANNELS) {' in result
assert 'target_pos = (target_pos + 1) % (targetCount() + 1)' in result
assert 'target_pos = (target_pos + choices - 1) % choices;' in result
assert 'preset = (preset + PRESET_COUNT) % (PRESET_COUNT + 1);' in result
assert 'mode = reply_mode ? INBOX : CHANNELS;' in result
assert 'if (confirm_choice == 0) sendSelected();' in result
assert 'if (mode == CONFIRM) {' in result
assert 'Room post ACK' in result and 'Room: await ACK' in result
assert 'DM ACK received' in result
assert 'queued = the_mesh.sendGroupMessage' in result, 'channel sending lost'
assert 'snprintf(destination, sizeof(destination), "R:%.16s", room->name);' in result
assert 'if (c == KEY_PREV)' in result
assert 'c = KEY_NEXT;\n    }\n    if (c == KEY_LEFT)' not in result
assert 'RPT FOUND:' in result
assert 'getBLEPin()' in result
# A malformed ancestor must fail closed without changing on-disk source.
try:
    patch(upstream.replace('FAKETEC_UI_V051_ACK_VOLTAGE', 'DRIFT'))
    raise AssertionError('mismatched source accepted')
except ValueError:
    pass
try:
    patch(upstream.replace('    if (c == KEY_PREV) {', '    if (c == OTHER_KEY) {'))
    raise AssertionError('changed hardware mapping accepted')
except ValueError:
    pass
print('PASS: v0.5.2 saved room target flow, encrypted send, ACK semantics, 1-next/2-prev, guarded anchors')
