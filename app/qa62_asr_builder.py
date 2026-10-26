"""Reuse exact QA59 Whisper test without changing tokenization/window metrics."""
from pathlib import Path
import py_compile
R=Path.home()/"Music Studio"
source=R/"app"/"qa59_asr.py"
text=source.read_text(encoding="utf-8")
old='''runs=json.loads((D/"qa59_inference_results.json").read_text(encoding="utf-8"))
paths={"source_ACE":Q/"QA54_CFG090_35s.source.wav","prior_QA54":Q/"QA54_CFG090_35s.dry.wav"}
for q in runs:
 if q.get("exit_code")==0 and q.get("audio"):
  paths["new_"+q["tag"]]=Path(q["audio"])
assert len(paths)>=3,paths'''
new='''paths={
 "source_ACE":Q/"QA54_CFG090_35s.source.wav",
 "prior_QA54":Q/"QA54_CFG090_35s.dry.wav",
 "OpenVoice_tau010":D/"QA62_OpenVoice_t01_raw.wav",
 "OpenVoice_tau030":D/"QA62_OpenVoice_t03_raw.wav"}
assert all(p.is_file() for p in paths.values())'''
assert text.count(old)==1
text=text.replace(old,new)
assert text.count('D=R/"Diagnostics"/"QA59"')==1
text=text.replace('D=R/"Diagnostics"/"QA59"','D=R/"Diagnostics"/"QA62"')
text=text.replace('qa59_asr_compare.json','qa62_asr_compare.json')
text=text.replace('QA59_ASR','QA62_ASR').replace('QA59_SCORES','QA62_SCORES')
dest=R/"app"/"qa62_asr.py"
dest.write_text(text,encoding="utf-8")
py_compile.compile(str(dest),doraise=True)
print("QA62_ASR_SCRIPT_READY",str(dest))
