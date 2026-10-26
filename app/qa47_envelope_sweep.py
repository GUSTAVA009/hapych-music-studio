"""QA47 offline gain-envelope experiment, no neural re-inference.
Goal: keep existing source phonemes intact, reduce unnaturally rapid vocal boosts.
Do not replace working Music Studio.
"""
import json,sys
from pathlib import Path
import numpy as np,soundfile as sf
from scipy.ndimage import gaussian_filter1d
V=Path.home()/"Music Studio"/"Voice Engine";sys.path.insert(0,str(V))
from voice_continuity42 import repair
from voice_guard42 import check
D=V.parent/"Diagnostics"/"QA47";D.mkdir(exist_ok=True,parents=True)
stem=D/"QA47_rawbase_35s"
src=stem.with_suffix(".source.wav");raw=stem.with_suffix(".raw.wav")
assert src.is_file() and raw.is_file(),(src,raw)
s,sr=sf.read(src,dtype="float32",always_2d=True)
v,sv=sf.read(raw,dtype="float32",always_2d=True)
assert sr==sv
s=s.mean(axis=1);v=v.mean(axis=1);n=min(len(s),len(v));s=s[:n];v=v[:n]
hop=max(256,round(sr*.02))
def frame_rms(z):
 pad=(-len(z))%hop
 if pad:z=np.pad(z,(0,pad))
 return np.sqrt(np.mean(z.reshape(-1,hop).astype("float64")**2,axis=1)+1e-12)
x,y=frame_rms(s),frame_rms(v)
active=x>max(.003,float(np.percentile(x,85))*.25)
stable=active&(y>.002)
assert stable.sum()>=60
ratio=20*np.log10((x+1e-8)/(y+1e-8))
median=float(np.median(ratio[stable]))
local=ratio-median
mask=active & (y>.002) & (local>7)
weight=gaussian_filter1d(mask.astype(float),sigma=2,mode="constant")
boost=gaussian_filter1d(np.clip((local-4)/10,0,1),sigma=2,mode="constant")
old_curve=6.5*np.minimum(boost,weight)
results=[]
def assess(name,db):
 if np.max(db)>0:
  positions=np.arange(len(db))*hop
  gain=np.interp(np.arange(n),positions,db,left=0,right=0)
  temp=(v * np.power(10.0,gain/20)).astype("float32")
 else:
  temp=v.copy()
 peak=float(np.max(np.abs(temp)))
 if peak>.985:temp*=.985/peak
 output=D/(name+".wav")
 sf.write(output,temp,sr,subtype="FLOAT")
 report=check(src,output,D/(name+".voicecheck.json"),"ru")
 em=report.get("metrics",{})
 # compare amplitude envelope change, not subjective vibrato.
 values={"label":name,"file":str(output),"voice_accept":report.get("accepted"),
 "dips":em.get("energy_dip_events"),"weak_ratio":em.get("relative_missing_vocal_frames"),
 "max_dip_s":em.get("longest_energy_dip_s"),
 "max_gain_db":round(float(np.max(db)),3),
 "mean_gain_on_active_db":round(float(np.mean(db[active])),3),
 "gain_step_p95_db_20ms":round(float(np.percentile(np.abs(np.diff(db)),95)),3),
 "gain_step_p99_db_20ms":round(float(np.percentile(np.abs(np.diff(db)),99)),3)}
 results.append(values)
 print("QA47_VOICE_ENVELOPE",json.dumps(values,ensure_ascii=True),flush=True)
 return values
assess("raw_neural",np.zeros_like(old_curve))
assess("old_fast_gain",old_curve)
for sigma in (2.5,4.,6.):
 for cap in (5.4,4.5):
  db=np.clip(gaussian_filter1d(old_curve,sigma=sigma,mode="nearest")*1.04,0,cap)
  db[~(gaussian_filter1d(active.astype(float),sigma=5)>.13)]=0
  # gradual slope, but don't force a loud boost across stops.
  for j in range(1,len(db)):
   if db[j]>db[j-1]+.34:db[j]=db[j-1]+.34
  for j in range(len(db)-2,-1,-1):
   if db[j]>db[j+1]+.34:db[j]=db[j+1]+.34
  name=f"smooth_{str(sigma).replace('.','p')}_cap_{str(cap).replace('.','p')}"
  assess(name,db)
# choose conservative candidate: never more dips than the old baseline, not worse
# in fraction missing vocal frames, and smaller gain change spikes.
old=next(x for x in results if x["label"]=="old_fast_gain")
eligible=[v for v in results if v["label"].startswith("smooth") and
          v["dips"]<=old["dips"] and v["weak_ratio"]<=old["weak_ratio"]+.003 and
          v["gain_step_p99_db_20ms"]<old["gain_step_p99_db_20ms"]]
if eligible:
 eligible.sort(key=lambda k:(k["gain_step_p99_db_20ms"],k["weak_ratio"],k["max_gain_db"]))
 chosen=eligible[0]
else:chosen=old
(D/"QA47_envelope_sweep.json").write_text(json.dumps({
 "source_raw_no_renet_generation":True,
 "raw_src_sha256":__import__("hashlib").sha256(raw.read_bytes()).hexdigest(),
 "results":results,"selected":chosen,
 "caution":"gain sweep only; no phonemes, F0 or model weights changed",
 "listening_quality_verified":False,"production_unchanged":True},ensure_ascii=False,indent=2),encoding="utf-8")
print("QA47_OPTIMUM",json.dumps(chosen,ensure_ascii=True),flush=True)
