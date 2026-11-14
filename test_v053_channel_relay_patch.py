#!/usr/bin/env python3
"""Source regression for FakeTec v0.5.3. No PlatformIO or device required."""
import runpy
from pathlib import Path
H = Path(__file__).resolve().parent
m = runpy.run_path(str(H/'faketec_ui_v0_5_3_channel_relay_patch.py'))
u = runpy.run_path(str(H/'test_v052_rooms_nav_patch.py'))['result']
patched_ui = m['patch_ui_cpp'](u)
assert m['patch_ui_cpp'](patched_ui) == patched_ui, 'UI idempotence'
assert patched_ui.count('FAKETEC_UI_V053_RELAY_ECHO') == 1
assert patched_ui.count('sendGroupMessageWatched(timestamp, ch.channel') == 2
assert 'sendGroupMessage(timestamp, ch.channel' not in patched_ui
assert 'Channel: queued' in patched_ui
assert 'RELAY SEEN' in patched_ui
assert 'No echo: unconfirmed' in patched_ui
assert 'CHANNEL_RELAY_SEEN' in patched_ui
assert 'PIN:%06lu TX:%s' in patched_ui
assert 'Room post ACK' in patched_ui
assert 'DM ACK received' in patched_ui
assert 'RPT FOUND:' in patched_ui
assert 'FAKETEC_UI_V052_ROOMS_NAV' in patched_ui
assert 'KEY_PREV' in patched_ui
assert 'renderVoltage(display)' in patched_ui
assert '[Quick Msg]' in patched_ui

header = '''class MyMesh : public BaseChatMesh, public DataStoreHost {
public:
  class Listener {
      virtual void onACKRecv(uint32_t ack_crc) { }
  };
  int  getRecentlyHeard(AdvertPath dest[], int max_num);
protected:
  void logRxRaw(float snr, float rssi, const uint8_t raw[], int len) override;
private:
  Listener* _listener;
};'''
ph = m['patch_hdr'](header)
assert m['patch_hdr'](ph) == ph
assert ph.count('FAKETEC_UI_V053_RELAY_ECHO') == 1
assert 'onChannelRelayStatus(uint8_t status)' in ph
assert 'logRx(mesh::Packet* packet' in ph
assert 'logTxFail(mesh::Packet* packet' in ph
assert 'channel_relay_hash[MAX_HASH_SIZE]' in ph
assert 'getChannelRelayStatus() const' in ph

cpp = '''void MyMesh::logRxRaw(float snr, float rssi, const uint8_t raw[], int len) {
}
void MyMesh::loop() {
  BaseChatMesh::loop();
}'''
pc = m['patch_mesh_cpp'](cpp)
assert m['patch_mesh_cpp'](pc) == pc
assert pc.count('FAKETEC_UI_V053_RELAY_ECHO') == 1
assert 'void MyMesh::logRx(mesh::Packet* packet' in pc
assert 'packet->getPathHashCount() == 0' in pc
assert 'channel_relay_state != CHANNEL_RELAY_LISTENING' in pc
assert 'channel_relay_started_ms) > 60000UL' in pc
assert 'pkt->calculatePacketHash(channel_relay_hash)' in pc
assert 'logTx(mesh::Packet* packet' in pc
assert 'CHANNEL_RELAY_QUEUE_STALE' in pc
assert 'createGroupDatagram(PAYLOAD_TYPE_GRP_TXT' in pc
assert 'sendFloodScoped(channel, pkt)' in pc
assert 'void MyMesh::logTxFail(' in pc
assert pc.index('logRx(mesh::Packet*') < pc.index('logRxRaw(float')
ui_h = '  void onACKRecv(uint32_t ack_crc) override;  // FAKETEC_UI_V051_ACK_VOLTAGE\n'
ui_h2 = m['patch_ui_hdr'](ui_h)
assert m['patch_ui_hdr'](ui_h2) == ui_h2
assert 'onChannelRelayStatus(uint8_t status) override;' in ui_h2
for f,s,old in [
  (m['patch_hdr'],header, '  Listener* _listener;'),
  (m['patch_mesh_cpp'],cpp,'BaseChatMesh::loop();'),
  (m['patch_ui_cpp'],u,'FAKETEC_UI_V052_ROOMS_NAV'),
]:
    try:
        f(s.replace(old, 'BROKEN', 1))
        raise AssertionError('Unsafe source drift passed validation')
    except ValueError:
        pass
print('PASS: v0.5.3 exact hash, pre-dedup receive, nonempty relay path, 60s timeout, channels only, room/DM unaffected, guarded idempotent patches')
