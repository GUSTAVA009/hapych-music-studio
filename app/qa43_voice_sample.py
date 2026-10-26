"""QA43 voice-preserving QA42 sample. Export A/B: source same 40s and original
voice recording via zero-shot baseline, no trained Ilya checkpoint. Diagnostics only.
"""
from pathlib import Path
import requests,subprocess,json,time,sys
ROOT=Path.home()/"Music Studio"
D=ROOT/"Diagnostics"/"QA43";D.mkdir(parents=True,exist_ok=True)
source=ROOT/"Diagnostics"/"QA42"/"QA42_SungSource_160s_same_seed.wav"
reference=next((ROOT/"Мой голос").glob("*df413d.wav"))
model=ROOT/"Voice Engine"/"seed-vc"/"runs"/"music_studio_personal_v1"/"ft_model.pth"
assert source.is_file() and reference.is_file() and not model.exists()
sess=requests.Session();sess.trust_env=False
h=sess.get("http://127.0.0.1:7870/api/health",timeout=8).json()
assert h["job"]["status"] not in ("preparing","generating","converting")
assert not any(h.get(k,{}).get("active") for k in ("training32","training41","training23"))
part=D/"QA43_QA42_SUNG_SOURCE_35to75.wav"
c=subprocess.run(["ffmpeg","-v","error","-nostdin","-y","-ss","35","-i",str(source),"-t","40",
                  "-ar","44100","-ac","2","-c:a","pcm_s24le",str(part)],capture_output=True,text=True,timeout=90)
assert c.returncode==0,c.stderr
print("SOURCE_SLICE_READY",part,part.stat().st_size,flush=True)
result=D/"QA43_MyVoice_22s_40steps.mp3"
py=ROOT/"Voice Engine"/".venv"/"Scripts"/"python.exe"
cli=ROOT/"Voice Engine"/"convert_track_studio40.py"  # Stable model with 22s reference window, not QA42 experiment
command=[str(py),"-u",str(cli),"--source",str(part),"--voice",str(reference),
         "--output",str(result),"--steps","40","--register","original","--language","ru","--keep-dry"]
start=time.monotonic()
r=subprocess.run(command,capture_output=True,text=True,timeout=1200)
(D/"QA43_conversion_stdout.log").write_text(r.stdout,encoding="utf-8")
(D/"QA43_conversion_stderr.log").write_text(r.stderr,encoding="utf-8")
report={"test":"QA42 source voice into single-person microphone reference",
        "slice_start_s":35,"slice_duration_s":40,"voice_reference":reference.name,
        "model":"base singing f0","diffusion_steps":40,"training":False,
        "same_user_music_not_overwritten":True,"elapsed_seconds":round(time.monotonic()-start,1),
        "returncode":r.returncode,"output":str(result),"error_excerpt":r.stderr[-1200:]}
if result.exists():
 report["size_bytes"]=result.stat().st_size
 qp=result.with_suffix(".quality.json")
 if qp.exists():
  data=json.loads(qp.read_text(encoding="utf-8"))
  report["f0_clean"]=data.get("f0_cleanup")
  report["pitch"]=data.get("pitch_consistency",{}).get("status")
  report["cosine"]=data.get("speaker_embedding_cosine")
  report["continuity"]=data.get("voice_check",{}).get("metrics")
(D/"QA43_voice_run.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA43_VOICE_RUN",json.dumps({k:v for k,v in report.items() if k!="error_excerpt"},ensure_ascii=True),flush=True)
if r.returncode!=0:print("FAILED",report["error_excerpt"],flush=True);sys.exit(r.returncode)
