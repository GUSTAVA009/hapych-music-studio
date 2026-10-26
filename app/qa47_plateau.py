"""QA47 plateau rescue sweep: smooth phrase envelopes while protecting quiet syllables.
No neural synthesis or production changes.
"""
from pathlib import Path
import json,sys
import numpy as np,soundfile as sf
from scipy.ndimage import gaussian_filter1d,maximum_filter1d
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA47";sys.path.insert(0,str(R/"Voice Engine"))
from voice_guard42 import check
stem=D/"QA47_rawbase_35s";src=stem.with_suffix(".source.wav");raw=stem.with_suffix(".raw.wav")
source,sr=sf.read(src,dtype="float32",always_2d=True)
converted,sc=sf.read(raw,dtype="float32",always_2d=True)
source=source.mean(axis=1);converted=converted.mean(axis=1)
n=min(len(source),len(converted))
source=source[:n];converted=converted[:n]
hop=max(256,round(sr*.02))
def frames(x):
 x=np.asarray(x,dtype="float64")
 if len(x)%hop:x=np.pad(x,(0,hop-len(x)%hop))
 return np.sqrt(np.mean(x.reshape(-1,hop)**2,axis=1)+1e-12)
x,y=frames(source),frames(converted)
active=x>max(.003,float(np.percentile(x,85))*.25)
stable=active&(y>.002)
relative=float(np.median(20*np.log10((x[stable]+1e-8)/(y[stable]+1e-8))))
local=20*np.log10((x+1e-8)/(y+1e-8))-relative
weak=(active & (y>.002) & (local>7))
old=6.5*np.minimum(gaussian_filter1d(np.clip((local-4)/10,0,1),2),
                    gaussian_filter1d(weak.astype(float),2))
prev=json.loads((D/"QA47_envelope_sweep.json").read_text(encoding="utf-8"))
baseline=next(r for r in prev["results"] if r["label"]=="old_fast_gain")
results=[]
support=gaussian_filter1d((active & (y>.0015)).astype(float),sigma=4)
for kernel in (5,9,13,19):
 for sigma in (3.0,5.0):
  elev=maximum_filter1d(old,size=kernel,mode="constant")
  db=gaussian_filter1d(elev,sigma=sigma,mode="constant")
  db*=np.clip(support*2.4,0,1)
  db=np.clip(db,0,5.4)
  for j in range(1,len(db)):
   db[j]=min(db[j],db[j-1]+.26)
  for j in range(len(db)-2,-1,-1):
   db[j]=min(db[j],db[j+1]+.26)
  # Output is fully diagnostic and preserves the original melody.
  positions=np.arange(len(db))*hop
  samples=np.interp(np.arange(n),positions,db,left=0,right=0)
  out=converted*np.power(10.,samples/20)
  peak=float(np.max(np.abs(out)))
  if peak>.985:out*=.985/peak
  name=f"plateau_{kernel}_sigma{int(sigma)}"
  file=D/(name+".wav");sf.write(file,out,sr,subtype="FLOAT")
  report=check(src,file,D/(name+".voicecheck.json"),"ru")
  metric=report["metrics"]
  item={"label":name,"file":str(file),"dips":metric["energy_dip_events"],
  "weak_ratio":metric["relative_missing_vocal_frames"],
  "max_dip_s":metric["longest_energy_dip_s"],
  "max_gain_db":round(float(db.max()),3),
  "gain_step_p99_db_20ms":round(float(np.percentile(np.abs(np.diff(db)),99)),3),
  "mean_gain_active_db":round(float(db[active].mean()),3)}
  results.append(item)
  print("QA47_PLATEAU",json.dumps(item,ensure_ascii=True),flush=True)
eligible=[v for v in results if v["dips"]<=baseline["dips"] and
  v["weak_ratio"]<=baseline["weak_ratio"]+.003 and
  v["gain_step_p99_db_20ms"]<baseline["gain_step_p99_db_20ms"]]
if eligible:
 eligible.sort(key=lambda x:(x["gain_step_p99_db_20ms"],x["mean_gain_active_db"],x["weak_ratio"]))
 choice=eligible[0]
else: choice=baseline
(D/"QA47_plateau_report.json").write_text(json.dumps({"base":baseline,"candidates":results,
 "selected":choice,"production_untouched":True,"f0_unchanged":True,"model_unchanged":True,
 "asr_not_yet_checked":True,"listening_not_certified":True},ensure_ascii=False,indent=2),encoding="utf-8")
print("QA47_PLATEAU_SELECTED",json.dumps(choice,ensure_ascii=True),flush=True)
