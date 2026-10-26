"""QA45 personal timbre comparison on new neo-soul verse, isolated 35 seconds.
Only experimental; full source song stays untouched.
"""
from pathlib import Path
import subprocess,sys,json,time,requests
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA45"
source=D/"QA45_NeoSoul_source.wav"
ref=next((R/"Мой голос").glob("*3867cb.wav"))
assert source.exists() and ref.exists()
c=subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-ss","18","-i",str(source),"-t","35",
 "-ar","44100","-ac","2","-c:a","pcm_s24le",str(D/"QA45_verse18to53.wav")],
 capture_output=True,text=True,timeout=90)
assert c.returncode==0,c.stderr
py=R/"Voice Engine"/".venv"/"Scripts"/"python.exe"
script=R/"Voice Engine"/"convert_track_studio44.py"
output=D/"QA45_MyVoice_QA44_35s.mp3"
s=requests.Session();s.trust_env=False
health=s.get("http://127.0.0.1:7870/api/health",timeout=9).json()
assert health["job"]["status"] not in ("generating","preparing","converting")
cmd=[str(py),"-u",str(script),"--source",str(D/"QA45_verse18to53.wav"),
 "--voice",str(ref),"--output",str(output),"--steps","40","--trained",
 "--register","original","--language","ru","--keep-dry"]
beg=time.monotonic()
p=subprocess.run(cmd,capture_output=True,text=True,timeout=1400)
(D/"qa45_personal_stdout.log").write_text(p.stdout,encoding="utf-8")
(D/"qa45_personal_stderr.log").write_text(p.stderr,encoding="utf-8")
r={"exit":p.returncode,"duration_source_s":35,"model":"QA44 clean-only fine-tuned",
 "audio":str(output),"deployed":False,"elapsed_seconds":round(time.monotonic()-beg,2)}
if output.exists():
 q=output.with_suffix(".quality.json")
 if q.exists():
  o=json.loads(q.read_text(encoding="utf-8"))
  r.update(speaker_similarity_proxy=o.get("speaker_embedding_cosine"),
   voice_check=o.get("voice_check",{}).get("status"),
   pitch=o.get("pitch_consistency",{}).get("status"),
   dips=o.get("voice_check",{}).get("metrics",{}).get("energy_dip_events"),
   loss=o.get("voice_check",{}).get("metrics",{}).get("relative_missing_vocal_frames"))
(D/"qa45_personal_report.json").write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA45_PERSONAL_RESULT",json.dumps(r,ensure_ascii=True),flush=True)
if p.returncode:print("ERROR",p.stderr[-1200:],flush=True);sys.exit(p.returncode)
