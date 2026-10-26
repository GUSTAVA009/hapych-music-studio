"""Build QA42 mastering from verified QA39 path with explicit safe replacements."""
from pathlib import Path
import py_compile
ROOT=Path.home()/"Music Studio"/"app"
s=(ROOT/"qa39_finish_export.py").read_text(encoding="utf-8")
edits=[
 ('D=ROOT/"Diagnostics"/"QA39"','D=ROOT/"Diagnostics"/"QA42"'),
 ('req=json.loads((ROOT/"Diagnostics"/"QA38"/"request.json").read_text(encoding="utf-8"))',
  'req=json.loads((D/"QA42_sung_request.json").read_text(encoding="utf-8"))["song"]'),
 ('source=D/"QA39_TURBO_corrected_same_seed.wav"','source=D/"QA42_SungSource_160s_same_seed.wav"'),
 ('record=json.loads((D/"turbo_fixed_result.json").read_text(encoding="utf-8"))',
  'record=json.loads((D/"QA42_sung_result.json").read_text(encoding="utf-8"))'),
 ('assert record["steps"]==8','assert record["DiT_steps"]==8'),
 ('text=record.get("sft_lrc","")','text=""'),
 ('QA39_','QA42_'),
]
for before,after in edits:
 count=s.count(before)
 if not count:raise RuntimeError("Missing source anchor: "+before)
 s=s.replace(before,after)
# Replaces all QA39_ file names; reports are isolated in the QA42 diagnostics folder.
p=ROOT/"qa42_master.py"
p.write_text(s,encoding="utf-8")
py_compile.compile(str(p),doraise=True)
print("QA42_MASTER_SCRIPT_READY",p)
