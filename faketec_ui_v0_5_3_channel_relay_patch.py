#!/usr/bin/env python3
"""FakeTec v0.5.3: passive return-echo detection for on-device channel sends.

No repeater changes, additional RF packets, or delivery claims. Only the
most recently sent Quick Msg channel packet is watched. Uses MeshCore's
Dispatcher::logRx hook, which fires before packet duplicate suppression.

Patch applies after v0.5.2 rooms/navigation. Backs up each source; fails
closed on changed anchors. No device is flashed by this patch script.
"""
import argparse
import os
import shutil
import tempfile
from pathlib import Path

MARKER = 'FAKETEC_UI_V053_RELAY_ECHO'


def once(src, old, new, label):
    n = src.count(old)
    if n != 1:
        raise ValueError(f'{label}: expected one exact source anchor, found {n}')
    return src.replace(old, new, 1)


def patch_hdr(src):
    if MARKER in src:
        return src
    src = once(src,
        '''class MyMesh : public BaseChatMesh, public DataStoreHost {
public:
  class Listener {''',
        '''class MyMesh : public BaseChatMesh, public DataStoreHost {
public:
  // FAKETEC_UI_V053_RELAY_ECHO: a received matching retransmission, not an ACK.
  enum ChannelRelayStatus : uint8_t {
    CHANNEL_RELAY_NONE = 0,
    CHANNEL_RELAY_QUEUED = 1,
    CHANNEL_RELAY_LISTENING = 2,
    CHANNEL_RELAY_SEEN = 3,
    CHANNEL_RELAY_UNCONFIRMED = 4,
    CHANNEL_RELAY_TX_FAILED = 5,
    CHANNEL_RELAY_QUEUE_STALE = 6
  };

  class Listener {''', 'relay states')
    src = once(src,
        '      virtual void onACKRecv(uint32_t ack_crc) { }',
        '''      virtual void onACKRecv(uint32_t ack_crc) { }
      virtual void onChannelRelayStatus(uint8_t status) { }''', 'on-device status callback')
    src = once(src,
        '  int  getRecentlyHeard(AdvertPath dest[], int max_num);',
        '''  int  getRecentlyHeard(AdvertPath dest[], int max_num);
  // Identical group payload format to BaseChatMesh::sendGroupMessage, with
  // an exact packet hash saved *before* the packet is sent. Not used by apps.
  bool sendGroupMessageWatched(uint32_t timestamp, mesh::GroupChannel& channel,
                               const char* sender, const char* text, int text_len);
  uint8_t getChannelRelayStatus() const { return channel_relay_state; }
  uint32_t getChannelRelayStatusMs() const { return channel_relay_status_ms; }''', 'watched-channel public API')
    src = once(src,
        '  void logRxRaw(float snr, float rssi, const uint8_t raw[], int len) override;',
        '''  void logRxRaw(float snr, float rssi, const uint8_t raw[], int len) override;
  void logRx(mesh::Packet* packet, int len, float score) override;
  void logTx(mesh::Packet* packet, int len) override;
  void logTxFail(mesh::Packet* packet, int len) override;''', 'pre-dedup RX and completion TX hooks')
    src = once(src,
        '''  Listener* _listener;
''',
        '''  Listener* _listener;

  // RAM-only monitor of the last Quick Msg channel send. Group-message
  // payload hash remains invariant as repeaters append path hashes.
  uint8_t channel_relay_hash[MAX_HASH_SIZE] = {0};
  uint8_t channel_relay_state = CHANNEL_RELAY_NONE;
  uint32_t channel_relay_started_ms = 0;
  uint32_t channel_relay_status_ms = 0;
  void updateChannelRelayStatus(uint8_t state);
''', 'monitor fields')
    if src.count(MARKER) != 1:
        raise ValueError('header marker invariant')
    return src


CPP_INSERT = r'''// FAKETEC_UI_V053_RELAY_ECHO: passive confirmation that some radio forwarded
// this specific ciphertext packet. No custom ACK traffic or repeater firmware.
// MeshCore's packet hash excludes the evolving route path. A match with a
// nonempty path can therefore identify a returning repeater/relay transmission.
void MyMesh::updateChannelRelayStatus(uint8_t state) {
  channel_relay_state = state;
  channel_relay_status_ms = millis();
  if (_listener) _listener->onChannelRelayStatus(state);
}

bool MyMesh::sendGroupMessageWatched(uint32_t timestamp, mesh::GroupChannel& channel,
                                     const char* sender, const char* text, int text_len) {
  // Follow BaseChatMesh::sendGroupMessage's wire payload exactly. Only
  // channel messages sent from the on-device Quick Msg UI are watched.
  if (!sender || !text || text_len < 0) return false;
  size_t name_len = strlen(sender);
  if (name_len + 2 > MAX_TEXT_LEN) return false;
  size_t prefix_len = name_len + 2;
  if ((size_t)text_len > MAX_TEXT_LEN - prefix_len)
    text_len = MAX_TEXT_LEN - prefix_len;

  uint8_t data[5 + MAX_TEXT_LEN + 32];
  memcpy(data, &timestamp, 4);
  data[4] = 0; // TXT_TYPE_PLAIN
  memcpy(&data[5], sender, name_len);
  data[5 + name_len] = ':';
  data[6 + name_len] = ' ';
  memcpy(&data[5 + prefix_len], text, text_len);

  mesh::Packet* pkt = createGroupDatagram(PAYLOAD_TYPE_GRP_TXT, channel,
                                         data, 5 + prefix_len + text_len);
  if (!pkt) return false;
  pkt->calculatePacketHash(channel_relay_hash);
  channel_relay_started_ms = millis();
  updateChannelRelayStatus(CHANNEL_RELAY_QUEUED);
  sendFloodScoped(channel, pkt);
  return true;
}

void MyMesh::logTx(mesh::Packet* packet, int len) {
  // Called when radio reports that an outbound transmission completed.
  if (channel_relay_state != CHANNEL_RELAY_QUEUED ||
      packet->getPayloadType() != PAYLOAD_TYPE_GRP_TXT) return;
  uint8_t h[MAX_HASH_SIZE];
  packet->calculatePacketHash(h);
  if (memcmp(h, channel_relay_hash, MAX_HASH_SIZE) != 0) return;
  channel_relay_started_ms = millis();
  updateChannelRelayStatus(CHANNEL_RELAY_LISTENING);
}

void MyMesh::logTxFail(mesh::Packet* packet, int len) {
  if (channel_relay_state != CHANNEL_RELAY_QUEUED ||
      packet->getPayloadType() != PAYLOAD_TYPE_GRP_TXT) return;
  uint8_t h[MAX_HASH_SIZE];
  packet->calculatePacketHash(h);
  if (memcmp(h, channel_relay_hash, MAX_HASH_SIZE) == 0)
    updateChannelRelayStatus(CHANNEL_RELAY_TX_FAILED);
}

void MyMesh::logRx(mesh::Packet* packet, int len, float score) {
  // Dispatcher calls logRx BEFORE Mesh::onRecvPacket and duplicate filtering.
  // The original TX is marked seen by Mesh::sendFlood, so the ordinary
  // channel receive callback cannot observe its relayed echo reliably.
  if (channel_relay_state != CHANNEL_RELAY_LISTENING ||
      (uint32_t)(millis() - channel_relay_started_ms) > 60000UL ||
      !packet->isRouteFlood() ||
      packet->getPayloadType() != PAYLOAD_TYPE_GRP_TXT ||
      packet->getPathHashCount() == 0) return;
  uint8_t h[MAX_HASH_SIZE];
  packet->calculatePacketHash(h);
  if (memcmp(h, channel_relay_hash, MAX_HASH_SIZE) == 0)
    updateChannelRelayStatus(CHANNEL_RELAY_SEEN);
}

'''


def patch_mesh_cpp(src):
    if MARKER in src:
        return src
    src = once(src,
        'void MyMesh::logRxRaw(float snr, float rssi, const uint8_t raw[], int len) {',
        CPP_INSERT + 'void MyMesh::logRxRaw(float snr, float rssi, const uint8_t raw[], int len) {',
        'pre-dedup channel return-path monitor')
    src = once(src,
        '''void MyMesh::loop() {
  BaseChatMesh::loop();
''',
        '''void MyMesh::loop() {
  BaseChatMesh::loop();
  // Distinguish a missing echo from a failed or still-queued transmission.
  if (channel_relay_state == CHANNEL_RELAY_LISTENING &&
      (uint32_t)(millis() - channel_relay_started_ms) >= 60000UL) {
    updateChannelRelayStatus(CHANNEL_RELAY_UNCONFIRMED);
  } else if (channel_relay_state == CHANNEL_RELAY_QUEUED &&
             (uint32_t)(millis() - channel_relay_started_ms) >= 300000UL) {
    updateChannelRelayStatus(CHANNEL_RELAY_QUEUE_STALE);
  }
''', 'channel echo timeout')
    if src.count(MARKER) != 1:
        raise ValueError('MyMesh.cpp marker invariant')
    return src


def patch_ui_hdr(src):
    if MARKER in src:
        return src
    if '  void onACKRecv(uint32_t ack_crc) override;' not in src:
        raise ValueError('v0.5.1 callback missing in UITask.h')
    src = once(src,
        '  void onACKRecv(uint32_t ack_crc) override;  // FAKETEC_UI_V051_ACK_VOLTAGE',
        '''  void onACKRecv(uint32_t ack_crc) override;  // FAKETEC_UI_V051_ACK_VOLTAGE
  void onChannelRelayStatus(uint8_t status) override; // FAKETEC_UI_V053_RELAY_ECHO''',
        'UI status callback')
    if src.count(MARKER) != 1:
        raise ValueError('UITask.h marker invariant')
    return src


def patch_ui_cpp(src):
    if MARKER in src:
        return src
    if 'FAKETEC_UI_V052_ROOMS_NAV' not in src:
        raise ValueError('Must apply v0.5.2 before v0.5.3')
    src = once(src,
        '''    bool direct_is_room = false;
''',
        '''    bool direct_is_room = false;
    bool watching_channel = false;
''', 'channel send tracking')
    old = '''queued = the_mesh.sendGroupMessage(timestamp, ch.channel,
                    the_mesh.getNodeName(), message, strlen(message));'''
    n = src.count(old)
    if n != 2:
        raise ValueError(f'Quick Msg channel call count changed, expected 2, got {n}')
    src = src.replace(old,
        '''queued = the_mesh.sendGroupMessageWatched(timestamp, ch.channel,
                    the_mesh.getNodeName(), message, strlen(message));
            watching_channel = queued;''')
    src = once(src,
        '''    task->showAlert(!queued ? "Send failed" :
                    direct_expected_ack ? (direct_is_room ? "Room: await ACK" :
                                           "DM: awaiting ACK") :
                    "Queued (not delivered)", 1800);''',
        '''    task->showAlert(!queued ? "Send failed" :
                    watching_channel ? "Channel: queued" :
                    direct_expected_ack ? (direct_is_room ? "Room: await ACK" :
                                           "DM: awaiting ACK") :
                    "Queued (not delivered)", 1800);''', 'queued is not an ACK')
    src = once(src,
        '''          snprintf(tmp, sizeof(tmp), "BLE:ON");
        }
      }
      display.print(tmp);''',
        '''          snprintf(tmp, sizeof(tmp), "BLE:ON");
        }
      }
      // FAKETEC_UI_V053_RELAY_ECHO: short, persistent home-screen TX status.
      // Preserve PIN when disconnected. Replaces transient SNR footer only;
      // Link Check still shows two-way SNR on its dedicated results screen.
      const uint8_t txstate = the_mesh.getChannelRelayStatus();
      if (txstate != MyMesh::CHANNEL_RELAY_NONE &&
          (uint32_t)(millis() - the_mesh.getChannelRelayStatusMs()) < 120000UL) {
        const char* txlabel = NULL;
        switch (txstate) {
          case MyMesh::CHANNEL_RELAY_QUEUED: txlabel = "Q"; break;
          case MyMesh::CHANNEL_RELAY_LISTENING: txlabel = "WAIT"; break;
          case MyMesh::CHANNEL_RELAY_SEEN: txlabel = "RELAY"; break;
          case MyMesh::CHANNEL_RELAY_UNCONFIRMED: txlabel = "NOECHO"; break;
          case MyMesh::CHANNEL_RELAY_TX_FAILED: txlabel = "FAIL"; break;
          case MyMesh::CHANNEL_RELAY_QUEUE_STALE: txlabel = "TX?"; break;
          default: break;
        }
        if (txlabel) {
          if (!_task->hasConnection() && the_mesh.getBLEPin())
            snprintf(tmp, sizeof(tmp), "PIN:%06lu TX:%s",
                     (unsigned long)the_mesh.getBLEPin(), txlabel);
          else
            snprintf(tmp, sizeof(tmp), "BLE:%s TX:%s",
                     _task->hasConnection() ? "ON" : "OFF", txlabel);
        }
      }
      display.print(tmp);''', 'home status beside BLE or PIN')
    src = once(src,
        '''void UITask::onQueueSizeChanged(int msgcount) {''',
        '''void UITask::onChannelRelayStatus(uint8_t state) {
  // Reception of our forwarded packet proves an on-air retransmission,
  // not receipt by any subscriber. Timeouts are deliberately unconfirmed.
  if (state == MyMesh::CHANNEL_RELAY_LISTENING)
    showAlert("CH sent; listening", 1500);
  else if (state == MyMesh::CHANNEL_RELAY_SEEN)
    showAlert("RELAY SEEN", 3500);
  else if (state == MyMesh::CHANNEL_RELAY_UNCONFIRMED)
    showAlert("No echo: unconfirmed", 2400);
  else if (state == MyMesh::CHANNEL_RELAY_TX_FAILED)
    showAlert("Channel TX failed", 2400);
  else if (state == MyMesh::CHANNEL_RELAY_QUEUE_STALE)
    showAlert("Channel TX unknown", 2400);
}

void UITask::onQueueSizeChanged(int msgcount) {''', 'OLED async relay status callback')
    if src.count(MARKER) != 1:
        raise ValueError('UITask.cpp marker invariant')
    return src


def atomic_save(path, txt):
    fd, tmp = tempfile.mkstemp(prefix='.faketec.v053.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            f.write(txt)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path,
                        default=Path.home() / 'faketec-ui' / 'MeshCore')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    root = args.source_root
    files = [
        (root / 'examples/companion_radio/MyMesh.h', patch_hdr),
        (root / 'examples/companion_radio/MyMesh.cpp', patch_mesh_cpp),
        (root / 'examples/companion_radio/ui-new/UITask.h', patch_ui_hdr),
        (root / 'examples/companion_radio/ui-new/UITask.cpp', patch_ui_cpp),
    ]
    changes = []
    try:
        for path, patch in files:
            old = path.read_text(encoding='utf-8')
            new = patch(old)
            changes.append((path, old, new))
    except (OSError, ValueError) as e:
        parser.error('No source was modified: ' + str(e))
    if args.check:
        print('Dry-run OK: exact channel packet fingerprint, pre-dedup echo, 60-second window')
        return
    for path, old, new in changes:
        if new == old:
            continue
        backup = path.with_suffix(path.suffix + '.v052-before-relay-watch')
        if not backup.exists():
            shutil.copy2(path, backup)
        atomic_save(path, new)
        print('Updated', path)
    print('FakeTec v0.5.3 relay watcher applied. Device not flashed.')


if __name__ == '__main__':
    main()
