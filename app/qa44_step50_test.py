"""QA44 early checkpoint 50 step holdout sample comparison.
No retraining/deployment; inspect overfit at 100 steps against heldout mic.
"""
from pathlib import Path
import subprocess,time,json,sys,py_compile
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA44"
base=R/"Voice Engine"/"convert_track_studio44.py"
early=R/"Voice Engine"/"convert_track_studio44_early.py"
orig=base.read_text(encoding="utf-8")
before="checkpoint=folder/'ft_model.pth'"
after="checkpoint=folder/'DiT_epoch_00004_step_00050.pth'"
assert orig.count(before)==1
early.write_text(orig.replace(before,after),encoding="utf-8")
py_compile.compile(str(early),doraise=True)
ref=next((R/"Мой голос").glob("*65f5f3.wav"))
src=R/"Diagnostics"/"QA43"/"QA43_QA42_SUNG_SOURCE_35to75.wav"
out=D/"QA44_step50_holdout_40s.mp3"
exe=R/"Voice Engine"/".venv"/"Scripts"/"python.exe"
cmd=[str(exe),"-u",str(early),"--source",str(src),"--voice",str(ref),
 "--output",str(out),"--steps","40","--trained","--register","original",
 "--language","ru","--keep-dry"]
started=time.monotonic()
p=subprocess.run(cmd,capture_output=True,text=True,timeout=1600)
(D/"qa44_step50_holdout_stdout.log").write_text(p.stdout,encoding="utf-8")
(D/"qa44_step50_holdout_stderr.log").write_text(p.stderr,encoding="utf-8")
r={"checkpoint":"QA44 50 steps","exit":p.returncode,"file":str(out),
   "elapsed":round(time.monotonic()-started,1),"deployed":False}
if out.is_file():
 q=out.with_suffix(".quality.json")
 if q.exists():
  j=json.loads(q.read_text(encoding="utf-8"))
  r.update(speaker_cosine=j.get("speaker_embedding_cosine"),
     lost_fraction=j.get("voice_check",{}).get("metrics",{}).get("relative_missing_vocal_frames"),
     dips=j.get("voice_check",{}).get("metrics",{}).get("energy_dip_events"),
     pitch=j.get("pitch_consistency",{}).get("status"))
(D/"qa44_step50_holdout_result.json").write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA44_EARLY_HOLDOUT",json.dumps(r,ensure_ascii=True),flush=True)
if p.returncode:sys.exit(p.returncode)
