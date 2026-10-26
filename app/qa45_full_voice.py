"""QA45 full soft vocal rendition, separate diagnostics; preserves original source."""
from pathlib import Path
import subprocess,json,time,sys,requests
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA45"
src=D/"QA45_NeoSoul_source.wav";ref=next((R/"Мой голос").glob("*3867cb.wav"))
out=D/"QA45_Tam_Gde_Teplo_MyVoice_Full.mp3"
assert src.is_file() and ref.is_file()
s=requests.Session();s.trust_env=False
h=s.get("http://127.0.0.1:7870/api/health",timeout=8).json()
assert h["job"]["status"] not in ("generating","preparing","converting")
args=[str(R/"Voice Engine"/".venv"/"Scripts"/"python.exe"),"-u",
 str(R/"Voice Engine"/"convert_track_studio44.py"),
 "--source",str(src),"--voice",str(ref),"--output",str(out),
 "--steps","40","--trained","--register","original","--language","ru"]
beg=time.monotonic()
p=subprocess.run(args,capture_output=True,text=True,timeout=1700)
(D/"qa45_full_voice_stdout.log").write_text(p.stdout,encoding="utf-8")
(D/"qa45_full_voice_stderr.log").write_text(p.stderr,encoding="utf-8")
r={"exit":p.returncode,"song":"Там, где тепло","original_untouched":True,"not_deployed":True,
 "model":"QA44 clean-only trained","audio":str(out),"duration":167,"elapsed":round(time.monotonic()-beg,1)}
if out.exists():
 q=out.with_suffix(".quality.json")
 if q.exists():
  j=json.loads(q.read_text(encoding="utf-8"))
  r["speaker_proxy"]=j.get("speaker_embedding_cosine")
  r["pitch_check"]=j.get("pitch_consistency",{}).get("status")
  r["guard_accepted"]=j.get("voice_check",{}).get("accepted")
  r["vocal_metrics"]=j.get("voice_check",{}).get("metrics")
(D/"qa45_full_voice_report.json").write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA45_FULL_PERSONAL_RESULT",json.dumps(r,ensure_ascii=True),flush=True)
if p.returncode:print("QA45_ERROR",p.stderr[-1200:],flush=True);sys.exit(p.returncode)
