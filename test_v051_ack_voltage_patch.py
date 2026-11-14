"""Offline regression for v0.5.1 voltage and DM-ACK follow-on (no compiling)."""
import importlib.util
import runpy
from pathlib import Path
HERE=Path(__file__).resolve().parent
base=runpy.run_path(str(HERE / 'test_v051_patch.py'))['patched']
spec=importlib.util.spec_from_file_location('ackvolt', HERE/'faketec_ui_v0_5_1_ack_voltage_patch.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
# Minimal stock UI snippets absent from the prior synthetic patch fixture.
base=base.replace('class HomeScreen : public UIScreen {', '''class HomeScreen : public UIScreen {
  void renderBatteryIndicator(DisplayDriver& display, uint16_t batteryMilliVolts) {
    int iconX = 0, iconY = 0, iconWidth = 24, iconHeight = 10;
    display.drawRect(iconX, iconY, iconWidth, iconHeight);
    display.fillRect(1,1,10,4);
  }
  CayenneLPP sensors_lpp;''',1)
base=base.replace('  int render(DisplayDriver& display) override {', '''  int render(DisplayDriver& display) override {
    display.setCursor(0, 2);
    display.print(filtered_name);''',1)
base+= '''
class MsgPreviewScreen : public UIScreen {
  int render(DisplayDriver& display) override {
    char tmp[16];
    display.setCursor(display.width() - display.getTextWidth(tmp) - 2, 0);
    display.print(tmp);

    display.drawRect(0, 11, display.width(), 1);
    return 1000;
  }
};
void UITask::onQueueSizeChanged(int msgcount) {}
'''
head='''class UITask {\n  void onQueueSizeChanged(int offline_queue_size) override;\n};\n'''
patched=m.patch_cpp(base)
h=m.patch_header(head)
assert m.patch_cpp(patched)==patched and m.patch_header(h)==h
assert patched.count(m.MARKER)==1
assert 'display.drawRect(iconX, iconY, iconWidth, iconHeight)' not in patched
assert 'display.print(voltage)' in patched
assert 'display.drawTextEllipsized(0, 2, display.width() - 54, filtered_name)' in patched
assert 'preview_voltage' in patched and 'void renderVoltage(DisplayDriver& display) const' in patched
assert 'renderVoltage(display); // every Quick Msg screen' in patched
assert 'DM: awaiting ACK' in patched and 'DM ACK received' in patched
assert 'pending_dm_ack[4]' in patched and 'direct_expected_ack = expected_ack' in patched
assert 'void UITask::onACKRecv(uint32_t ack_crc)' in patched
assert 'void onACKRecv(uint32_t ack_crc) override;' in h
assert '"PIN:%06lu BLE:OFF"' in patched and '"BLE:WAIT"' in patched
assert '"BLE:ON"' in patched
assert '"PIN:%06lu B:%.2fV"' not in patched
assert 'confirm_choice == 0 ? "> SEND"' in patched
assert 'std::' not in patched, 'unexpected C++ runtime dependency'
try:
    m.patch_cpp(base.replace('display.drawRect(iconX, iconY, iconWidth, iconHeight)','otherIcon()'))
    raise AssertionError('layout drift was accepted')
except ValueError: pass
try:
    m.patch_cpp(base.replace('direct_expected_ack', 'bad_crc'))
except ValueError: pass
print('PASS: ACK matching + all-screen voltage patch, idempotence, guarded anchors, fixed confirmation')
