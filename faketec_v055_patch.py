from pathlib import Path
import sys

root = Path(sys.argv[1]).expanduser().resolve()
folder = root / "examples/companion_radio"

hp = folder / "MyMesh.h"
cp = folder / "MyMesh.cpp"
pp = folder / "NodePrefs.h"
up = folder / "ui-new/UITask.cpp"

h = hp.read_text()
c = cp.read_text()
p = pp.read_text()
u = up.read_text()

def replace_once(s, old, new):
    if s.count(old) != 1:
        raise RuntimeError("Unexpected source pattern: " + old)
    return s.replace(old, new, 1)

if "FAKETEC_RELAY_PERSIST_V055" in c:
    raise RuntimeError("Persistence patch already applied")

if "CUSTOM_RELAY_CLI_V1" in c:
    raise RuntimeError("Use the original v0.5.4 source without CLI patch")

if "_ad_hoc_relay_enabled" not in h:
    raise RuntimeError("v0.5.4 relay source required")

# Add persistent preferences.
p = replace_once(
    p,
    "  RepeatPrefs repeat;",
    """  RepeatPrefs repeat;

public:
  uint8_t adhoc_relay_remember = 0;
  uint8_t adhoc_relay_last = 0;
private:
"""
)

p = replace_once(
    p,
    '    def("repeat", repeat);',
    '''    def("repeat", repeat);
    def("adhoc_remember", adhoc_relay_remember);
    def("adhoc_last", adhoc_relay_last);'''
)

# Replace the RAM-only relay setter.
h = replace_once(
    h,
    "  void setAdHocRelayEnabled(bool enabled) { _ad_hoc_relay_enabled = enabled; }",
    """  bool setAdHocRelayEnabled(bool enabled);
  bool setAdHocRelayRemember(bool enabled);

  bool isAdHocRelayRemembered() const {
    return _prefs.adhoc_relay_remember == 1;
  }
"""
)

# Restore the relay state after loading preferences.
c = replace_once(
    c,
    "  _store->loadPrefs(_prefs);",
    """  _store->loadPrefs(_prefs);

  _ad_hoc_relay_enabled =
      _prefs.adhoc_relay_remember == 1 &&
      _prefs.adhoc_relay_last == 1;
"""
)

# Shared relay setter used by OLED and CLI.
anchor = "bool MyMesh::allowPacketForward("

methods = """
// FAKETEC_RELAY_PERSIST_V055

bool MyMesh::setAdHocRelayEnabled(bool enabled) {
  if (isAdHocRelayRemembered()) {
    uint8_t next = enabled ? 1 : 0;

    if (_prefs.adhoc_relay_last != next) {
      uint8_t old = _prefs.adhoc_relay_last;
      _prefs.adhoc_relay_last = next;

      if (!_store->savePrefs(_prefs)) {
        _prefs.adhoc_relay_last = old;
        return false;
      }
    }
  }

  _ad_hoc_relay_enabled = enabled;
  return true;
}

bool MyMesh::setAdHocRelayRemember(bool enabled) {
  uint8_t old_policy = _prefs.adhoc_relay_remember;
  uint8_t old_state = _prefs.adhoc_relay_last;

  uint8_t next_policy = enabled ? 1 : 0;
  uint8_t next_state =
      enabled && _ad_hoc_relay_enabled ? 1 : 0;

  if (old_policy == next_policy &&
      old_state == next_state) {
    return true;
  }

  _prefs.adhoc_relay_remember = next_policy;
  _prefs.adhoc_relay_last = next_state;

  if (!_store->savePrefs(_prefs)) {
    _prefs.adhoc_relay_remember = old_policy;
    _prefs.adhoc_relay_last = old_state;
    return false;
  }

  return true;
}

"""

c = replace_once(c, anchor, methods + anchor)

# Prevent relay control through remote LoRa commands.
remote_anchor = \
    "    if (!handleCommand(text, sender_timestamp, reply)) {"

remote_guard = """
    const char* cmd = text;
    while (*cmd == ' ') cmd++;

    if (strlen(cmd) > 4 && cmd[2] == '|') {
      cmd += 3;
    }

    if (strncmp(cmd, "get relay", 9) == 0 ||
        strncmp(cmd, "set relay", 9) == 0) {
      strcpy(reply, "Error: local CLI only");
      return;
    }

"""

c = replace_once(
    c, remote_anchor, remote_guard + remote_anchor
)

# Companion CLI commands.
anchor = "  if (_prefs.getRadioPrefs()->handleCommand("

cli = """
  if (strcmp(command, "get relay") == 0 ||
      strcmp(command, "get relay.boot") == 0 ||
      strncmp(command, "set relay ", 10) == 0 ||
      strncmp(command, "set relay.boot ", 15) == 0) {

    if (sender_timestamp != 0) {
      strcpy(reply, "Error: local CLI only");
      return true;
    }

    bool ok = true;

    if (strcmp(command, "set relay on") == 0) {
      ok = setAdHocRelayEnabled(true);

    } else if (strcmp(command, "set relay off") == 0) {
      ok = setAdHocRelayEnabled(false);

    } else if (strcmp(command, "set relay.boot last") == 0) {
      ok = setAdHocRelayRemember(true);

    } else if (strcmp(command, "set relay.boot off") == 0) {
      ok = setAdHocRelayRemember(false);

    } else if (strcmp(command, "get relay") != 0 &&
               strcmp(command, "get relay.boot") != 0) {

      strcpy(reply, "Usage: relay on/off; relay.boot off/last");
      return true;
    }

    if (!ok) {
      strcpy(reply, "Error: preference save failed");
      return true;
    }

    sprintf(reply, "> relay %s; boot %s; off-grid %s",
        isAdHocRelayEnabled() ? "ON" : "OFF",
        isAdHocRelayRemembered() ? "LAST" : "OFF",
        _prefs.isRepeatEn() ? "ON" : "OFF");

    return true;
  }

"""

c = replace_once(c, anchor, cli + anchor)

# Make the existing OLED relay toggle handle save errors.
u = replace_once(
    u,
    '''          the_mesh.setAdHocRelayEnabled(enabled);
          _task->showAlert(enabled ? "Ad hoc relay ON" : "Ad hoc relay OFF", 1200);''',
    '''          if (the_mesh.setAdHocRelayEnabled(enabled)) {
            _task->showAlert(enabled ? "Ad hoc relay ON" : "Ad hoc relay OFF", 1200);
          } else {
            _task->showAlert("Relay save failed", 1200);
          }'''
)

# Write only after all source checks pass.
hp.write_text(h)
cp.write_text(c)
pp.write_text(p)
up.write_text(u)

print("SUCCESS: FakeTec v0.5.5 patch applied.")
print("CLI relay control: enabled")
print("Persistent startup policy: enabled")
print("Default startup policy: OFF")
print("Remote LoRa relay control: blocked")
