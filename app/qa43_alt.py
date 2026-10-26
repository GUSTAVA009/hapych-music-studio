"""QA43 reference crosscheck with longer alternate clean mic. Same QA42 source excerpt,
same diffusion steps and seed. Diagnostics only; no auto-promotion.
"""
from pathlib import Path
import subprocess,json,time,sys
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA43"
src=D/"QA43_QA42_SUNG_SOURCE_35to75.wav"
ref=next((R/"Мой голос").glob("*3867cb.wav"))
assert src.is_file() and ref.is_file()
out=D/"QA43_MyVoice_AltRef_22s_40steps.mp3"
exe=R/"Voice Engine"/".venv"/"Scripts"/"python.exe"
call=[str(exe),"-u",str(R/"Voice Engine"/"convert_track_studio40.py"),
      "--source",str(src),"--voice",str(ref),"--output",str(out),
      "--steps","40","--register","original","--language","ru","--keep-dry"]
now=time.monotonic()
p=subprocess.run(call,capture_output=True,text=True,timeout=1500)
(D/"QA43_alt_stdout.log").write_text(p.stdout,encoding="utf-8")
(D/"QA43_alt_stderr.log").write_text(p.stderr,encoding="utf-8")
report={"exit":p.returncode,"duration_seconds":round(time.monotonic()-now,1),
        "reference":ref.name,"output":str(out),"base_model":True}
if out.is_file():
 report["bytes"]=out.stat().st_size
 q=out.with_suffix(".quality.json")
 if q.exists():
  t=json.loads(q.read_text(encoding="utf-8"))
  report.update({"voice_checker":t.get("voice_check",{}).get("status"),
    "voice_metrics":t.get("voice_check",{}).get("metrics"),
    "cosine":t.get("speaker_embedding_cosine"),
    "pitch_check":t.get("pitch_consistency",{}).get("status")})
(D/"QA43_alt_run.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("ALT_REF_RUN",json.dumps(report,ensure_ascii=True),flush=True)
if p.returncode:print("FAILED",p.stderr[-900:],flush=True);sys.exit(p.returncode)
