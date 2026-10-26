"""QA37 factorial crossover: distinguish 12s speaker-reference effect from inference steps.
All outputs diagnostic only. User recordings and published tracks are untouched.
"""
from pathlib import Path
import json,sys,time,requests
R=Path.home()/"Music Studio";sys.path.insert(0,str(R/"app"))
from voice_bridge25 import convert_song
D=R/"Diagnostics"/"QA37";D.mkdir(exist_ok=True,parents=True)
source=R/"Diagnostics"/"QA36"/"QA36_calibration_original_40s.wav"
assert source.is_file()
voices=R/"Мой голос"
settings=[
 ("C_23sec_ref_48steps","df413d",48),
 ("D_31sec_ref_40steps","3867cb",40),
]
h=requests.Session();h.trust_env=False
j=h.get("http://127.0.0.1:7870/api/health",timeout=7).json()
assert j["job"]["status"] not in ("generating","preparing","converting")
assert not any(j.get(k,{}).get("active") for k in ("training32","training41","training23"))
assert not (R/"Voice Engine"/"seed-vc"/"runs"/"music_studio_personal_v1"/"ft_model.pth").exists()
results=[]
for label,ref_id,steps in settings:
 reference=next(voices.glob("*"+ref_id+".wav"),None)
 assert reference and reference.is_file()
 output=D/("QA37_"+label+".mp3")
 t=time.monotonic()
 try:
  convert_song(source,reference,output,steps=steps,trained=False,
    register_mode="original",vocal_language="ru",chorus_ranges=[],
    on_stage=lambda s:print("STAGE",label,s,flush=True))
  report=json.loads(output.with_suffix(".quality.json").read_text(encoding="utf-8"))
  guard=report.get("voice_check",{})
  entry={"label":label,"ok":True,"file":str(output),"reference":reference.name,"steps":steps,
    "speaker_embedding_cosine":report.get("speaker_embedding_cosine"),
    "guard_status":guard.get("status"),"drop_fraction":guard.get("metrics",{}).get("relative_missing_vocal_frames"),
    "dips":guard.get("metrics",{}).get("energy_dip_events"),
    "max_dip_s":guard.get("metrics",{}).get("longest_energy_dip_s")}
 except BaseException as err:entry={"label":label,"ok":False,"error":str(err)[:400]}
 entry["elapsed_s"]=round(time.monotonic()-t,1)
 results.append(entry)
 (D/"factorial_voice_comparison.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
 print("QA37_GRID",json.dumps(entry,ensure_ascii=True),flush=True)
print("QA37_GRID_DONE",len(results))
