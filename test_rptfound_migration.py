#!/usr/bin/env python3
from pathlib import Path
import subprocess
import tempfile

p = Path(__file__).with_name('faketec_v051_rptfound_migrate.py')
old = """// FAKETEC_UI_V051_UX
    display.print("REPLY: not checked");
    snprintf(tmp, sizeof(tmp), "REPLY:%u (stale)", replies);
    snprintf(tmp, sizeof(tmp), "REPLY:%u %lum ago", replies,
    display.print("REPLY: unavailable");
"""
with tempfile.TemporaryDirectory() as td:
    src = Path(td)/'UITask.cpp'
    src.write_text(old)
    subprocess.run(['python3', str(p), str(src)], check=True)
    expected = src.read_text()
    assert 'REPLY:' not in expected and expected.count('RPT FOUND:') == 4
    subprocess.run(['python3', str(p), str(src)], check=True)
    assert expected == src.read_text()
print('PASS: repair existing REPLY strings, idempotent migration')
