"""QA136 source singing register diagnostic: original isolated vocal versus
converted vocal; objective pitch only. No inference of singer's sex identity.
"""
from pathlib import Path
import json,sys,numpy as np,soundfile as sf
import parselmouth
sys.stdout.reconfigure(encoding="utf8")
R=Path.home()/"Music Studio";D=R/"Integrations"/"RapFullTrack-QA135"
state=json.loads((D/"Results"/"QA135_apex_pipeline_report.json").read_text(encoding="utf8"))
items={"ACE_original_vocal":Path(state["vocal_stem_file"]),
       "Apex_owner_voice":Path(state["dry_vocal"])}
regions={"verse1":(5,27),"chorus1":(33,64),
         "verse2":(69,85),"chorus2":(100,121),
         "outro":(138,149)}
out={}
for name,path in items.items():
 y,sr=sf.read(path,always_2d=True,dtype="float32");y=y.mean(axis=1)
 results={}
 for label,(a,b) in regions.items():
  seg=y[round(a*sr):round(b*sr)]
  pitch=parselmouth.Sound(seg,sr).to_pitch(time_step=.01,pitch_floor=70,pitch_ceiling=650)
  f=pitch.selected_array["frequency"]
  voiced=f[(f>70)&(f<650)]
  results[label]={"f0_median_hz":round(float(np.median(voiced)),1) if len(voiced) else None,
    "f0_p25_hz":round(float(np.quantile(voiced,.25)),1) if len(voiced) else None,
    "f0_p75_hz":round(float(np.quantile(voiced,.75)),1) if len(voiced) else None,
    "voiced_frames":int(len(voiced))}
 out[name]=results
 print("QA136_F0",name,results,flush=True)
(D/"QA136_vocal_pitch_diagnostic.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf8")
