"""QA37 voice ref A/B: maintain same musical source, base Seed-VC, no mixed-person model.
Makes second candidate only in Diagnostics. Records objective guard results for comparison.
"""
from pathlib import Path
import sys,json,time,requests
R=Path.home()/"Music Studio"
APP=R/"app";sys.path.insert(0,str(APP))
from voice_bridge25 import convert_song
D=R/"Diagnostics"/"QA37";D.mkdir(parents=True,exist_ok=True)
A=R/"Diagnostics"/"QA36"/"QA36_MY_VOICE_CALIBRATION_40s.mp3"
clip=R/"Diagnostics"/"QA36"/"QA36_calibration_original_40s.wav"
a_report=A.with_suffix(".quality.json")
mic_dir=R/"Мой голос"
ref=next(mic_dir.glob("*3867cb.wav"),None)
assert clip.is_file() and a_report.is_file() and ref is not None
assert not (R/"Voice Engine"/"seed-vc"/"runs"/"music_studio_personal_v1"/"ft_model.pth").exists(),"Unverified personal model still active"
h=requests.Session();h.trust_env=False
health=h.get("http://127.0.0.1:7870/api/health",timeout=8).json()
assert health["job"]["status"] not in ("preparing","generating","converting")
assert not any(health.get(n,{}).get("active") for n in ("training32","training41","training23"))
b_file=D/"QA37_B_REF3867_40s.mp3"
start=time.monotonic()
errors=[]
try:
 convert_song(clip,ref,b_file,steps=48,trained=False,register_mode="original",vocal_language="ru",
 on_stage=lambda x:print("STAGE",x,flush=True))
except BaseException as e:
 errors.append(repr(e))
base=json.loads(a_report.read_text(encoding="utf-8"))
second=json.loads(b_file.with_suffix(".quality.json").read_text(encoding="utf-8")) if b_file.with_suffix(".quality.json").exists() else None
def summarize(name,x):
 if x is None:return {"candidate":name,"completed":False}
 guard=x.get("voice_check",{})
 pitch=x.get("pitch_consistency",{})
 m=guard.get("metrics",{})
 return {"candidate":name,"completed":True,"file":x.get("final"),"reference":x.get("reference_preparation",{}).get("source"),"reference_selected_seconds":x.get("reference_preparation",{}).get("seconds"),"selected_start_seconds":x.get("reference_preparation",{}).get("start_seconds"),
         "diffusion_steps":x.get("diffusion_steps"),"pitch_status":pitch.get("status"),"speaker_embedding_cosine":x.get("speaker_embedding_cosine"),
         "vocal_drop_fraction":m.get("relative_missing_vocal_frames"),"dip_count":m.get("energy_dip_events"),"max_dip_s":m.get("longest_energy_dip_s"),
         "guard_status":guard.get("status"),"guard_accepted":guard.get("accepted"),
         "asr_checked":guard.get("asr_checked"),"naturalness_verified":guard.get("perceptual_quality_verified"),
         "model":x.get("model"),"voice_bytes":Path(x["final"]).stat().st_size if Path(x.get("final","")).exists() else 0}
x=summarize("A_QA36_23sec_reference_40steps",base)
y=summarize("B_QA37_31sec_reference_48steps",second)
out={"experimental":True,"modified_studio_ui":False,"baseline":x,"challenger":y,"errors":errors,"elapsed_s":round(time.monotonic()-start,2)}
(D/"compare_voices.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print("COMPARE",json.dumps(out,ensure_ascii=True),flush=True)
