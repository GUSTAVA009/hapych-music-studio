"""QA36 personal-voice calibration; isolated 40s test, not promoted to library.
Uses one user-reported microphone reference. Zero-shot Seed-VC; no legacy Ilya-trained weights.
"""
import sys,subprocess,json,time,traceback,requests
from pathlib import Path
R=Path.home()/"Music Studio";sys.path.insert(0,str(R/"app"))
from voice_bridge25 import convert_song
folder=R/"Diagnostics"/"QA36";folder.mkdir(parents=True,exist_ok=True)
vocal=next((R/"Мой голос").glob("*183309*Микрофон*.wav"),None)
source=sorted((R/"Исходные версии").glob("*QA36*.wav"),key=lambda p:p.name)[-1]
if vocal is None or source is None:raise RuntimeError("Source or recognized microphone reference missing")
if (R/"Voice Engine"/"seed-vc"/"runs"/"music_studio_personal_v1"/"ft_model.pth").exists():
 raise RuntimeError("Unverified mixed speaker checkpoint still active")
sess=requests.Session();sess.trust_env=False
h=sess.get("http://127.0.0.1:7870/api/health",timeout=8).json()
if h["job"]["status"] in ("preparing","generating","converting") or any(h.get(v,{}).get("active") for v in ("training32","training41","training23")):
 raise RuntimeError("GPU busy; voice calibration not started")
clip=folder/"QA36_calibration_original_40s.wav"
command=["ffmpeg","-y","-v","error","-ss","25","-i",str(source),"-t","40",
         "-ac","2","-ar","44100","-c:a","pcm_s24le",str(clip)]
p=subprocess.run(command,capture_output=True,text=True,timeout=120)
if p.returncode:raise RuntimeError("Could not create test excerpt: "+p.stderr[-400:])
target=folder/"QA36_MY_VOICE_CALIBRATION_40s.mp3"
start=time.monotonic()
report={"source":str(source),"reference":vocal.name,"output":str(target),
        "personal_mixed_checkpoint":False,"legacy_speaker_training_disabled":True,
        "model":"zero-shot Seed-VC","steps":40,
        "human_voice_identity_verified":False,"native_russian_diction_verified":False,
        "target_has_independent_backing_singers":False}
try:
 convert_song(clip,vocal,target,steps=40,trained=False,
              vocal_language="ru",register_mode="original",
              chorus_ranges=[],
              on_stage=lambda msg:print("VOICE_STAGE",msg,flush=True))
 report["status"]="completed"
 report["output_bytes"]=target.stat().st_size
except BaseException as e:
 report["status"]="rejected_or_failed"
 report["error"]=str(e)
 print("VOICE_CALIBRATION_FAILED",repr(e),flush=True)
finally:
 report["elapsed_s"]=round(time.monotonic()-start,2)
 (folder/"QA36_voice_calibration_report.json").write_text(
    json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
 print("CALIBRATION_REPORT",json.dumps(report,ensure_ascii=True),flush=True)
