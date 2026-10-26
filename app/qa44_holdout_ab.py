"""QA44 independent reference holdout AB check.
No interaction with base user's model; no dataset modifications.
"""
import json,time,subprocess,sys
from pathlib import Path
ROOT=Path.home()/"Music Studio";D=ROOT/"Diagnostics"/"QA44"
manifest=json.loads((D/"qa44_v2_manifest.json").read_text(encoding="utf-8"))
hold=next(x for x in manifest["samples"] if x["role"]=="holdout")
ref=ROOT/"Мой голос"/hold["original"]
assert ref.is_file() and ref.name.endswith("65f5f3.wav")
source=ROOT/"Diagnostics"/"QA43"/"QA43_QA42_SUNG_SOURCE_35to75.wav"
exe=ROOT/"Voice Engine"/".venv"/"Scripts"/"python.exe"
for name,script,trained in [
 ("base_holdout",ROOT/"Voice Engine"/"convert_track_studio40.py",False),
 ("tuned_holdout",ROOT/"Voice Engine"/"convert_track_studio44.py",True)]:
 target=D/("QA44_"+name+"_40s.mp3")
 cmd=[str(exe),"-u",str(script),"--source",str(source),"--voice",str(ref),
      "--output",str(target),"--steps","40","--register","original",
      "--language","ru","--keep-dry"]
 if trained:cmd.append("--trained")
 started=time.monotonic()
 p=subprocess.run(cmd,capture_output=True,text=True,timeout=1600)
 (D/(name+"_stdout.log")).write_text(p.stdout,encoding="utf-8")
 (D/(name+"_stderr.log")).write_text(p.stderr,encoding="utf-8")
 record={"variant":name,"exit_code":p.returncode,"holdout_recording":ref.name,
  "matched_audio_source":str(source),"elapsed_seconds":round(time.monotonic()-started,1),
  "file":str(target),"deployed":False}
 if target.exists():
  rpt=target.with_suffix(".quality.json")
  if rpt.exists():
   q=json.loads(rpt.read_text(encoding="utf-8"))
   record.update(cosine=q.get("speaker_embedding_cosine"),
     pitch=q.get("pitch_consistency",{}).get("status"),
     dips=q.get("voice_check",{}).get("metrics",{}).get("energy_dip_events"),
     frame_loss=q.get("voice_check",{}).get("metrics",{}).get("relative_missing_vocal_frames"))
 (D/(name+"_run.json")).write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
 print("QA44_HOLDOUT",json.dumps(record,ensure_ascii=True),flush=True)
 if p.returncode:sys.exit(p.returncode)
