#!/usr/bin/env python3
# Upgrade existing v0.5.1-patched MeshCore trees from REPLY to RPT FOUND.
# Safe to rerun. Does not flash firmware.
from pathlib import Path
import sys, shutil, datetime
p = Path(sys.argv[1]); s = p.read_text(encoding='utf-8')
if 'FAKETEC_UI_V051_UX' not in s:
    sys.exit('ERROR: This source is not the expected FakeTec UI v0.5.1 build. No changes made.')
old = {
    'display.print("REPLY: not checked");': 'display.print("RPT FOUND:--");',
    'snprintf(tmp, sizeof(tmp), "REPLY:%u (stale)", replies);': 'snprintf(tmp, sizeof(tmp), "RPT FOUND:%u old", replies);',
    'snprintf(tmp, sizeof(tmp), "REPLY:%u %lum ago", replies,': 'snprintf(tmp, sizeof(tmp), "RPT FOUND:%u %lum", replies,',
    'display.print("REPLY: unavailable");': 'display.print("RPT FOUND:N/A");',
}
new_count = s.count('RPT FOUND:')
legacy_count = s.count('"REPLY:')
if legacy_count:
    if legacy_count != len(old) or any(s.count(k)!=1 for k in old):
        sys.exit('ERROR: Unexpected REPLY labels; source may differ. No changes made.')
    if new_count:
        sys.exit('ERROR: Mixed old/new dashboard labels; no changes made.')
    out=s
    for a,b in old.items(): out=out.replace(a,b,1)
    if '"REPLY:' in out or out.count('RPT FOUND:') != 4:
        sys.exit('ERROR: Label replacement validation failed. No changes made.')
    bk=p.with_name(p.name + '.before-rptfound-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    shutil.copy2(p,bk)
    p.write_text(out,encoding='utf-8')
    print('Updated home-screen label to RPT FOUND (4 display cases).')
    print('Source backup:',bk)
elif new_count==4:
    print('Home-screen label already says RPT FOUND. Recompiling.')
else:
    sys.exit('ERROR: Neither known REPLY nor RPT FOUND dashboard found. No changes made.')
