#!/usr/bin/env python3
"""Host-side C++ compilation of the actual v0.5.3 relay callback functions.
Uses mock mesh Packet/radio callbacks, not the actual nRF52840 toolchain.
"""
import runpy
import subprocess
import tempfile
from pathlib import Path

h = Path(__file__).resolve().parent
insert = runpy.run_path(str(h / 'faketec_ui_v0_5_3_channel_relay_patch.py'))['CPP_INSERT']
pre = r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#define MAX_TEXT_LEN 160
#define MAX_HASH_SIZE 8
#define PAYLOAD_TYPE_GRP_TXT 5
static uint32_t test_now = 1000;
uint32_t millis() { return test_now; }
namespace mesh {
struct GroupChannel {};
struct Packet {
  uint8_t type = PAYLOAD_TYPE_GRP_TXT;
  uint8_t path_count = 0;
  bool flood = true;
  uint8_t bytes[256] = {0};
  size_t len = 0;
  uint8_t getPayloadType() const { return type; }
  bool isRouteFlood() const { return flood; }
  uint8_t getPathHashCount() const { return path_count; }
  void calculatePacketHash(uint8_t* out) const {
    for(int i=0;i<MAX_HASH_SIZE;i++) {
      uint32_t a = 5381U+i;
      a = a*33U+type;
      for(size_t j=0;j<len;j++) a = (a*33U) ^ bytes[j];
      out[i] = (a >> ((i%4)*8)) & 0xff;
    }
  }
};
}
class MyMesh {
public:
  enum ChannelRelayStatus : uint8_t {
    CHANNEL_RELAY_NONE, CHANNEL_RELAY_QUEUED, CHANNEL_RELAY_LISTENING,
    CHANNEL_RELAY_SEEN, CHANNEL_RELAY_UNCONFIRMED,
    CHANNEL_RELAY_TX_FAILED, CHANNEL_RELAY_QUEUE_STALE
  };
  struct Listener {
    virtual ~Listener() {}
    virtual void onChannelRelayStatus(uint8_t state) = 0;
  };
  Listener* _listener = nullptr;
  uint8_t channel_relay_hash[MAX_HASH_SIZE] = {0};
  uint8_t channel_relay_state = CHANNEL_RELAY_NONE;
  uint32_t channel_relay_started_ms = 0;
  uint32_t channel_relay_status_ms = 0;
  mesh::Packet packet;
  bool packet_exists = false;
  mesh::Packet* createGroupDatagram(uint8_t type, const mesh::GroupChannel&,const uint8_t* data, size_t len) {
    assert(len <= sizeof(packet.bytes));
    packet_exists = true;
    packet = mesh::Packet();
    packet.type = type;
    packet.len = len;
    memcpy(packet.bytes, data, len);
    return &packet;
  }
  void sendFloodScoped(const mesh::GroupChannel&,mesh::Packet*,uint32_t delay_ms=0) {(void)delay_ms;}
  void updateChannelRelayStatus(uint8_t state);
  bool sendGroupMessageWatched(uint32_t,mesh::GroupChannel&,const char*,const char*,int);
  void logTx(mesh::Packet*, int);
  void logTxFail(mesh::Packet*, int);
  void logRx(mesh::Packet*, int,float);
};
'''
post = r'''
struct Logger : MyMesh::Listener {
  uint8_t last=0;
  int calls=0;
  void onChannelRelayStatus(uint8_t s) override {last=s;calls++;}
};
int main(){
  MyMesh m;
  Logger logger;
  m._listener=&logger;
  mesh::GroupChannel ch;
  assert(m.sendGroupMessageWatched(123456,ch,"DV2XXR","I'm safe",8));
  assert(m.channel_relay_state==MyMesh::CHANNEL_RELAY_QUEUED);
  auto p=m.packet;
  auto relay=p;
  relay.path_count=1;
  m.logRx(&relay,0,1.0f); // before own TX completion: NOT evidence
  assert(m.channel_relay_state==MyMesh::CHANNEL_RELAY_QUEUED);
  m.logTx(&p,0);
  assert(m.channel_relay_state==MyMesh::CHANNEL_RELAY_LISTENING);
  auto wrong=relay;
  wrong.bytes[8]^=0x55;
  m.logRx(&wrong,0,1.0f); // unrelated packet must not match
  assert(m.channel_relay_state==MyMesh::CHANNEL_RELAY_LISTENING);
  relay.path_count=0;
  m.logRx(&relay,0,1.0f); // no relay path, cannot count
  assert(m.channel_relay_state==MyMesh::CHANNEL_RELAY_LISTENING);
  relay.path_count=1;
  m.logRx(&relay,0,1.0f);
  assert(m.channel_relay_state==MyMesh::CHANNEL_RELAY_SEEN);
  assert(logger.last==MyMesh::CHANNEL_RELAY_SEEN);
  int calls=logger.calls;
  m.logRx(&relay,0,1.0f);
  assert(logger.calls==calls); // one notification only
  assert(m.sendGroupMessageWatched(123458,ch,"DV2XXR","OK",2));
  m.logTxFail(&m.packet,0);
  assert(m.channel_relay_state==MyMesh::CHANNEL_RELAY_TX_FAILED);
  assert(m.sendGroupMessageWatched(123459,ch,"DV2XXR","OK",2));
  m.logTx(&m.packet,0);
  test_now+=61000;
  relay=m.packet;
  relay.path_count=2;
  m.logRx(&relay,0,1.0f);
  assert(m.channel_relay_state==MyMesh::CHANNEL_RELAY_LISTENING); // stale echo ignored
  assert(m.sendGroupMessageWatched(123460,ch,"DV2XXR","Yes",3));
  m.logTx(&m.packet,0);
  test_now+=5000;
  relay=m.packet;
  relay.path_count=2;
  relay.flood=false;
  m.logRx(&relay,0,1.0f);
  assert(m.channel_relay_state==MyMesh::CHANNEL_RELAY_LISTENING); // non-flood ignored
  puts("PASS: host C++ relay states, exact packet echo, path requirement, time limit, failure, no duplicate alert");
}
'''
with tempfile.TemporaryDirectory() as d:
    root=Path(d)
    cpp=root/'relay_watch_test.cpp'
    exe=root/'relay_watch_test'
    cpp.write_text(pre+'\n'+insert+'\n'+post)
    subprocess.run(['g++','-std=c++11','-Wall','-Wextra','-Wno-unused-parameter',str(cpp),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
